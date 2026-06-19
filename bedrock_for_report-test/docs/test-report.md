# CodeBuddy 테스트 리포트

## 테스트 환경

- 테스트 일자: 2026-06-16
- AWS 리전: `ap-northeast-2`
- 배포 스택: `CodeBuddyStack`
- 기본 브랜치: `test`
- 데모 PR 브랜치: `codex/broken-review-sample`
- Bedrock 설정: 데모 단계에서는 `EnableBedrock=false`

## 기능 테스트

| 테스트 | 입력/상황 | 기대 결과 | 상태 |
|---|---|---|---|
| 수동 PR 리뷰 | `{"pr_url":"https://github.com/OWNER/REPO/pull/1"}` | PR 댓글과 Discord 알림 생성 | 통과 |
| GitHub webhook | `pull_request.opened` 또는 `synchronize` + 유효한 서명 | 리뷰 Lambda 실행 | 통과 |
| 닫힌 PR 이벤트 무시 | `pull_request.closed` | HTTP 202, 리뷰 미실행 | 통과 |
| 잘못된 PR URL | `{"pr_url":"invalid"}` | HTTP 400 | 통과 |
| 빈 PR | 변경 파일 없음 | 주요 이슈 없음으로 댓글 생성 | 준비 |
| 바이너리 파일 포함 | `.png`, `.pdf` 변경 | 바이너리는 건너뛰고 코드 파일만 분석 | 준비 |
| 큰 PR | 80개 초과 파일 또는 45k chars 초과 diff | diff 축약 및 경고 표시 | 준비 |
| 동시 PR | 여러 webhook 연속 수신 | request ID별 독립 처리 | 준비 |
| Discord 전송 | Lambda에서 Discord webhook 호출 | HTTP 204, 한글 알림 수신 | 통과 |

## 엣지 케이스 테스트

| 케이스 | 위험 | 방어/처리 방식 |
|---|---|---|
| GitHub 서명 누락 | 외부 임의 호출 가능성 | GitHub webhook이면 `X-Hub-Signature-256` 필수 |
| GitHub 서명 불일치 | webhook secret 불일치 또는 위조 요청 | HMAC 비교 실패 시 400 반환 |
| GitHub token 권한 부족 | PR 댓글 작성 실패 | GitHub API 오류를 502로 반환하고 로그 기록 |
| Discord webhook 403 | 알림 누락 | `User-Agent` 명시 및 HTTPError 상태/본문 기록 |
| 동일 commit 재전송 | 중복 댓글 생성 | DynamoDB cache key로 중복 리뷰 차단 |
| Bedrock Agent 미설정 | 모델 호출 실패 가능성 | `EnableBedrock=false`일 때 로컬 리뷰 엔진만 사용 |
| 대형 diff | token 비용/timeout 증가 | diff truncation과 binary skip 적용 |
| 민감 정보 로그 | 토큰/비밀번호 노출 | 리뷰 룰에서 debug secret logging 탐지 |

## 보안 탐지 테스트

| 위험 | 샘플 | 기대 탐지 |
|---|---|---|
| SQL Injection | `f"SELECT * FROM users WHERE id = {id}"` | 높은 심각도 |
| 하드코딩된 시크릿 | `API_KEY = "12345"` | 높은 심각도 |
| unsafe pickle | `pickle.loads(data)` | 높은 심각도 |
| 민감 로그 | `print(secret_token)` | 중간 심각도 |
| shell injection | `subprocess.run(cmd, shell=True)` | 중간 심각도 |
| unsafe YAML | `yaml.load(raw_config)` | 중간 심각도 |

## 성능 측정 결과

| 지표 | 측정 방법 | 결과 | 판단 |
|---|---|---:|---|
| 로컬 단위 테스트 | `uv run --with pytest python -m pytest tests` | 4 passed, 0.34초 | 통과 |
| 리뷰 처리 시간 평균 | CloudWatch `CodeBuddy/ReviewDuration`, 최근 24시간 | 1.05초 | 목표 30초 이내 |
| 리뷰 처리 시간 최댓값 | CloudWatch `CodeBuddy/ReviewDuration`, 최근 24시간 | 1.19초 | 목표 30초 이내 |
| 성공 처리 수 | CloudWatch `CodeBuddy/Success`, 최근 24시간 | 7건 | 데모 요청 정상 처리 |
| Discord 전송 | Lambda action group smoke test | HTTP 204 | 정상 |

## 제출 증거로 캡처할 화면

- GitHub PR에 생성된 CodeBuddy 한국어 리뷰 댓글
- Discord에 도착한 한국어 알림
- GitHub Webhook delivery의 성공 응답
- CloudFormation `CodeBuddyStack` 상태
- CloudWatch `ReviewDuration`, `Success`, `Failure` 메트릭
- 로컬 `uv run --with pytest python -m pytest tests` 실행 결과
