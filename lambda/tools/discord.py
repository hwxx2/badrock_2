import json
import urllib.error
import urllib.request


def send_discord_notification(webhook_url, pr_url, status, summary):
    if not webhook_url:
        return {"sent": False, "reason": "missing_webhook_url"}

    color = 0x2ECC71 if status == "success" else 0xE74C3C
    status_label = {"success": "성공", "failure": "실패"}.get(status, status)
    message = {
        "username": "CodeBuddy",
        "allowed_mentions": {"parse": []},
        "embeds": [
            {
                "title": "CodeBuddy 리뷰 완료",
                "url": pr_url,
                "color": color,
                "fields": [
                    {"name": "상태", "value": status_label, "inline": True},
                    {"name": "Pull Request", "value": pr_url[:1024], "inline": False},
                    {"name": "요약", "value": summary[:1024] or "요약 없음", "inline": False},
                ],
            }
        ],
    }
    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(message).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "CodeBuddyBot/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return {"sent": 200 <= response.status < 300, "status": response.status}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        return {"sent": False, "status": exc.code, "reason": exc.reason, "body": body}
    except urllib.error.URLError as exc:
        return {"sent": False, "reason": str(exc.reason)}

