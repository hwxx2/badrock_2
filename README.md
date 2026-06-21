# 자동리뷰 Agent

리뷰를 자동 생성합니다. 리뷰 결과는 GitHub PR 댓글로 남기고, Discord로 완료 알림을 보냅니다.

## 아키텍처

```text
GitHub PR webhook
  -> API Gateway POST /review
  -> Orchestrator Lambda
  -> Bedrock Agent 또는 로컬 deterministic 리뷰 엔진
  -> Action Group Lambda tools
  -> GitHub PR 댓글 + Discord 알림 + CloudWatch 메트릭
```

## 제출 범위

- CloudFormation 기반 배포
- GitHub PR 자동 리뷰 댓글
- Discord 알림
- 월간 예상 비용 분석

## 사전 준비

- AWS CLI 로그인
- S3 버킷
- GitHub fine-grained token
- GitHub Webhook Secret
- Discord Webhook URL

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

## 수동 테스트

```bash
curl -X POST "$REVIEW_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{"pr_url":"https://github.com/OWNER/REPO/pull/1"}'
```

## 기대 결과

PR에 리뷰 댓글을 남깁니다.

- 리뷰 상태와 요약
- 높은/중간 심각도 보안 탐지 결과
- 복잡도 탐지 결과
- 리팩터링 제안

Discord에는 PR URL, 상태, 탐지 요약이 포함된 알림이 전송됩니다.

## 데모 체크리스트

1. 위험성이 높은 Python 코드가 포함된 PR을 엽니다.
2. Github PR 댓글을 보여줍니다.
3. Discord 알림을 보여줍니다.

## 로컬 테스트

```bash
python -m pytest tests
```

로컬 테스트는 AWS나 GitHub를 호출하지 않고, PR URL 파서와 deterministic 리뷰 엔진의 핵심 동작을 검증합니다.
