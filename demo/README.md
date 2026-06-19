# 데모 녹화 가이드

45초에서 60초 정도의 짧은 데모 영상을 권장합니다.

1. 의도적으로 문제가 있는 코드가 포함된 GitHub PR을 보여줍니다.
2. GitHub webhook delivery 또는 `/review` 엔드포인트 수동 호출을 보여줍니다.
3. Lambda 로그 스트림에서 요청이 처리되는 장면을 보여줍니다.
4. CodeBuddy가 남긴 한국어 PR 리뷰 댓글을 보여줍니다.
5. Discord에 도착한 한국어 알림을 보여줍니다.
6. CloudWatch Dashboard의 `ReviewDuration`, `Success`, `Failure` 메트릭으로 마무리합니다.

## 데모용 문제 코드 예시

```python
API_KEY = "12345"

def get_user(cursor, id):
    query = f"SELECT * FROM users WHERE id = {id}"
    return cursor.execute(query)
```

위 코드는 하드코딩된 시크릿과 SQL Injection 위험을 동시에 만들기 때문에 CodeBuddy의 탐지 결과를 보여주기 좋습니다.
