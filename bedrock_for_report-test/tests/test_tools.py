import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lambda"))

from tools.github_pr import build_diff_bundle, parse_pr_url
from tools.security import find_security_findings


def test_parse_pr_url():
    assert parse_pr_url("https://github.com/acme/shop/pull/42") == ("acme", "shop", 42)


def test_parse_pr_url_rejects_invalid_url():
    try:
        parse_pr_url("https://example.com/acme/shop/pull/42")
    except ValueError as exc:
        assert "github.com" in str(exc)
    else:
        raise AssertionError("invalid URL should fail")


def test_binary_files_are_skipped():
    bundle = build_diff_bundle(
        [
            {"filename": "diagram.png", "patch": None},
            {"filename": "app.py", "patch": "@@ -1 +1 @@\n+print('ok')"},
        ]
    )
    assert bundle["included_files"] == 1
    assert bundle["skipped"][0]["filename"] == "diagram.png"


def test_security_finds_sql_injection_and_secret():
    bundle = {
        "files": [
            {
                "filename": "app.py",
                "patch": '@@ -1,0 +1,2 @@\n+API_KEY = "12345"\n+query = f"SELECT * FROM users WHERE id = {id}"',
            }
        ]
    }
    findings = find_security_findings(bundle)
    rule_ids = {item["rule_id"] for item in findings}
    assert "hardcoded-secret" in rule_ids
    assert "sql-injection-fstring" in rule_ids

