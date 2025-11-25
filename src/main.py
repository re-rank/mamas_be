"""Main FastAPI application - MAMAS RAG Backend"""

import gc
import logging
import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# .env 파일 로드
load_dotenv()

from src.config import app_config as config
from src.api.routes import register_routes

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Windows 환경 UTF-8 설정
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 생명주기 관리"""
    # 시작 시
    logger.info("🚀 MAMAS RAG 서버 시작 중...")
    logger.info(f"📍 환경: {config.ENVIRONMENT}")
    logger.info(f"🗄️  Qdrant URL: {config.QDRANT_URL}")
    logger.info(f"📦 컬렉션: {config.COLLECTION_NAME}")
    
    # 필수 환경변수 확인
    errors = config.validate_config()
    if errors:
        for error in errors:
            logger.warning(f"⚠️  {error}")
    
    logger.info("✅ 서버 초기화 완료")
    
    yield
    
    # 종료 시
    logger.info("🛑 서버 종료 중...")
    gc.collect()
    logger.info("✅ 서버 종료 완료")


def create_app() -> FastAPI:
    """FastAPI 앱 생성"""
    
    app = FastAPI(
        title="MAMAS RAG API",
        description="Qdrant 기반 RAG 검색 시스템",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # CORS 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 전역 예외 처리
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"전역 예외: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "내부 서버 오류가 발생했습니다."}
        )
    
    @app.exception_handler(MemoryError)
    async def memory_error_handler(request: Request, exc: MemoryError):
        logger.critical("메모리 부족 오류!")
        gc.collect()
        return JSONResponse(
            status_code=503,
            content={"detail": "서버 메모리가 부족합니다."}
        )
    
    # 라우터 등록
    register_routes(app)
    
    # 루트 엔드포인트
    @app.get("/")
    async def root():
        return {
            "message": "MAMAS RAG API 서버",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs"
        }
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "MAMAS RAG API"}
    
    return app


# 앱 인스턴스 생성
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    host = config.HOST
    port = config.PORT
    
    logger.info(f"🚀 서버 시작: {host}:{port}")
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )

