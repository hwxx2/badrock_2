import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request


PR_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+)/pull/(?P<number>\d+)/?$"
)

BINARY_EXTENSIONS = {
    ".7z",
    ".avif",
    ".bin",
    ".bmp",
    ".class",
    ".dll",
    ".doc",
    ".docx",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".jar",
    ".jpeg",
    ".jpg",
    ".mov",
    ".mp4",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".so",
    ".tar",
    ".webp",
    ".xls",
    ".xlsx",
    ".zip",
}


class GitHubError(RuntimeError):
    pass


def parse_pr_url(pr_url):
    match = PR_URL_RE.match((pr_url or "").strip())
    if not match:
        raise ValueError("PR URL must look like https://github.com/OWNER/REPO/pull/NUMBER")
    return match.group("owner"), match.group("repo"), int(match.group("number"))


def is_binary_filename(filename):
    _, ext = os.path.splitext((filename or "").lower())
    return ext in BINARY_EXTENSIONS


class GitHubClient:
    def __init__(self, token, api_base="https://api.github.com", timeout=20):
        self.token = token
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout

    def get_pull_request(self, owner, repo, number):
        return self._request("GET", f"/repos/{owner}/{repo}/pulls/{number}")

    def list_pull_request_files(self, owner, repo, number):
        files = []
        page = 1
        while True:
            path = f"/repos/{owner}/{repo}/pulls/{number}/files?per_page=100&page={page}"
            batch = self._request("GET", path)
            files.extend(batch)
            if len(batch) < 100:
                return files
            page += 1

    def post_issue_comment(self, owner, repo, number, body):
        payload = {"body": body}
        return self._request("POST", f"/repos/{owner}/{repo}/issues/{number}/comments", payload)

    def _request(self, method, path, payload=None):
        url = f"{self.api_base}{path}"
        data = None
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "codebuddy-agent",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                text = response.read().decode("utf-8")
                return json.loads(text) if text else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise GitHubError(f"GitHub API {method} {path} failed: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise GitHubError(f"GitHub API {method} {path} failed: {exc.reason}") from exc


def build_diff_bundle(files, max_files=80, max_patch_chars=45000):
    included = []
    skipped = []
    total_patch_chars = 0
    truncated = False

    for item in files[:max_files]:
        filename = item.get("filename", "")
        patch = item.get("patch")
        if is_binary_filename(filename) or patch is None:
            skipped.append({"filename": filename, "reason": "binary_or_no_patch"})
            continue

        remaining = max_patch_chars - total_patch_chars
        if remaining <= 0:
            truncated = True
            break

        if len(patch) > remaining:
            patch = patch[:remaining] + "\n...TRUNCATED..."
            truncated = True

        included.append(
            {
                "filename": filename,
                "status": item.get("status"),
                "additions": item.get("additions", 0),
                "deletions": item.get("deletions", 0),
                "changes": item.get("changes", 0),
                "patch": patch,
            }
        )
        total_patch_chars += len(patch)

    if len(files) > max_files:
        truncated = True
        skipped.extend(
            {"filename": item.get("filename", ""), "reason": "file_limit"}
            for item in files[max_files:]
        )

    return {
        "files": included,
        "skipped": skipped,
        "truncated": truncated,
        "total_files": len(files),
        "included_files": len(included),
    }

