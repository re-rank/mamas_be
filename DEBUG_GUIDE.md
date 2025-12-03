# 🔧 긴급 디버깅 가이드

## 문제 상황
- Qdrant 쿼리는 성공 (HTTP 200 OK)
- `labor_consultant_docs` 컬렉션 사용 중 ✅
- 하지만 검색 결과 0개 ❌

## 원인 추정
검색 결과의 점수가 모두 `SEARCH_SCORE_THRESHOLD` 미만이어서 필터링됨

## 🚀 즉시 해결 방법

### 1단계: 서버 재시작
```bash
# 서버를 종료하고 다시 시작
start.bat
```

### 2단계: 설정 확인 API 호출
서버 시작 후 브라우저나 curl로 다음 URL 접속:
```
http://your-server:8000/api/system/config
```

**확인할 값:**
- `collection_name`: `"labor_consultant_docs"` 여야 함
- `search_score_threshold`: `0.0` 이어야 함 (임시)

### 3단계: 테스트
같은 질문을 다시 보내고 로그 확인:
```
🔍 Qdrant 검색 - 컬렉션: labor_consultant_docs, limit: 5, threshold: 0.0
📊 Qdrant 응답 - 원본 결과 수: X개
📈 최고 점수: 0.XXXX, 최저 점수: 0.XXXX
```

## 📊 디버깅 로그 추가사항

이제 다음과 같은 디버그 로그가 출력됩니다:
- 실제 사용 중인 threshold 값
- Qdrant가 반환한 원본 결과 수
- 점수 범위 (최고/최저)

## 🎯 예상 결과

**성공 시:**
```
✅ 검색 완료: 3개 결과 (또는 그 이상)
```

**여전히 0개라면:**
1. 벡터 임베딩이 올바르지 않음
2. 컬렉션에 데이터가 없음 (하지만 1625개 있다고 확인됨)
3. 다른 기술적 문제

## ⚠️ 임시 조치
현재 `SEARCH_SCORE_THRESHOLD`를 0.0으로 설정하여 **모든 결과를 반환**하도록 했습니다.
이것은 디버깅용이며, 실제 점수를 확인한 후 적절한 값(0.25~0.35)으로 조정해야 합니다.

---
생성일: 2025-12-01 13:20
