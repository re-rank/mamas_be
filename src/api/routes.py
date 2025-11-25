"""Route registration"""

from fastapi import FastAPI

from src.api.v1.chat import router as chat_router
from src.api.v1.documents import router as documents_router


def register_routes(app: FastAPI) -> None:
    """모든 API 라우터 등록"""
    
    # Chat API (검색, 채팅, 헬스체크 포함)
    app.include_router(chat_router, prefix="/api", tags=["api"])
    
    # Documents API (문서 업로드, 관리)
    app.include_router(documents_router, prefix="/api/documents", tags=["documents"])

