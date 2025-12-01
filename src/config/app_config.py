"""Configuration settings for MAMAS Backend"""

import logging
import os
from dotenv import load_dotenv

# 로깅 설정
logger = logging.getLogger(__name__)

# .env 파일 로드
for _env in ('.env', '.env.local'):
    if os.path.exists(_env):
        try:
            load_dotenv(_env)
            logger.info(f"{_env} 파일 로드됨")
        except Exception:
            pass

# 환경 설정
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# Qdrant 설정
QDRANT_URL = os.getenv("QDRANT_URL", "https://3d64fa5a-33ce-43f3-bf39-9ad85f5ef0ee.us-west-1-0.aws.cloud.qdrant.io:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")

# OpenAI 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# VoyageAI 설정
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")
USE_VOYAGE_EMBEDDING = os.getenv("USE_VOYAGE_EMBEDDING", "true").lower() == "true"
VOYAGE_MODEL_NAME = "voyage-3-large"

# 임베딩 설정
EMBEDDING_MODEL = VOYAGE_MODEL_NAME if USE_VOYAGE_EMBEDDING else "text-embedding-3-small"
VECTOR_SIZE = 1024  # voyage-3-large 차원

# LLM 설정
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2000"))

# 검색 설정
DEFAULT_SEARCH_K = int(os.getenv("DEFAULT_SEARCH_K", "5"))
MAX_SEARCH_K = int(os.getenv("MAX_SEARCH_K", "20"))
SEARCH_SCORE_THRESHOLD = float(os.getenv("SEARCH_SCORE_THRESHOLD", "0.3"))

# 서버 설정
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# CORS 설정
_default_cors = ",".join([
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://rag-murex-seven.vercel.app",
])
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", _default_cors).split(",")]

# 캐시 설정
ENABLE_SEARCH_CACHE = os.getenv("ENABLE_SEARCH_CACHE", "true").lower() == "true"
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "100"))

# 컬렉션 설정
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "labor_consultant_docs")

# 로깅 설정
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO" if IS_PRODUCTION else "DEBUG")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 청킹 설정
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# 타임아웃 설정
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "120"))

# 배치 설정
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "100"))
UPLOAD_BATCH_SIZE = int(os.getenv("UPLOAD_BATCH_SIZE", "100"))


def validate_config() -> list[str]:
    """환경변수 검증"""
    errors = []
    
    if not QDRANT_URL:
        errors.append("QDRANT_URL이 설정되지 않았습니다")
    if not QDRANT_API_KEY:
        errors.append("QDRANT_API_KEY가 설정되지 않았습니다")
    if not OPENAI_API_KEY and not VOYAGE_API_KEY:
        errors.append("OPENAI_API_KEY 또는 VOYAGE_API_KEY가 설정되지 않았습니다")
    
    for error in errors:
        logger.warning(f"⚠️ {error}")
    
    return errors


def print_config_summary() -> None:
    """설정 요약 출력"""
    logger.info("=== 설정 요약 ===")
    logger.info(f"환경: {ENVIRONMENT}")
    logger.info(f"임베딩 모델: {EMBEDDING_MODEL}")
    logger.info(f"LLM 모델: {LLM_MODEL}")
    logger.info(f"벡터 차원: {VECTOR_SIZE}")
    logger.info(f"컬렉션: {COLLECTION_NAME}")
    logger.info(f"캐시 활성화: {ENABLE_SEARCH_CACHE}")
    logger.info("================")

