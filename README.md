# CodeBuddy Agent

CodeBuddy는 GitHub Pull Request를 자동으로 검토하는 Bedrock 기반 리뷰 에이전트입니다. GitHub 웹훅을 API Gateway로 받고, Lambda Orchestrator가 변경 파일을 수집한 뒤 보안/복잡도/테스트 관점의 리뷰를 생성합니다. 리뷰 결과는 GitHub PR 댓글로 남기고, Discord로 완료 알림을 보냅니다.

## 아키텍처

```text
GitHub PR webhook
  -> API Gateway POST /review
  -> Orchestrator Lambda
  -> Bedrock Agent 또는 로컬 deterministic 리뷰 엔진
  -> Action Group Lambda tools
  -> GitHub PR 댓글 + Discord 알림 + CloudWatch 메트릭
```

Bedrock Agent가 아직 준비되지 않았거나 데모 비용을 줄이고 싶을 때는 `EnableBedrock=false`로 배포할 수 있습니다. 이 경우에도 CodeBuddy는 로컬 리뷰 엔진으로 SQL Injection, 하드코딩된 시크릿, unsafe pickle/yaml, `shell=True`, 민감 로그, 복잡도 이슈를 탐지하고 유용한 PR 댓글을 생성합니다.

## 제출 범위

- CloudFormation 기반 API Gateway, Lambda, IAM, DynamoDB 캐시, API key, throttling, CloudWatch Dashboard 배포
- GitHub PR URL 파싱, 변경 파일 조회, 바이너리 파일 제외, 큰 PR diff 축약
- GitHub PR 자동 리뷰 댓글
- Discord 한글 알림
- 보안/복잡도/테스트/리팩터링 제안
- 월간 예상 비용 분석 보고서: [docs/cost-analysis.md](docs/cost-analysis.md)
- 엣지 케이스 및 성능 측정 테스트 리포트: [docs/test-report.md](docs/test-report.md)
- Bedrock Agent Action Group OpenAPI 스키마: [docs/action-group-openapi.yaml](docs/action-group-openapi.yaml)

## 사전 준비

- AWS CLI 로그인 및 `ap-northeast-2` 리전 사용
- Lambda 배포 아티팩트용 S3 버킷
- GitHub fine-grained token: repository contents read, pull requests read, issues write 권한
- GitHub Webhook Secret
- Discord Webhook URL
- Bedrock Agent를 사용할 경우 Agent ID와 Agent Alias ID

## 배포

PowerShell:

```powershell
.\scripts\deploy.ps1 `
  -Bucket codebuddy-artifacts-ACCOUNT-ap-northeast-2 `
  -StackName CodeBuddyStack `
  -AgentId disabled `
  -AgentAliasId disabled `
  -EnableBedrock false `
  -GitHubToken $GitHubToken `
  -GitHubWebhookSecret $GitHubWebhookSecret `
  -DiscordWebhookUrl $DiscordWebhookUrl
```

Bedrock Agent를 연결한 뒤에는 `AgentId`, `AgentAliasId`, `EnableBedrock` 값을 실제 값으로 바꿔 다시 배포합니다.

## GitHub Webhook 설정

CloudFormation 출력값의 `ReviewEndpoint`를 GitHub webhook payload URL로 사용합니다.

- Content type: `application/json`
- Secret: CloudFormation 파라미터 `GitHubWebhookSecret`과 같은 값
- Events: `Pull requests`

GitHub webhook은 임의의 API key 헤더를 붙일 수 없으므로, 요청 보호는 `X-Hub-Signature-256` 서명 검증으로 처리합니다. API Gateway throttling은 과도한 요청을 제한하고, 스택은 수동 테스트용 API key도 함께 생성합니다.

## Bedrock Agent Action Group 설정

- Action Group 스키마: [docs/action-group-openapi.yaml](docs/action-group-openapi.yaml)
- Action Group Lambda target: CloudFormation 출력값 `ActionGroupFunctionArn`
- Agent instruction: [docs/bedrock-agent-instructions.md](docs/bedrock-agent-instructions.md)

## 수동 테스트

```bash
curl -X POST "$REVIEW_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{"pr_url":"https://github.com/OWNER/REPO/pull/1"}'
```

실제 GitHub webhook 테스트에서는 `X-Hub-Signature-256`, `X-GitHub-Delivery`, `X-GitHub-Event` 헤더가 함께 전달됩니다.

## 기대 결과

CodeBuddy는 PR에 한국어 Markdown 리뷰 댓글을 남깁니다.

- 리뷰 상태와 요약
- 높은/중간 심각도 보안 탐지 결과
- 복잡도 탐지 결과
- 권장 pytest 코드
- 리팩터링 제안
- 처리 시간, 큰 PR 축약, 바이너리 파일 제외 같은 운영 메타데이터

Discord에는 PR URL, 상태, 탐지 요약이 포함된 한글 알림이 전송됩니다.

## 데모 체크리스트

1. 일부러 위험한 Python 코드가 포함된 PR을 엽니다.
2. GitHub webhook delivery가 성공한 것을 보여줍니다.
3. CloudWatch Logs 또는 Dashboard에서 Lambda 실행을 보여줍니다.
4. CodeBuddy의 한국어 PR 댓글을 보여줍니다.
5. Discord 한글 알림을 보여줍니다.
6. 비용 분석 보고서와 테스트 리포트를 제출 자료에 포함합니다.

## 로컬 테스트

```bash
python -m pytest tests
```

로컬 테스트는 AWS나 GitHub를 호출하지 않고, PR URL 파서와 deterministic 리뷰 엔진의 핵심 동작을 검증합니다.
