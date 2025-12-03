"""Route registration"""

from fastapi import FastAPI

from src.api.v1.chat import router as chat_router
from src.api.v1.documents import router as documents_router
from src.api.v1.system import router as system_router


def register_routes(app: FastAPI) -> None:
    """모든 API 라우터 등록"""

    # Chat API - 루트 경로 (프론트엔드 호환)
    app.include_router(chat_router, tags=["chat"])

    # Chat API - /api prefix
    app.include_router(chat_router, prefix="/api", tags=["api"])

    # Documents API (문서 업로드, 관리)
    app.include_router(documents_router, prefix="/api/documents", tags=["documents"])
    
    # System API (설정 확인)
    app.include_router(system_router, prefix="/api/system", tags=["system"])

