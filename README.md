# MAMAS RAG Backend

Qdrant Cloud를 활용한 RAG(Retrieval-Augmented Generation) 기반 검색 시스템

## 주요 기능

- 🔍 **벡터 검색**: Qdrant Cloud 기반 고성능 벡터 검색
- 🤖 **RAG 답변 생성**: OpenAI GPT를 활용한 컨텍스트 기반 답변
- 📊 **임베딩**: VoyageAI/OpenAI 임베딩 지원
- 📄 **문서 관리**: 문서 업로드, 인덱싱, 삭제 기능
- 💾 **캐싱**: 검색 결과 캐싱으로 성능 최적화
- 🌐 **REST API**: FastAPI 기반 RESTful API

## 기술 스택

- **Framework**: FastAPI
- **Vector DB**: Qdrant Cloud
- **LLM**: OpenAI GPT-4o-mini
- **Embeddings**: VoyageAI (voyage-3-large) / OpenAI
- **Language**: Python 3.10+

## 프로젝트 구조

```
mamas_be/
├── src/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── chat.py          # 채팅 & 검색 API
│   │   │   └── documents.py     # 문서 관리 API
│   │   └── routes.py            # 라우터 등록
│   ├── config/
│   │   └── app_config.py        # 설정
│   ├── infrastructure/
│   │   └── database/
│   │       └── qdrant_manager.py # Qdrant 매니저
│   ├── services/
│   │   ├── embeddings/
│   │   │   └── manager.py       # 임베딩 매니저
│   │   ├── llm/
│   │   │   └── handler.py       # LLM 핸들러
│   │   ├── search/
│   │   │   └── search_service.py # 검색 서비스
│   │   └── document/
│   │       └── upload_service.py # 문서 업로드
│   └── main.py                   # FastAPI 앱
├── requirements.txt
└── README.md
```

## 설치 및 실행

### 1. 환경 설정

```bash
# 파이썬 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정

`env.example` 파일을 참고하여 `.env` 파일 생성:

```env
# Qdrant 설정
QDRANT_URL=https://3d64fa5a-33ce-43f3-bf39-9ad85f5ef0ee.us-west-1-0.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.E6Gu12AWu-cv4uNVPpZUy_IeDj1TtSLS6fFu5AWeTD4

# OpenAI 설정
OPENAI_API_KEY=your_openai_api_key

# VoyageAI 설정 (선택)
VOYAGE_API_KEY=your_voyage_api_key
USE_VOYAGE_EMBEDDING=true

# 컬렉션 이름
COLLECTION_NAME=mamas_documents
```

### 3. 서버 실행

```bash
# 개발 서버
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 또는
python src/main.py
```

서버가 실행되면 다음 URL에서 확인:
- API 문서: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

## API 사용 예제

### 1. 채팅 API (RAG)

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "안녕하세요?",
    "top_k": 5,
    "temperature": 0.7
  }'
```

### 2. 검색 API

```bash
curl -X POST "http://localhost:8000/api/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "검색할 내용",
    "top_k": 5
  }'
```

### 3. 문서 업로드

```bash
curl -X POST "http://localhost:8000/api/documents/upload" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "문서 내용...",
    "title": "문서 제목",
    "metadata": {"category": "일반"}
  }'
```

### 4. 파일 업로드

```bash
curl -X POST "http://localhost:8000/api/documents/upload/file" \
  -F "file=@document.txt" \
  -F "title=내 문서"
```

## API 엔드포인트

### Chat & Search
- `POST /api/chat` - RAG 기반 채팅
- `POST /api/search` - 벡터 검색
- `GET /api/health` - 헬스 체크
- `GET /api/collections` - 컬렉션 목록
- `DELETE /api/cache` - 캐시 초기화

### Documents
- `POST /api/documents/upload` - 문서 업로드 (JSON)
- `POST /api/documents/upload/file` - 파일 업로드
- `POST /api/documents/upload/batch` - 배치 업로드
- `GET /api/documents/{document_id}` - 문서 정보 조회
- `DELETE /api/documents/{document_id}` - 문서 삭제

## 설정 옵션

주요 환경변수:

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `QDRANT_URL` | Qdrant 서버 URL | 필수 |
| `QDRANT_API_KEY` | Qdrant API 키 | 필수 |
| `OPENAI_API_KEY` | OpenAI API 키 | 필수 |
| `VOYAGE_API_KEY` | VoyageAI API 키 | 선택 |
| `USE_VOYAGE_EMBEDDING` | VoyageAI 사용 여부 | true |
| `LLM_MODEL` | LLM 모델 | gpt-4o-mini |
| `LLM_TEMPERATURE` | LLM 온도 | 0.7 |
| `DEFAULT_SEARCH_K` | 기본 검색 결과 수 | 5 |
| `ENABLE_SEARCH_CACHE` | 검색 캐시 활성화 | true |
| `CACHE_TTL_SECONDS` | 캐시 유지 시간 (초) | 300 |
| `CHUNK_SIZE` | 청킹 크기 | 1000 |
| `CHUNK_OVERLAP` | 청킹 오버랩 | 200 |

## 개발

### 코드 스타일

```bash
# 린트 체크
flake8 src/

# 포맷팅
black src/

# 타입 체크
mypy src/
```

### 테스트

```bash
# 테스트 실행
pytest

# 커버리지
pytest --cov=src tests/
```

## 배포

### Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# 빌드
docker build -t mamas-rag-backend .

# 실행
docker run -p 8000:8000 --env-file .env mamas-rag-backend
```

## 참고

- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Qdrant 문서](https://qdrant.tech/documentation/)
- [VoyageAI 문서](https://docs.voyageai.com/)
- [OpenAI 문서](https://platform.openai.com/docs/)

## 라이선스

MIT License

