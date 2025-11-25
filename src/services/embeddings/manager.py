"""Embedding Manager - 임베딩 생성 및 관리"""

import logging
import time
import random
from typing import Any, Optional

from src.config import app_config as config

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """임베딩 생성 및 관리"""
    
    def __init__(self):
        """임베딩 매니저 초기화"""
        self.model = None
        self.embedding_type = None
        self.dimension = config.VECTOR_SIZE
        
        # VoyageAI 우선 사용
        if config.USE_VOYAGE_EMBEDDING and config.VOYAGE_API_KEY:
            self._init_voyage()
        elif config.OPENAI_API_KEY:
            self._init_openai()
        else:
            raise ValueError("VOYAGE_API_KEY 또는 OPENAI_API_KEY가 필요합니다")
        
        logger.info(f"📊 임베딩 매니저 초기화 완료")
        logger.info(f"    모델: {self.model}")
        logger.info(f"    타입: {self.embedding_type}")
        logger.info(f"    차원: {self.dimension}")
    
    def _init_voyage(self):
        """VoyageAI 임베딩 초기화"""
        try:
            import voyageai
            self.voyage_client = voyageai.Client(api_key=config.VOYAGE_API_KEY)
            self.model = config.VOYAGE_MODEL_NAME
            self.embedding_type = "voyage"
            self.dimension = 1024  # voyage-3-large
            logger.info("✅ VoyageAI 임베딩 초기화 완료")
        except Exception as e:
            logger.error(f"❌ VoyageAI 초기화 실패: {e}")
            # OpenAI로 폴백
            if config.OPENAI_API_KEY:
                self._init_openai()
            else:
                raise
    
    def _init_openai(self):
        """OpenAI 임베딩 초기화"""
        try:
            from openai import OpenAI
            self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
            self.model = "text-embedding-3-small"
            self.embedding_type = "openai"
            self.dimension = 1536  # text-embedding-3-small
            logger.info("✅ OpenAI 임베딩 초기화 완료")
        except Exception as e:
            logger.error(f"❌ OpenAI 초기화 실패: {e}")
            raise
    
    def create_embedding(self, text: str, input_type: str = "document") -> list[float]:
        """단일 텍스트 임베딩 생성"""
        if self.embedding_type == "voyage":
            return self._create_voyage_embedding(text, input_type)
        else:
            return self._create_openai_embedding(text)
    
    def _create_voyage_embedding(self, text: str, input_type: str = "document") -> list[float]:
        """VoyageAI 임베딩 생성"""
        try:
            result = self.voyage_client.embed(
                texts=[text],
                model=self.model,
                input_type=input_type
            )
            return result.embeddings[0]
        except Exception as e:
            logger.error(f"VoyageAI 임베딩 실패: {e}")
            raise
    
    def _create_openai_embedding(self, text: str) -> list[float]:
        """OpenAI 임베딩 생성"""
        try:
            response = self.openai_client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI 임베딩 실패: {e}")
            raise
    
    def create_embedding_with_retry(
        self,
        text: str,
        max_retries: int = 3,
        input_type: str = "document"
    ) -> list[float]:
        """재시도 로직이 포함된 임베딩 생성"""
        for attempt in range(max_retries):
            try:
                return self.create_embedding(text, input_type)
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                    logger.warning(f"⏳ 임베딩 재시도 {attempt + 1}/{max_retries} - {wait_time:.1f}초 대기")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ 임베딩 최대 재시도 초과: {e}")
                    raise
        
        raise Exception("최대 재시도 횟수 초과")
    
    def create_query_embedding(self, query: str) -> list[float]:
        """쿼리용 임베딩 생성 (검색 최적화)"""
        if self.embedding_type == "voyage":
            return self._create_voyage_embedding(query, input_type="query")
        else:
            return self._create_openai_embedding(query)
    
    def create_embeddings_batch(
        self,
        texts: list[str],
        input_type: str = "document",
        batch_size: int = 128
    ) -> list[list[float]]:
        """배치 임베딩 생성"""
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                if self.embedding_type == "voyage":
                    result = self.voyage_client.embed(
                        texts=batch,
                        model=self.model,
                        input_type=input_type
                    )
                    all_embeddings.extend(result.embeddings)
                else:
                    response = self.openai_client.embeddings.create(
                        model=self.model,
                        input=batch
                    )
                    all_embeddings.extend([d.embedding for d in response.data])
                
                logger.info(f"배치 임베딩 진행: {min(i + batch_size, len(texts))}/{len(texts)}")
            except Exception as e:
                logger.error(f"배치 임베딩 실패: {e}")
                # 개별 처리로 폴백
                for text in batch:
                    try:
                        embedding = self.create_embedding_with_retry(text, input_type=input_type)
                        all_embeddings.append(embedding)
                    except Exception as inner_e:
                        logger.error(f"개별 임베딩 실패: {inner_e}")
                        # 빈 벡터로 대체
                        all_embeddings.append([0.0] * self.dimension)
        
        return all_embeddings
    
    def embed_query(self, query: str) -> list[float]:
        """쿼리 임베딩 (create_query_embedding의 별칭)"""
        return self.create_query_embedding(query)
    
    def embed_documents(self, documents: list[str]) -> list[list[float]]:
        """문서 목록 임베딩"""
        return self.create_embeddings_batch(documents, input_type="document")

