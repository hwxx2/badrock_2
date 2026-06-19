def suggest_refactors(diff_bundle, findings):
    suggestions = []
    if diff_bundle.get("truncated"):
        suggestions.append(
            {
                "severity": "Medium",
                "issue": "PR이 커서 diff 일부가 축약되었습니다.",
                "recommendation": "기계적인 변경과 동작 변경을 별도 PR로 나누세요.",
            }
        )

    security_count = len([item for item in findings if item.get("type") == "security"])
    complexity_count = len([item for item in findings if item.get("type") == "complexity"])

    if security_count:
        suggestions.append(
            {
                "severity": "High",
                "issue": f"보안 이슈 {security_count}건이 탐지되었습니다.",
                "recommendation": "병합 전에 높은 심각도 보안 항목을 수정하고 회귀 테스트를 추가하세요.",
            }
        )
    if complexity_count:
        suggestions.append(
            {
                "severity": "Medium",
                "issue": f"복잡도 관련 이슈 {complexity_count}건이 탐지되었습니다.",
                "recommendation": "작은 헬퍼 함수로 분리하고 공개 동작은 테스트로 보호하세요.",
            }
        )

    if not suggestions:
        suggestions.append(
            {
                "severity": "Low",
                "issue": "큰 리팩터링 필요성은 탐지되지 않았습니다.",
                "recommendation": "PR 범위를 작게 유지하고 변경된 동작에 대한 테스트를 추가하세요.",
            }
        )
    return suggestions
