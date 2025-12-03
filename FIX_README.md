# 검색 문제 해결 완료

## 문제 원인
1. **컬렉션 이름 불일치**: 설정값이 `mamas_documents`였으나 실제 DB는 `labor_consultant_docs` 사용
2. **검색 임계값이 너무 높음**: 0.5 → 0.3으로 조정 필요
3. **Qdrant API 메서드 오류**: `search()` → `query_points()` 메서드 사용

## 수정 사항
1. ✅ `src/config/app_config.py`: 기본 컬렉션명과 임계값 변경
2. ✅ `src/infrastructure/database/qdrant_manager.py`: 
   - `query_points()` 메서드로 변경
   - 컬렉션 정보 조회 버그 수정
3. ✅ `env.example`: 예제 설정 업데이트

## 필수 조치사항 ⚠️

### 방법 1: 자동 스크립트 실행 (추천)

**Windows:**
```cmd
update_env.bat
```

**Linux/Mac:**
```bash
chmod +x update_env.sh
./update_env.sh
```

### 방법 2: 수동 설정

**`.env` 파일을 직접 열어서 다음 두 줄을 수정하세요:**

```env
# 기존값 수정 또는 새로 추가
COLLECTION_NAME=labor_consultant_docs
SEARCH_SCORE_THRESHOLD=0.3
```

**`.env` 파일이 없다면:**
```bash
# env.example을 복사
cp env.example .env

# 그 후 위의 두 줄을 수정
```

## 서버 재시작
수정 후 서버를 재시작하세요:

```bash
# Windows
start.bat

# Linux/Mac
./start.sh
```

## 테스트 확인
```bash
python test_search.py
```

## 검색 결과 예시
- 쿼리: "식대+자가용운전지원금 40만원을 지급받는 중인데 이게 최저시급에 포함되나?"
- 결과: 3개 (점수 0.35~0.48)
- 상태: ✅ 정상 작동

---
생성일: 2025-12-01

