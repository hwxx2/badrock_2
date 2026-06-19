def generate_test_suggestions(diff_bundle, findings):
    suggestions = []
    filenames = [item["filename"] for item in diff_bundle.get("files", [])]

    if any(name.endswith(".py") for name in filenames):
        suggestions.append(
            {
                "title": "변경된 Python 동작에 대한 pytest 커버리지 추가",
                "code": """def test_add_handles_positive_numbers():
    assert add(2, 3) == 5

def test_get_user_uses_parameterized_query(mocker):
    cursor = mocker.Mock()
    get_user(cursor, 1)
    sql, params = cursor.execute.call_args.args
    assert "%s" in sql
    assert params == (1,)
""",
            }
        )

    if any(item.get("severity") == "High" for item in findings):
        suggestions.append(
            {
                "title": "높은 심각도 이슈에 대한 회귀 테스트 추가",
                "code": """from pathlib import Path


def test_no_plaintext_secret_in_config():
    source = Path("app.py").read_text(encoding="utf-8")
    assert "API_KEY =" not in source
    assert "password =" not in source.lower()
""",
            }
        )

    if not suggestions:
        suggestions.append(
            {
                "title": "기본 스모크 테스트 추가",
                "code": """def test_changed_module_imports():
    import app
    assert app is not None
""",
            }
        )

    return suggestions
