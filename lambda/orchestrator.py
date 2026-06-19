import base64
import hashlib
import hmac
import json
import logging
import os
import time
import uuid

try:
    import boto3
except ImportError:
    boto3 = None

from tools.complexity import analyze_complexity
from tools.discord import send_discord_notification
from tools.github_pr import GitHubClient, GitHubError, build_diff_bundle, parse_pr_url
from tools.refactor import suggest_refactors
from tools.review_format import compose_review, summary_for_notification
from tools.security import find_security_findings
from tools.testgen import generate_test_suggestions


LOGGER = logging.getLogger()
LOGGER.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


def handler(event, context):
    start = time.time()
    request_id = _request_id(event)
    LOGGER.info("codebuddy request started request_id=%s", request_id)

    try:
        payload = _load_payload(event)
        _verify_github_signature(event, payload)
        if _is_ignored_github_action(payload):
            return _response(202, {"message": "ignored pull_request action"})

        pr_url = _extract_pr_url(payload)
        owner, repo, number = parse_pr_url(pr_url)
        github = GitHubClient(
            token=os.environ.get("GITHUB_TOKEN", ""),
            api_base=os.environ.get("GITHUB_API_BASE", "https://api.github.com"),
        )

        pr = github.get_pull_request(owner, repo, number)
        cache_key = _cache_key(owner, repo, number, pr)
        cached = _get_cached_review(cache_key)
        if cached:
            LOGGER.info("cache hit for %s", cache_key)
            return _response(200, {"message": "already reviewed", "request_id": request_id})

        files = github.list_pull_request_files(owner, repo, number)
        diff_bundle = build_diff_bundle(files)
        findings = _run_local_review(diff_bundle)
        bedrock_text = _invoke_bedrock_agent(pr, diff_bundle, findings)
        tests = generate_test_suggestions(diff_bundle, findings)
        refactors = suggest_refactors(diff_bundle, findings)
        duration = time.time() - start

        review_body = compose_review(
            pr=pr,
            diff_bundle=diff_bundle,
            findings=findings,
            tests=tests,
            refactors=refactors,
            bedrock_text=bedrock_text,
            duration_seconds=duration,
        )
        github.post_issue_comment(owner, repo, number, review_body)

        summary = summary_for_notification(findings)
        discord_result = send_discord_notification(
            os.environ.get("DISCORD_WEBHOOK_URL", ""),
            pr_url,
            "success",
            summary,
        )
        _put_metric("ReviewDuration", duration, "Seconds")
        _put_metric("Success", 1, "Count")
        _put_metric("ToolCallCount", 5, "Count")
        _put_cached_review(cache_key, review_body)

        return _response(
            200,
            {
                "message": "review complete",
                "request_id": request_id,
                "pr_url": pr_url,
                "findings": len(findings),
                "discord": discord_result,
                "duration_seconds": round(duration, 3),
            },
        )
    except ValueError as exc:
        _put_metric("Failure", 1, "Count")
        return _response(400, {"error": str(exc), "request_id": request_id})
    except GitHubError as exc:
        LOGGER.exception("github error")
        _put_metric("Failure", 1, "Count")
        return _response(502, {"error": str(exc), "request_id": request_id})
    except Exception as exc:
        LOGGER.exception("unexpected error")
        _put_metric("Failure", 1, "Count")
        return _response(500, {"error": str(exc), "request_id": request_id})


def _run_local_review(diff_bundle):
    return find_security_findings(diff_bundle) + analyze_complexity(diff_bundle)


