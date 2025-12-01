"""검색 기능 테스트 스크립트"""
import asyncio
import logging
from src.infrastructure.database.qdrant_manager import QdrantManager
from src.services.embeddings.manager import EmbeddingManager
from src.services.search.search_service import SearchService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_search():
    """검색 테스트"""
    try:
        # 매니저 초기화
        logger.info("=== 검색 테스트 시작 ===\n")
        
        qdrant_manager = QdrantManager()
        embedding_manager = EmbeddingManager()
        search_service = SearchService(qdrant_manager, embedding_manager)
        
        # 테스트 쿼리
        test_queries = [
            "식대+자가용운전지원금 40만원을 지급받는 중인데 이게 최저시급에 포함되나?",
            "최저시급",
            "근로기준법"
        ]
        
        for query in test_queries:
            logger.info(f"\n{'='*60}")
            logger.info(f"🔍 쿼리: '{query}'")
            logger.info(f"{'='*60}")
            
            # labor_consultant_docs 검색
            logger.info("\n📚 컬렉션: labor_consultant_docs")
            results1 = search_service.search(
                query=query,
                top_k=3,
                collection_name="labor_consultant_docs",
                score_threshold=0.3
            )
            
            logger.info(f"결과 수: {len(results1)}")
            for i, result in enumerate(results1, 1):
                logger.info(f"\n[결과 {i}]")
                logger.info(f"  - 점수: {result['score']:.4f}")
                logger.info(f"  - 제목: {result.get('title', 'N/A')}")
                logger.info(f"  - 내용 미리보기: {result['content'][:100]}...")
            
            # labor_standards_act_commentary 검색
            logger.info("\n📚 컬렉션: labor_standards_act_commentary")
            results2 = search_service.search(
                query=query,
                top_k=3,
                collection_name="labor_standards_act_commentary",
                score_threshold=0.3
            )
            
            logger.info(f"결과 수: {len(results2)}")
            for i, result in enumerate(results2, 1):
                logger.info(f"\n[결과 {i}]")
                logger.info(f"  - 점수: {result['score']:.4f}")
                logger.info(f"  - 제목: {result.get('title', 'N/A')}")
                logger.info(f"  - 내용 미리보기: {result['content'][:100]}...")
        
        logger.info("\n\n=== 검색 테스트 완료 ===")
        
        qdrant_manager.close()
        
    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_search())

