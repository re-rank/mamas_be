"""Qdrant Manager - 벡터 데이터베이스 매니저"""

import logging
import time
from typing import Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from src.config import app_config as config

logger = logging.getLogger(__name__)


class QdrantManager:
    """Qdrant 벡터 데이터베이스 매니저"""
    
    def __init__(self):
        """Qdrant 매니저 초기화"""
        self.client = QdrantClient(
            url=config.QDRANT_URL,
            api_key=config.QDRANT_API_KEY,
            timeout=30,
            prefer_grpc=False,
            https=True
        )
        
        self.collection_name = config.COLLECTION_NAME
        self.vector_size = config.VECTOR_SIZE
        
        # 컬렉션 정보 캐시
        self._collection_cache: dict[str, dict] = {}
        self._cache_ttl = 300  # 5분
        self._cache_timestamp: dict[str, float] = {}
        
        logger.info("🗄️ Qdrant 매니저 초기화 완료")
        logger.info(f"    호스트: {config.QDRANT_URL}")
        logger.info(f"    컬렉션: {self.collection_name}")
        logger.info(f"    벡터 차원: {self.vector_size}")
        
        # 연결 테스트
        self._test_connection()
    
    def _test_connection(self) -> bool:
        """Qdrant 연결 테스트"""
        try:
            collections = self.client.get_collections()
            logger.info(f"    ✅ Qdrant 연결 성공 - {len(collections.collections)}개 컬렉션 발견")
            return True
        except Exception as e:
            logger.error(f"    ❌ Qdrant 연결 실패: {e}")
            return False
    
    def collection_exists(self, collection_name: Optional[str] = None) -> bool:
        """컬렉션 존재 여부 확인"""
        name = collection_name or self.collection_name
        try:
            self.client.get_collection(name)
            return True
        except Exception:
            return False
    
    def create_collection(
        self,
        collection_name: Optional[str] = None,
        vector_size: Optional[int] = None,
        distance: Distance = Distance.COSINE
    ) -> bool:
        """컬렉션 생성"""
        name = collection_name or self.collection_name
        size = vector_size or self.vector_size
        
        try:
            if self.collection_exists(name):
                logger.info(f"컬렉션 '{name}'이 이미 존재합니다")
                return True
            
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=size,
                    distance=distance
                )
            )
            logger.info(f"✅ 컬렉션 '{name}' 생성 완료 (차원: {size})")
            return True
        except Exception as e:
            logger.error(f"❌ 컬렉션 생성 실패: {e}")
            return False
    
    def get_collection_info(self, collection_name: Optional[str] = None) -> Optional[dict]:
        """컬렉션 정보 조회"""
        name = collection_name or self.collection_name
        
        # 캐시 확인
        now = time.time()
        if name in self._collection_cache:
            if now - self._cache_timestamp.get(name, 0) < self._cache_ttl:
                return self._collection_cache[name]
        
        try:
            info = self.client.get_collection(name)
            result = {
                "name": name,
                "vectors_count": info.vectors_count if hasattr(info, 'vectors_count') else info.points_count,
                "points_count": info.points_count,
                "status": info.status.value if info.status else "unknown"
            }
            
            # 캐시 저장
            self._collection_cache[name] = result
            self._cache_timestamp[name] = now
            
            return result
        except Exception as e:
            logger.error(f"컬렉션 정보 조회 실패: {e}")
            return None
    
    def search(
        self,
        query_vector: list[float],
        collection_name: Optional[str] = None,
        limit: int = 5,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[models.Filter] = None
    ) -> list[dict]:
        """벡터 검색 수행"""
        name = collection_name or self.collection_name
        threshold = score_threshold or config.SEARCH_SCORE_THRESHOLD
        
        try:
            results = self.client.query_points(
                collection_name=name,
                query=query_vector,
                limit=limit,
                score_threshold=threshold,
                query_filter=filter_conditions
            ).points
            
            return [
                {
                    "id": str(hit.id),
                    "score": hit.score,
                    "payload": hit.payload or {}
                }
                for hit in results
            ]
        except Exception as e:
            logger.error(f"검색 실패: {e}")
            return []
    
    def search_with_payload_filter(
        self,
        query_vector: list[float],
        collection_name: Optional[str] = None,
        limit: int = 5,
        score_threshold: Optional[float] = None,
        must_conditions: Optional[list[dict]] = None,
        should_conditions: Optional[list[dict]] = None
    ) -> list[dict]:
        """페이로드 필터를 적용한 검색"""
        name = collection_name or self.collection_name
        
        # 필터 조건 구성
        filter_obj = None
        if must_conditions or should_conditions:
            must_list = []
            should_list = []
            
            if must_conditions:
                for cond in must_conditions:
                    if "key" in cond and "match" in cond:
                        must_list.append(
                            models.FieldCondition(
                                key=cond["key"],
                                match=models.MatchValue(value=cond["match"])
                            )
                        )
            
            if should_conditions:
                for cond in should_conditions:
                    if "key" in cond and "match" in cond:
                        should_list.append(
                            models.FieldCondition(
                                key=cond["key"],
                                match=models.MatchValue(value=cond["match"])
                            )
                        )
            
            filter_obj = models.Filter(
                must=must_list if must_list else None,
                should=should_list if should_list else None
            )
        
        return self.search(
            query_vector=query_vector,
            collection_name=name,
            limit=limit,
            score_threshold=score_threshold,
            filter_conditions=filter_obj
        )
    
    def upsert_points(
        self,
        points: list[dict],
        collection_name: Optional[str] = None,
        batch_size: int = 100
    ) -> bool:
        """포인트 업서트 (배치 처리)"""
        name = collection_name or self.collection_name
        
        try:
            # 컬렉션 존재 확인
            if not self.collection_exists(name):
                self.create_collection(name)
            
            # 배치 처리
            total = len(points)
            for i in range(0, total, batch_size):
                batch = points[i:i + batch_size]
                point_structs = [
                    PointStruct(
                        id=p["id"],
                        vector=p["vector"],
                        payload=p.get("payload", {})
                    )
                    for p in batch
                ]
                
                self.client.upsert(
                    collection_name=name,
                    points=point_structs
                )
                
                logger.info(f"배치 업로드 진행: {min(i + batch_size, total)}/{total}")
            
            logger.info(f"✅ {total}개 포인트 업서트 완료")
            return True
        except Exception as e:
            logger.error(f"❌ 포인트 업서트 실패: {e}")
            return False
    
    def delete_points(
        self,
        point_ids: list[str],
        collection_name: Optional[str] = None
    ) -> bool:
        """포인트 삭제"""
        name = collection_name or self.collection_name
        
        try:
            self.client.delete(
                collection_name=name,
                points_selector=models.PointIdsList(points=point_ids)
            )
            logger.info(f"✅ {len(point_ids)}개 포인트 삭제 완료")
            return True
        except Exception as e:
            logger.error(f"❌ 포인트 삭제 실패: {e}")
            return False
    
    def get_points_by_ids(
        self,
        point_ids: list[str],
        collection_name: Optional[str] = None
    ) -> list[dict]:
        """ID로 포인트 조회"""
        name = collection_name or self.collection_name
        
        try:
            results = self.client.retrieve(
                collection_name=name,
                ids=point_ids,
                with_payload=True,
                with_vectors=False
            )
            
            return [
                {
                    "id": str(point.id),
                    "payload": point.payload or {}
                }
                for point in results
            ]
        except Exception as e:
            logger.error(f"포인트 조회 실패: {e}")
            return []
    
    def list_collections(self) -> list[str]:
        """모든 컬렉션 목록 조회"""
        try:
            collections = self.client.get_collections()
            return [col.name for col in collections.collections]
        except Exception as e:
            logger.error(f"컬렉션 목록 조회 실패: {e}")
            return []
    
    def delete_collection(self, collection_name: Optional[str] = None) -> bool:
        """컬렉션 삭제"""
        name = collection_name or self.collection_name
        
        try:
            self.client.delete_collection(name)
            logger.info(f"✅ 컬렉션 '{name}' 삭제 완료")
            return True
        except Exception as e:
            logger.error(f"❌ 컬렉션 삭제 실패: {e}")
            return False
    
    def count_points(self, collection_name: Optional[str] = None) -> int:
        """컬렉션의 포인트 수 조회"""
        name = collection_name or self.collection_name
        
        try:
            info = self.client.get_collection(name)
            return info.points_count or 0
        except Exception:
            return 0
    
    def close(self):
        """연결 종료"""
        try:
            self.client.close()
            logger.info("Qdrant 연결 종료")
        except Exception:
            pass

