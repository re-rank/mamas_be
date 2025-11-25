"""Search Service - RAG 기반 검색 서비스"""

import logging
from typing import Any, Optional
from cachetools import TTLCache

from src.config import app_config as config
from src.infrastructure.database.qdrant_manager import QdrantManager
from src.services.embeddings.manager import EmbeddingManager

logger = logging.getLogger(__name__)


class SearchService:
    """RAG 기반 검색 서비스"""
    
    def __init__(
        self,
        qdrant_manager: QdrantManager,
        embedding_manager: EmbeddingManager
    ):
        """검색 서비스 초기화"""
        self.qdrant_manager = qdrant_manager
        self.embedding_manager = embedding_manager
        
        # 검색 캐시
        if config.ENABLE_SEARCH_CACHE:
            self.cache = TTLCache(
                maxsize=config.CACHE_MAX_SIZE,
                ttl=config.CACHE_TTL_SECONDS
            )
        else:
            self.cache = None
        
        logger.info("🔍 검색 서비스 초기화 완료")
    
    def _get_cache_key(self, query: str, top_k: int, collection_name: str) -> str:
        """캐시 키 생성"""
        return f"{collection_name}:{top_k}:{hash(query)}"
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        collection_name: Optional[str] = None,
        score_threshold: Optional[float] = None,
        use_cache: bool = True
    ) -> list[dict[str, Any]]:
        """쿼리 기반 벡터 검색 수행"""
        collection = collection_name or config.COLLECTION_NAME
        threshold = score_threshold or config.SEARCH_SCORE_THRESHOLD
        
        # 캐시 확인
        if use_cache and self.cache is not None:
            cache_key = self._get_cache_key(query, top_k, collection)
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info(f"✅ 캐시 적중: '{query[:30]}...'")
                return cached_result
        
        try:
            # 쿼리 임베딩 생성
            logger.info(f"🔍 검색 시작: '{query[:50]}...'")
            query_vector = self.embedding_manager.create_query_embedding(query)
            
            # 벡터 검색 수행
            results = self.qdrant_manager.search(
                query_vector=query_vector,
                collection_name=collection,
                limit=top_k,
                score_threshold=threshold
            )
            
            # 결과 후처리
            processed_results = self._process_search_results(results, query)
            
            # 캐시 저장
            if use_cache and self.cache is not None and processed_results:
                cache_key = self._get_cache_key(query, top_k, collection)
                self.cache[cache_key] = processed_results
            
            logger.info(f"✅ 검색 완료: {len(processed_results)}개 결과")
            return processed_results
            
        except Exception as e:
            logger.error(f"❌ 검색 실패: {e}")
            return []
    
    def _process_search_results(
        self,
        results: list[dict],
        query: str
    ) -> list[dict[str, Any]]:
        """검색 결과 후처리"""
        processed = []
        
        for i, result in enumerate(results):
            payload = result.get("payload", {})
            
            processed_item = {
                "id": result.get("id"),
                "score": result.get("score", 0.0),
                "rank": i + 1,
                "content": payload.get("content", payload.get("text", "")),
                "title": payload.get("title", ""),
                "metadata": {
                    k: v for k, v in payload.items()
                    if k not in ["content", "text", "title", "vector"]
                }
            }
            processed.append(processed_item)
        
        return processed
    
    def search_with_filter(
        self,
        query: str,
        filters: dict[str, Any],
        top_k: int = 5,
        collection_name: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """필터를 적용한 검색"""
        collection = collection_name or config.COLLECTION_NAME
        
        try:
            query_vector = self.embedding_manager.create_query_embedding(query)
            
            # 필터 조건 구성
            must_conditions = []
            for key, value in filters.items():
                if value is not None:
                    must_conditions.append({"key": key, "match": value})
            
            results = self.qdrant_manager.search_with_payload_filter(
                query_vector=query_vector,
                collection_name=collection,
                limit=top_k,
                must_conditions=must_conditions if must_conditions else None
            )
            
            return self._process_search_results(results, query)
            
        except Exception as e:
            logger.error(f"필터 검색 실패: {e}")
            return []
    
    def multi_collection_search(
        self,
        query: str,
        collection_names: list[str],
        top_k: int = 5
    ) -> dict[str, list[dict[str, Any]]]:
        """여러 컬렉션에서 동시 검색"""
        results = {}
        
        try:
            query_vector = self.embedding_manager.create_query_embedding(query)
            
            for collection in collection_names:
                try:
                    collection_results = self.qdrant_manager.search(
                        query_vector=query_vector,
                        collection_name=collection,
                        limit=top_k
                    )
                    results[collection] = self._process_search_results(
                        collection_results, query
                    )
                except Exception as e:
                    logger.warning(f"컬렉션 '{collection}' 검색 실패: {e}")
                    results[collection] = []
            
            return results
            
        except Exception as e:
            logger.error(f"멀티 컬렉션 검색 실패: {e}")
            return {name: [] for name in collection_names}
    
    def get_similar_documents(
        self,
        document_id: str,
        top_k: int = 5,
        collection_name: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """특정 문서와 유사한 문서 검색"""
        collection = collection_name or config.COLLECTION_NAME
        
        try:
            # 문서 조회
            docs = self.qdrant_manager.get_points_by_ids(
                [document_id],
                collection
            )
            
            if not docs:
                logger.warning(f"문서를 찾을 수 없음: {document_id}")
                return []
            
            # 문서 내용으로 검색
            content = docs[0].get("payload", {}).get("content", "")
            if not content:
                return []
            
            results = self.search(
                query=content,
                top_k=top_k + 1,  # 자기 자신 제외를 위해 +1
                collection_name=collection
            )
            
            # 자기 자신 제외
            return [r for r in results if r.get("id") != document_id][:top_k]
            
        except Exception as e:
            logger.error(f"유사 문서 검색 실패: {e}")
            return []
    
    def clear_cache(self):
        """캐시 초기화"""
        if self.cache is not None:
            self.cache.clear()
            logger.info("검색 캐시 초기화 완료")

