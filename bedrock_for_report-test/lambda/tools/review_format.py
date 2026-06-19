def compose_review(pr, diff_bundle, findings, tests, refactors, bedrock_text=None, duration_seconds=None):
    high_count = len([item for item in findings if item.get("severity") == "High"])
    medium_count = len([item for item in findings if item.get("severity") == "Medium"])
    status = "수정 요청" if high_count else "검토 완료"

    lines = [
        "## CodeBuddy 리뷰",
        "",
        f"**상태:** {status}",
        "",
        "### 요약",
        f"- 분석한 변경 파일: {diff_bundle.get('included_files', 0)} / {diff_bundle.get('total_files', 0)}",
        f"- 건너뛴 바이너리 또는 미지원 파일: {len(diff_bundle.get('skipped', []))}",
        f"- 높은 심각도 이슈: {high_count}",
        f"- 중간 심각도 이슈: {medium_count}",
    ]
    if duration_seconds is not None:
        lines.append(f"- 리뷰 소요 시간: {duration_seconds:.2f}초")
    if diff_bundle.get("truncated"):
        lines.append("- 큰 PR 처리: 모델 안전성을 위해 diff 일부를 분할하거나 축약했습니다.")
    lines.append("")

    if bedrock_text:
        lines.extend(["### Bedrock Agent 추가 의견", _trim(bedrock_text, 2500), ""])

    lines.append("### 탐지 결과")
    if findings:
        lines.extend(["| 심각도 | 파일 | 줄 | 이슈 | 권장 조치 |", "|---|---|---:|---|---|"])
        for item in findings[:20]:
            lines.append(
                "| {severity} | `{file}` | {line} | {issue} | {recommendation} |".format(
                    severity=_severity_label(item.get("severity", "Info")),
                    file=item.get("file", ""),
                    line=item.get("line") or "",
                    issue=_escape_table(item.get("issue", "")),
                    recommendation=_escape_table(item.get("recommendation", "")),
                )
            )
    else:
        lines.append("병합을 막을 만한 주요 이슈는 탐지되지 않았습니다.")
    lines.append("")

    lines.append("### 권장 테스트")
    for test in tests[:3]:
        lines.append(f"**{test['title']}**")
        lines.append("")
        lines.append("```python")
        lines.append(test["code"].strip())
        lines.append("```")
    lines.append("")

    lines.append("### 리팩터링 제안")
    for item in refactors[:5]:
        lines.append(f"- **{_severity_label(item['severity'])}**: {item['issue']} {item['recommendation']}")
    lines.append("")

    if diff_bundle.get("skipped"):
        skipped = ", ".join(item["filename"] for item in diff_bundle["skipped"][:10])
        lines.extend(["### 건너뛴 파일", skipped, ""])

    lines.append("_CodeBuddy가 자동 생성한 리뷰입니다._")
    return "\n".join(lines)


def summary_for_notification(findings):
    high_count = len([item for item in findings if item.get("severity") == "High"])
    medium_count = len([item for item in findings if item.get("severity") == "Medium"])
    return f"높은 심각도 {high_count}건, 중간 심각도 {medium_count}건입니다. 자세한 내용은 PR 댓글을 확인하세요."


def _severity_label(value):
    return {
        "High": "높음",
        "Medium": "중간",
        "Low": "낮음",
        "Info": "정보",
    }.get(value, value)


def _trim(text, limit):
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit] + "\n..."


def _escape_table(value):
    return str(value).replace("|", "\\|").replace("\n", " ")