def _invoke_bedrock_agent(pr, diff_bundle, local_findings):
    if os.environ.get("ENABLE_BEDROCK", "true").lower() != "true":
        return ""
    if not boto3:
        return ""

    agent_id = os.environ.get("BEDROCK_AGENT_ID")
    alias_id = os.environ.get("BEDROCK_AGENT_ALIAS_ID")
    if not agent_id or not alias_id:
        return ""

    prompt = {
        "task": "이 GitHub Pull Request를 한국어로 리뷰하세요. 보안, 코드 스타일, 복잡도, 테스트, 리팩터링 관점에 집중하세요.",
        "pull_request": {
            "title": pr.get("title"),
            "html_url": pr.get("html_url"),
            "author": pr.get("user", {}).get("login"),
        },
        "diff_bundle": diff_bundle,
        "local_findings": local_findings,
        "output_format": "GitHub PR 댓글에 바로 붙일 수 있는 간결한 한국어 Markdown 리뷰를 작성하세요. 변경되지 않은 코드는 반복하지 마세요.",
    }
    client = boto3.client("bedrock-agent-runtime")
    chunks = []
    response = client.invoke_agent(
        agentId=agent_id,
        agentAliasId=alias_id,
        sessionId=f"webhook-{pr.get('id', uuid.uuid4())}",
        inputText=json.dumps(prompt, ensure_ascii=False),
        enableTrace=os.environ.get("ENABLE_BEDROCK_TRACE", "false").lower() == "true",
    )
    for event in response.get("completion", []):
        if "chunk" in event:
            chunks.append(event["chunk"]["bytes"].decode("utf-8"))
    return "".join(chunks).strip()


def _load_payload(event):
    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError("request body must be valid JSON") from exc


def _extract_pr_url(payload):
    if payload.get("pr_url"):
        return payload["pr_url"]
    if payload.get("pull_request", {}).get("html_url"):
        return payload["pull_request"]["html_url"]
    raise ValueError("payload must include pr_url or pull_request.html_url")


def _is_ignored_github_action(payload):
    if "pull_request" not in payload:
        return False
    return payload.get("action") not in {"opened", "reopened", "synchronize", "ready_for_review"}


def _verify_github_signature(event, payload):
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
    if not secret:
        return

    headers = {str(k).lower(): v for k, v in (event.get("headers") or {}).items()}
    is_github_webhook = "x-github-event" in headers or "pull_request" in payload
    if not is_github_webhook:
        return

    signature = headers.get("x-hub-signature-256")
    if not signature:
        raise ValueError("missing X-Hub-Signature-256 header")

    body = event.get("body") or ""
    raw_body = base64.b64decode(body) if event.get("isBase64Encoded") else body.encode("utf-8")
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise ValueError("invalid GitHub webhook signature")


def _request_id(event):
    headers = {str(k).lower(): v for k, v in (event.get("headers") or {}).items()}
    return headers.get("x-github-delivery") or event.get("requestContext", {}).get("requestId") or str(uuid.uuid4())


def _cache_key(owner, repo, number, pr):
    sha = pr.get("head", {}).get("sha", "unknown")
    return f"{owner}/{repo}#{number}:{sha}"


def _get_cached_review(cache_key):
    table_name = os.environ.get("REVIEW_CACHE_TABLE")
    if not table_name or not boto3:
        return None
    table = boto3.resource("dynamodb").Table(table_name)
    item = table.get_item(Key={"ReviewKey": cache_key}).get("Item")
    return item.get("ReviewBody") if item else None


def _put_cached_review(cache_key, review_body):
    table_name = os.environ.get("REVIEW_CACHE_TABLE")
    if not table_name or not boto3:
        return
    table = boto3.resource("dynamodb").Table(table_name)
    table.put_item(
        Item={
            "ReviewKey": cache_key,
            "ReviewBody": review_body[:300000],
            "CreatedAt": int(time.time()),
        }
    )


def _put_metric(name, value, unit):
    if not boto3:
        return
    try:
        boto3.client("cloudwatch").put_metric_data(
            Namespace="CodeBuddy",
            MetricData=[{"MetricName": name, "Value": value, "Unit": unit}],
        )
    except Exception:
        LOGGER.exception("failed to put metric %s", name)


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }
