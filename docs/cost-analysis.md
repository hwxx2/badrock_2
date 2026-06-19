# CodeBuddy 비용 분석 보고서

## 산정 기준

- 리전: `ap-northeast-2`
- 사용량: 평일 기준 하루 100건 PR 리뷰, 월 22일 사용, 총 2,200건 리뷰
- 현재 데모 구성: `EnableBedrock=false`, 로컬 deterministic 리뷰 엔진 사용
- Lambda 설정: Orchestrator 1024MB / 300초 timeout, Action Group 512MB / 120초 timeout
- 실측 참고값: 2026-06-16 CloudWatch `ReviewDuration` 7건 평균 1.05초, 최소 0.93초, 최대 1.19초
- 실제 청구액은 AWS Free Tier, 리전별 단가, 선택 모델, 로그 보관량, 재시도 횟수에 따라 달라집니다.

## 월간 예상 비용 표

| 항목 | 산정 방식 | 현재 데모 예상 | Bedrock 활성화 시 예상 | 비고 |
|---|---:|---:|---:|---|
| API Gateway REST API | 2,200 calls/month | 약 $0.01 | 약 $0.01 | 요청 수가 매우 작아 비용 영향 낮음 |
| Orchestrator Lambda | 1GB, 보수적으로 평균 3초 가정 | 약 $0.11 | 약 $0.11~$0.55 | Bedrock 호출 대기 시간이 길면 증가 |
| Action Group Lambda | Bedrock 미사용 시 호출 없음 | $0.00 | 약 $0.05~$0.30 | Agent tool call 횟수에 따라 증가 |
| DynamoDB Review Cache | PAY_PER_REQUEST, 소형 item | $0.01 미만 | $0.01 미만 | 동일 commit 중복 리뷰 방지 |
| CloudWatch Logs/Metrics/Dashboard | 짧은 로그, 14일 보관 권장 | 약 $0.50~$2.00 | 약 $0.50~$3.00 | 로그 상세도와 보관 기간에 따라 증가 |
| S3 배포 아티팩트 | Lambda zip 1개, 낮은 요청량 | $0.05 미만 | $0.05 미만 | 배포 파일 저장용 |
| Bedrock Agent / 모델 호출 | 모델별 token 과금 | $0.00 | 약 $10~$150+ | Haiku급/ Sonnet급 모델 선택과 diff 크기에 따라 크게 달라짐 |
| OpenSearch Serverless Knowledge Base | 현재 템플릿에는 미포함 | $0.00 | 선택 시 별도 비용 | 항상 켜두면 비용이 크게 증가할 수 있음 |
| **합계** | 위 가정 합산 | **약 $1~$3/month** | **약 $12~$155+/month** | 학습/데모 단계는 Bedrock 비활성화가 안전 |

## 비용 절감 전략

- `owner/repo#pr:head_sha` 기준으로 리뷰 결과를 캐시해 같은 commit의 중복 호출을 막습니다.
- 큰 PR은 diff를 축약하고, 바이너리/생성 파일은 분석에서 제외합니다.
- 데모 중에는 `EnableBedrock=false`로 배포해 모델 호출 비용을 0으로 유지할 수 있습니다.
- Bedrock을 켤 때는 낮은 비용 모델로 먼저 검증하고, 필요한 PR에만 고성능 모델을 사용합니다.
- CloudWatch Log retention을 14일 이하로 제한하고, Bedrock trace는 디버깅 중에만 켭니다.
- Knowledge Base/OpenSearch Serverless는 과제 데모에 꼭 필요할 때만 구성합니다.

## 참고한 공식 가격 페이지

- AWS Lambda Pricing: https://aws.amazon.com/lambda/pricing/
- Amazon API Gateway Pricing: https://aws.amazon.com/api-gateway/pricing/
- Amazon DynamoDB Pricing: https://aws.amazon.com/dynamodb/pricing/
- Amazon Bedrock Pricing: https://aws.amazon.com/bedrock/pricing/
- Amazon OpenSearch Service Pricing: https://aws.amazon.com/opensearch-service/pricing/
