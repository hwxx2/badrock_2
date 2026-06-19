import ast
import re


BRANCH_TOKENS = re.compile(r"\b(if|for|while|and|or|except|case|elif)\b")


def analyze_complexity(diff_bundle):
    findings = []
    for file_info in diff_bundle.get("files", []):
        filename = file_info["filename"]
        added_code = "\n".join(line for _, line in _added_lines(file_info.get("patch", "")))
        if not added_code.strip():
            continue

        branch_score = len(BRANCH_TOKENS.findall(added_code))
        added_lines = len([line for line in added_code.splitlines() if line.strip()])
        if added_lines > 80 or branch_score >= 8:
            findings.append(
                {
                    "type": "complexity",
                    "severity": "Medium",
                    "file": filename,
                    "line": None,
                    "issue": f"추가된 코드가 크거나 분기 조건이 많습니다. ({added_lines}줄, 분기 점수 {branch_score})",
                    "recommendation": "변경을 더 작은 함수로 나누고 핵심 흐름별 테스트를 추가하세요.",
                }
            )

        if filename.endswith(".py"):
            findings.extend(_python_function_findings(filename, added_code))
    return findings


def _python_function_findings(filename, added_code):
    findings = []
    try:
        tree = ast.parse(added_code)
    except SyntaxError:
        return findings

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            complexity = 1
            for child in ast.walk(node):
                if isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.BoolOp, ast.Try, ast.Match)):
                    complexity += 1
            if complexity >= 8:
                findings.append(
                    {
                        "type": "complexity",
                        "severity": "Medium",
                        "file": filename,
                        "line": node.lineno,
                        "issue": f"`{node.name}` 함수의 추정 순환 복잡도가 {complexity}입니다.",
                        "recommendation": "검증, 입출력, 비즈니스 로직을 별도 헬퍼로 분리하세요.",
                    }
                )
    return findings


def _added_lines(patch):
    current_new_line = 0
    for raw_line in patch.splitlines():
        if raw_line.startswith("@@"):
            match = re.search(r"\+(\d+)", raw_line)
            current_new_line = int(match.group(1)) - 1 if match else current_new_line
            continue
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            current_new_line += 1
            yield current_new_line, raw_line[1:]
        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            continue
        else:
            current_new_line += 1
