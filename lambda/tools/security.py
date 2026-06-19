import re


RULES = [
    {
        "id": "sql-injection-fstring",
        "severity": "High",
        "pattern": re.compile(r"f[\"'].*SELECT .*WHERE .*\{.*\}", re.IGNORECASE),
        "issue": "SQL 쿼리가 문자열 보간으로 생성되고 있습니다.",
        "recommendation": "cursor.execute(sql, (value,)) 형태의 파라미터 바인딩을 사용하세요.",
    },
    {
        "id": "hardcoded-secret",
        "severity": "High",
        "pattern": re.compile(r"(api[_-]?key|secret|token|password)\s*=\s*[\"'][^\"']{4,}[\"']", re.IGNORECASE),
        "issue": "소스 코드에 민감 정보가 하드코딩된 것으로 보입니다.",
        "recommendation": "민감 정보는 AWS Secrets Manager, SSM Parameter Store 또는 환경 변수로 분리하세요.",
    },
    {
        "id": "unsafe-pickle",
        "severity": "High",
        "pattern": re.compile(r"\bpickle\.loads?\s*\("),
        "issue": "pickle 역직렬화는 공격자가 조작한 코드를 실행할 수 있습니다.",
        "recommendation": "신뢰된 JSON에는 json.loads를 사용하고, 가능한 경우 타입이 고정된 안전한 파서를 사용하세요.",
    },
    {
        "id": "debug-secret-log",
        "severity": "Medium",
        "pattern": re.compile(r"(console\.log|print|logger\.\w+)\s*\(.*(secret|token|password|api_key)", re.IGNORECASE),
        "issue": "민감 값이 로그에 기록될 수 있습니다.",
        "recommendation": "해당 로그를 제거하거나 민감 필드를 마스킹한 뒤 기록하세요.",
    },
    {
        "id": "shell-true",
        "severity": "Medium",
        "pattern": re.compile(r"subprocess\.\w+\s*\(.*shell\s*=\s*True"),
        "issue": "명령 실행에 shell=True가 사용되고 있습니다.",
        "recommendation": "문자열 명령 대신 인자 리스트를 전달하고 shell=False를 유지하세요.",
    },
    {
        "id": "unsafe-yaml",
        "severity": "Medium",
        "pattern": re.compile(r"\byaml\.load\s*\((?!.*SafeLoader)"),
        "issue": "SafeLoader 없이 yaml.load를 사용하면 안전하지 않은 객체가 생성될 수 있습니다.",
        "recommendation": "yaml.safe_load 또는 yaml.load(..., Loader=yaml.SafeLoader)를 사용하세요.",
    },
]


def find_security_findings(diff_bundle):
    findings = []
    for file_info in diff_bundle.get("files", []):
        filename = file_info["filename"]
        for line_no, line in _added_lines(file_info.get("patch", "")):
            for rule in RULES:
                if rule["pattern"].search(line):
                    findings.append(
                        {
                            "type": "security",
                            "rule_id": rule["id"],
                            "severity": rule["severity"],
                            "file": filename,
                            "line": line_no,
                            "issue": rule["issue"],
                            "recommendation": rule["recommendation"],
                            "evidence": line.strip()[:160],
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
