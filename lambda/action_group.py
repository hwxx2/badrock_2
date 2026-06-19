import json
import os

from tools.discord import send_discord_notification
from tools.complexity import analyze_complexity
from tools.github_pr import GitHubClient, build_diff_bundle, parse_pr_url
from tools.refactor import suggest_refactors
from tools.security import find_security_findings
from tools.testgen import generate_test_suggestions


def handler(event, context):
    api_path = event.get("apiPath", "")
    method = event.get("httpMethod", "post").lower()
    body = _request_body(event)

    try:
        if api_path == "/github/pr" and method == "post":
            result = _get_github_pr(body)
        elif api_path == "/complexity/analyze" and method == "post":
            result = analyze_complexity(body.get("diff_bundle", {}))
        elif api_path == "/security/analyze" and method == "post":
            result = find_security_findings(body.get("diff_bundle", {}))
        elif api_path == "/tests/generate" and method == "post":
            result = generate_test_suggestions(body.get("diff_bundle", {}), body.get("findings", []))
        elif api_path == "/refactor/suggest" and method == "post":
            result = suggest_refactors(body.get("diff_bundle", {}), body.get("findings", []))
        elif api_path == "/discord/notify" and method == "post":
            result = send_discord_notification(
                os.environ.get("DISCORD_WEBHOOK_URL", ""),
                body.get("pr_url", ""),
                body.get("status", "success"),
                body.get("summary", ""),
            )
        else:
            return _bedrock_response(event, 404, {"error": f"unsupported path {api_path}"})
        return _bedrock_response(event, 200, result)
    except Exception as exc:
        return _bedrock_response(event, 500, {"error": str(exc)})


def _get_github_pr(body):
    owner, repo, number = parse_pr_url(body["pr_url"])
    github = GitHubClient(
        token=os.environ.get("GITHUB_TOKEN", ""),
        api_base=os.environ.get("GITHUB_API_BASE", "https://api.github.com"),
    )
    pr = github.get_pull_request(owner, repo, number)
    files = github.list_pull_request_files(owner, repo, number)
    return {"pull_request": pr, "diff_bundle": build_diff_bundle(files)}


def _request_body(event):
    request_body = event.get("requestBody", {}).get("content", {}).get("application/json", {})
    body = request_body.get("properties") or request_body.get("body") or {}
    if isinstance(body, str):
        return json.loads(body)
    if isinstance(body, list):
        return {item["name"]: item.get("value") for item in body if "name" in item}
    return body


def _bedrock_response(event, status_code, payload):
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", "CodeBuddyTools"),
            "apiPath": event.get("apiPath", "/"),
            "httpMethod": event.get("httpMethod", "post"),
            "httpStatusCode": status_code,
            "responseBody": {
                "application/json": {
                    "body": json.dumps(payload, ensure_ascii=False),
                }
            },
        },
    }
