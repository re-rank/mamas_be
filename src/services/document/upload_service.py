"""Document Upload Service - 문서 업로드 및 인덱싱"""

import logging
import hashlib
import uuid
from typing import Any, Optional
from datetime import datetime

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import app_config as config
from src.infrastructure.database.qdrant_manager import QdrantManager
from src.services.embeddings.manager import EmbeddingManager

logger = logging.getLogger(__name__)


class DocumentUploadService:
    """문서 업로드 및 벡터 DB 인덱싱 서비스"""
    
    def __init__(
        self,
        qdrant_manager: QdrantManager,
        embedding_manager: EmbeddingManager
    ):
        """문서 업로드 서비스 초기화"""
        self.qdrant_manager = qdrant_manager
        self.embedding_manager = embedding_manager
        
        # 텍스트 분할기 초기화
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ";", " ", ""]
        )
        
        logger.info("📄 문서 업로드 서비스 초기화 완료")
    
    def upload_document(
        self,
        content: str,
        title: str,
        metadata: Optional[dict[str, Any]] = None,
        collection_name: Optional[str] = None
    ) -> dict[str, Any]:
        """
        단일 문서 업로드 및 인덱싱
        
        Args:
            content: 문서 내용
            title: 문서 제목
            metadata: 추가 메타데이터
            collection_name: 대상 컬렉션 이름
        
        Returns:
            업로드 결과 정보
        """
        collection = collection_name or config.COLLECTION_NAME
        
        try:
            logger.info(f"📤 문서 업로드 시작: {title}")
            
            # 컬렉션 확인/생성
            if not self.qdrant_manager.collection_exists(collection):
                self.qdrant_manager.create_collection(collection)
            
            # 텍스트 분할
            chunks = self.text_splitter.split_text(content)
            logger.info(f"    청크 수: {len(chunks)}")
            
            if not chunks:
                return {
                    "success": False,
                    "error": "문서에서 텍스트를 추출할 수 없습니다",
                    "chunks_count": 0
                }
            
            # 문서 ID 생성
            doc_id = hashlib.md5(content.encode()).hexdigest()[:16]
            
            # 기본 메타데이터
            base_metadata = {
                "title": title,
                "document_id": doc_id,
                "uploaded_at": datetime.now().isoformat(),
                "total_chunks": len(chunks),
                **(metadata or {})
            }
            
            # 청크별 포인트 생성
            points = []
            chunk_texts = []
            
            for i, chunk in enumerate(chunks):
                point_id = f"{doc_id}_{i}"
                chunk_metadata = {
                    **base_metadata,
                    "chunk_index": i,
                    "content": chunk
                }
                
                points.append({
                    "id": point_id,
                    "vector": None,  # 나중에 추가
                    "payload": chunk_metadata
                })
                chunk_texts.append(chunk)
            
            # 배치 임베딩 생성
            logger.info("    임베딩 생성 중...")
            embeddings = self.embedding_manager.create_embeddings_batch(
                chunk_texts,
                input_type="document"
            )
            
            # 벡터 추가
            for point, embedding in zip(points, embeddings):
                point["vector"] = embedding
            
            # Qdrant에 업로드
            logger.info("    Qdrant에 업로드 중...")
            success = self.qdrant_manager.upsert_points(
                points=points,
                collection_name=collection,
                batch_size=config.UPLOAD_BATCH_SIZE
            )
            
            if success:
                logger.info(f"✅ 문서 업로드 완료: {title} ({len(chunks)}개 청크)")
                return {
                    "success": True,
                    "document_id": doc_id,
                    "title": title,
                    "chunks_count": len(chunks),
                    "collection": collection
                }
            else:
                return {
                    "success": False,
                    "error": "Qdrant 업로드 실패",
                    "chunks_count": len(chunks)
                }
            
        except Exception as e:
            logger.error(f"❌ 문서 업로드 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "chunks_count": 0
            }
    
    def upload_documents_batch(
        self,
        documents: list[dict[str, Any]],
        collection_name: Optional[str] = None
    ) -> dict[str, Any]:
        """
        다중 문서 배치 업로드
        
        Args:
            documents: 문서 목록 [{"content": str, "title": str, "metadata": dict}, ...]
            collection_name: 대상 컬렉션 이름
        
        Returns:
            업로드 결과 요약
        """
        results = {
            "total": len(documents),
            "success": 0,
            "failed": 0,
            "details": []
        }
        
        for doc in documents:
            result = self.upload_document(
                content=doc.get("content", ""),
                title=doc.get("title", "Untitled"),
                metadata=doc.get("metadata"),
                collection_name=collection_name
            )
            
            if result.get("success"):
                results["success"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append(result)
        
        logger.info(f"📦 배치 업로드 완료: {results['success']}/{results['total']} 성공")
        return results
    
    def delete_document(
        self,
        document_id: str,
        collection_name: Optional[str] = None
    ) -> bool:
        """문서 삭제 (모든 청크 삭제)"""
        collection = collection_name or config.COLLECTION_NAME
        
        try:
            # 문서 ID로 모든 청크 포인트 ID 조회
            # document_id 필터로 검색
            from qdrant_client.http import models
            
            # 스크롤로 모든 포인트 조회
            points, _ = self.qdrant_manager.client.scroll(
                collection_name=collection,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id)
                        )
                    ]
                ),
                limit=1000,
                with_payload=False
            )
            
            if not points:
                logger.warning(f"문서를 찾을 수 없음: {document_id}")
                return False
            
            point_ids = [str(p.id) for p in points]
            
            success = self.qdrant_manager.delete_points(point_ids, collection)
            if success:
                logger.info(f"✅ 문서 삭제 완료: {document_id} ({len(point_ids)}개 청크)")
            return success
            
        except Exception as e:
            logger.error(f"❌ 문서 삭제 실패: {e}")
            return False
    
    def get_document_info(
        self,
        document_id: str,
        collection_name: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
        """문서 정보 조회"""
        collection = collection_name or config.COLLECTION_NAME
        
        try:
            from qdrant_client.http import models
            
            # 문서의 첫 번째 청크 조회
            points, _ = self.qdrant_manager.client.scroll(
                collection_name=collection,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id)
                        )
                    ]
                ),
                limit=1,
                with_payload=True
            )
            
            if not points:
                return None
            
            payload = points[0].payload
            return {
                "document_id": document_id,
                "title": payload.get("title", ""),
                "total_chunks": payload.get("total_chunks", 0),
                "uploaded_at": payload.get("uploaded_at", ""),
                "metadata": {
                    k: v for k, v in payload.items()
                    if k not in ["content", "title", "document_id", "chunk_index", "total_chunks", "uploaded_at"]
                }
            }
            
        except Exception as e:
            logger.error(f"문서 정보 조회 실패: {e}")
            return None

