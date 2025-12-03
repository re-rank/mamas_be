"""System/Config API endpoints"""

from fastapi import APIRouter
from typing import Dict, Any

from src.config import app_config

router = APIRouter()


@router.get("/config")
async def get_config() -> Dict[str, Any]:
    """현재 시스템 설정 확인"""
    return {
        "environment": app_config.ENVIRONMENT,
        "collection_name": app_config.COLLECTION_NAME,
        "search_score_threshold": app_config.SEARCH_SCORE_THRESHOLD,
        "vector_size": app_config.VECTOR_SIZE,
        "embedding_model": app_config.EMBEDDING_MODEL,
        "llm_model": app_config.LLM_MODEL,
        "default_search_k": app_config.DEFAULT_SEARCH_K,
    }

