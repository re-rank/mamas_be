"""Chat API - RAG 기반 채팅 엔드포인트"""

import logging
from typing import Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.config import app_config as config
from src.infrastructure.database.qdrant_manager import QdrantManager
from src.services.embeddings.manager import EmbeddingManager
from src.services.search.search_service import SearchService
from src.services.llm.handler import LLMHandler

logger = logging.getLogger(__name__)

router = APIRouter()


# 의존성 주입을 위한 싱글톤 인스턴스
_qdrant_manager: Optional[QdrantManager] = None
_embedding_manager: Optional[EmbeddingManager] = None
_search_service: Optional[SearchService] = None
_llm_handler: Optional[LLMHandler] = None


def get_qdrant_manager() -> QdrantManager:
    """Qdrant 매니저 의존성"""
    global _qdrant_manager
    if _qdrant_manager is None:
        _qdrant_manager = QdrantManager()
    return _qdrant_manager


def get_embedding_manager() -> EmbeddingManager:
    """임베딩 매니저 의존성"""
    global _embedding_manager
    if _embedding_manager is None:
        _embedding_manager = EmbeddingManager()
    return _embedding_manager


def get_search_service() -> SearchService:
    """검색 서비스 의존성"""
    global _search_service
    if _search_service is None:
        _search_service = SearchService(
            qdrant_manager=get_qdrant_manager(),
            embedding_manager=get_embedding_manager()
        )
    return _search_service


def get_llm_handler() -> LLMHandler:
    """LLM 핸들러 의존성"""
    global _llm_handler
    if _llm_handler is None:
        _llm_handler = LLMHandler()
    return _llm_handler


# Request/Response 모델
class ChatMessage(BaseModel):
    """채팅 메시지"""
    role: str = Field(..., description="메시지 역할 (user/assistant)")
    content: str = Field(..., description="메시지 내용")


class ChatRequest(BaseModel):
    """채팅 요청"""
    message: str = Field(..., description="사용자 메시지", min_length=1)
    conversation_history: list[ChatMessage] = Field(
        default=[],
        description="대화 기록"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="검색할 문서 수"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM 온도"
    )
    collection_name: Optional[str] = Field(
        default=None,
        description="검색할 컬렉션 이름"
    )
    stream: bool = Field(
        default=False,
        description="스트리밍 응답 여부"
    )


class SearchResult(BaseModel):
    """검색 결과"""
    id: str
    score: float
    rank: int
    content: str
    title: str
    metadata: dict[str, Any] = {}


class ChatResponse(BaseModel):
    """채팅 응답"""
    answer: str = Field(..., description="AI 응답")
    search_results: list[SearchResult] = Field(
        default=[],
        description="검색 결과"
    )
    model: str = Field(default="", description="사용된 LLM 모델")
    usage: dict[str, int] = Field(
        default={},
        description="토큰 사용량"
    )
    success: bool = Field(default=True, description="성공 여부")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="응답 시간"
    )


class SearchRequest(BaseModel):
    """검색 요청"""
    query: str = Field(..., description="검색 쿼리", min_length=1)
    top_k: int = Field(default=5, ge=1, le=20, description="검색 결과 수")
    collection_name: Optional[str] = Field(default=None, description="컬렉션 이름")
    filters: dict[str, Any] = Field(default={}, description="필터 조건")


class SearchResponse(BaseModel):
    """검색 응답"""
    results: list[SearchResult]
    total: int
    query: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )


