"""Documents API - 문서 업로드 및 관리 엔드포인트"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel, Field

from src.api.v1.chat import get_qdrant_manager, get_embedding_manager
from src.infrastructure.database.qdrant_manager import QdrantManager
from src.services.embeddings.manager import EmbeddingManager
from src.services.document.upload_service import DocumentUploadService

logger = logging.getLogger(__name__)

router = APIRouter()

# 의존성
_upload_service: Optional[DocumentUploadService] = None


def get_upload_service() -> DocumentUploadService:
    """문서 업로드 서비스 의존성"""
    global _upload_service
    if _upload_service is None:
        _upload_service = DocumentUploadService(
            qdrant_manager=get_qdrant_manager(),
            embedding_manager=get_embedding_manager()
        )
    return _upload_service


# Request/Response 모델
class DocumentUploadRequest(BaseModel):
    """문서 업로드 요청"""
    content: str = Field(..., description="문서 내용", min_length=10)
    title: str = Field(..., description="문서 제목", min_length=1)
    metadata: dict[str, Any] = Field(default={}, description="추가 메타데이터")
    collection_name: Optional[str] = Field(default=None, description="컬렉션 이름")


class DocumentUploadResponse(BaseModel):
    """문서 업로드 응답"""
    success: bool
    document_id: Optional[str] = None
    title: Optional[str] = None
    chunks_count: int = 0
    collection: Optional[str] = None
    error: Optional[str] = None


class BatchUploadRequest(BaseModel):
    """배치 업로드 요청"""
    documents: list[dict[str, Any]] = Field(..., description="문서 목록")
    collection_name: Optional[str] = Field(default=None, description="컬렉션 이름")


class BatchUploadResponse(BaseModel):
    """배치 업로드 응답"""
    total: int
    success: int
    failed: int
    details: list[dict[str, Any]]


class DocumentInfoResponse(BaseModel):
    """문서 정보 응답"""
    document_id: str
    title: str
    total_chunks: int
    uploaded_at: str
    metadata: dict[str, Any]


# API 엔드포인트
@router.post("/upload", response_model=DocumentUploadResponse, tags=["documents"])
async def upload_document(
    request: DocumentUploadRequest,
    upload_service: DocumentUploadService = Depends(get_upload_service)
):
    """
    문서 업로드 API
    
    텍스트 문서를 청킹하고 벡터 DB에 인덱싱합니다.
    """
    try:
        result = upload_service.upload_document(
            content=request.content,
            title=request.title,
            metadata=request.metadata,
            collection_name=request.collection_name
        )
        
        return DocumentUploadResponse(**result)
        
    except Exception as e:
        logger.error(f"문서 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/batch", response_model=BatchUploadResponse, tags=["documents"])
async def upload_documents_batch(
    request: BatchUploadRequest,
    upload_service: DocumentUploadService = Depends(get_upload_service)
):
    """
    배치 문서 업로드 API
    
    여러 문서를 한 번에 업로드합니다.
    """
    try:
        result = upload_service.upload_documents_batch(
            documents=request.documents,
            collection_name=request.collection_name
        )
        
        return BatchUploadResponse(**result)
        
    except Exception as e:
        logger.error(f"배치 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/file", response_model=DocumentUploadResponse, tags=["documents"])
async def upload_file(
    file: UploadFile = File(...),
    title: str = Form(None),
    collection_name: str = Form(None),
    upload_service: DocumentUploadService = Depends(get_upload_service)
):
    """
    파일 업로드 API
    
    텍스트 파일(.txt)을 업로드하고 인덱싱합니다.
    """
    try:
        # 파일 내용 읽기
        content = await file.read()
        
        # 텍스트 디코딩 시도
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text_content = content.decode('cp949')
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="파일 인코딩을 인식할 수 없습니다")
        
        # 제목 설정
        doc_title = title or file.filename or "Untitled"
        
        result = upload_service.upload_document(
            content=text_content,
            title=doc_title,
            metadata={"filename": file.filename, "content_type": file.content_type},
            collection_name=collection_name
        )
        
        return DocumentUploadResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}", response_model=DocumentInfoResponse, tags=["documents"])
async def get_document_info(
    document_id: str,
    collection_name: Optional[str] = None,
    upload_service: DocumentUploadService = Depends(get_upload_service)
):
    """문서 정보 조회 API"""
    try:
        info = upload_service.get_document_info(document_id, collection_name)
        
        if not info:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
        
        return DocumentInfoResponse(**info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}", tags=["documents"])
async def delete_document(
    document_id: str,
    collection_name: Optional[str] = None,
    upload_service: DocumentUploadService = Depends(get_upload_service)
):
    """문서 삭제 API"""
    try:
        success = upload_service.delete_document(document_id, collection_name)
        
        if not success:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다")
        
        return {"message": "문서가 삭제되었습니다", "document_id": document_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