# API 엔드포인트
@router.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(
    request: ChatRequest,
    search_service: SearchService = Depends(get_search_service),
    llm_handler: LLMHandler = Depends(get_llm_handler)
):
    """
    RAG 기반 채팅 API
    
    1. 사용자 메시지로 관련 문서 검색
    2. 검색 결과를 컨텍스트로 LLM 답변 생성
    """
    try:
        logger.info(f"📨 채팅 요청: '{request.message[:50]}...'")
        
        # 스트리밍 응답
        if request.stream:
            return StreamingResponse(
                _stream_chat_response(request, search_service, llm_handler),
                media_type="text/event-stream"
            )

        # 검색 수행 (멀티 컬렉션 검색)
        search_results = _perform_search(request, search_service)

        # 대화 기록 변환
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]
        
        # 답변 생성
        result = llm_handler.generate_answer(
            question=request.message,
            search_results=search_results,
            conversation_history=history,
            temperature=request.temperature
        )
        
        # 응답 구성
        return ChatResponse(
            answer=result.get("answer", ""),
            search_results=[
                SearchResult(
                    id=r.get("id", ""),
                    score=r.get("score", 0.0),
                    rank=r.get("rank", 0),
                    content=r.get("content", ""),
                    title=r.get("title", ""),
                    metadata=r.get("metadata", {})
                )
                for r in search_results
            ],
            model=result.get("model", ""),
            usage=result.get("usage", {}),
            success=result.get("success", True)
        )
        
    except Exception as e:
        logger.error(f"❌ 채팅 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _perform_search(request: ChatRequest, search_service: SearchService) -> list[dict]:
    """멀티 컬렉션 검색 수행"""
    if request.collection_name:
        # 특정 컬렉션 지정 시 해당 컬렉션만 검색
        return search_service.search(
            query=request.message,
            top_k=request.top_k,
            collection_name=request.collection_name
        )

    # 기본: 모든 설정된 컬렉션에서 검색
    multi_results = search_service.multi_collection_search(
        query=request.message,
        collection_names=config.SEARCH_COLLECTIONS,
        top_k=request.top_k
    )

    # 모든 컬렉션 결과를 점수순으로 정렬하여 병합
    all_results = []
    for collection_name, results in multi_results.items():
        for r in results:
            r["collection"] = collection_name
        all_results.extend(results)

    # 점수순 정렬 후 top_k개 선택
    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    search_results = all_results[:request.top_k]

    # rank 재할당
    for i, r in enumerate(search_results):
        r["rank"] = i + 1

    logger.info(f"📊 멀티 컬렉션 검색 완료: {len(search_results)}개 결과")
    return search_results


async def _stream_chat_response(
    request: ChatRequest,
    search_service: SearchService,
    llm_handler: LLMHandler
):
    """스트리밍 응답 생성기"""
    try:
        # 검색 수행 (멀티 컬렉션 검색)
        search_results = _perform_search(request, search_service)

        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]
        
        # 스트리밍 답변 생성
        for chunk in llm_handler.generate_answer_stream(
            question=request.message,
            search_results=search_results,
            conversation_history=history,
            temperature=request.temperature
        ):
            yield f"data: {chunk}\n\n"
        
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        yield f"data: [ERROR] {str(e)}\n\n"


@router.post("/search", response_model=SearchResponse, tags=["search"])
async def search(
    request: SearchRequest,
    search_service: SearchService = Depends(get_search_service)
):
    """
    벡터 검색 API
    
    쿼리와 관련된 문서를 검색합니다.
    """
    try:
        logger.info(f"🔍 검색 요청: '{request.query[:50]}...'")
        
        if request.filters:
            results = search_service.search_with_filter(
                query=request.query,
                filters=request.filters,
                top_k=request.top_k,
                collection_name=request.collection_name
            )
        else:
            results = search_service.search(
                query=request.query,
                top_k=request.top_k,
                collection_name=request.collection_name
            )
        
        return SearchResponse(
            results=[
                SearchResult(
                    id=r.get("id", ""),
                    score=r.get("score", 0.0),
                    rank=r.get("rank", 0),
                    content=r.get("content", ""),
                    title=r.get("title", ""),
                    metadata=r.get("metadata", {})
                )
                for r in results
            ],
            total=len(results),
            query=request.query
        )
        
    except Exception as e:
        logger.error(f"❌ 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", tags=["health"])
async def health_check(
    qdrant_manager: QdrantManager = Depends(get_qdrant_manager)
):
    """헬스 체크 API"""
    try:
        collections = qdrant_manager.list_collections()
        return {
            "status": "healthy",
            "service": "MAMAS RAG API",
            "qdrant_connected": True,
            "collections_count": len(collections),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "MAMAS RAG API",
            "qdrant_connected": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/collections", tags=["admin"])
async def list_collections(
    qdrant_manager: QdrantManager = Depends(get_qdrant_manager)
):
    """컬렉션 목록 조회 API"""
    try:
        collections = qdrant_manager.list_collections()
        collection_info = []
        
        for name in collections:
            info = qdrant_manager.get_collection_info(name)
            if info:
                collection_info.append(info)
        
        return {
            "collections": collection_info,
            "total": len(collections)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache", tags=["admin"])
async def clear_cache(
    search_service: SearchService = Depends(get_search_service)
):
    """검색 캐시 초기화 API"""
    try:
        search_service.clear_cache()
        return {"message": "캐시가 초기화되었습니다", "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

