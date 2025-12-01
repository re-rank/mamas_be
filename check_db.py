"""Qdrant DB 상태 확인 스크립트"""
import asyncio
import logging
from src.infrastructure.database.qdrant_manager import QdrantManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_database():
    """데이터베이스 상태 확인"""
    try:
        manager = QdrantManager()
        
        # 모든 컬렉션 조회
        collections = manager.list_collections()
        logger.info(f"\n📊 전체 컬렉션 목록 ({len(collections)}개):")
        for col in collections:
            logger.info(f"  - {col}")
        
        # 각 컬렉션 정보 출력
        logger.info("\n📈 컬렉션 상세 정보:")
        for col_name in collections:
            info = manager.get_collection_info(col_name)
            if info:
                logger.info(f"\n컬렉션: {col_name}")
                logger.info(f"  - 포인트 수: {info['points_count']}")
                logger.info(f"  - 벡터 수: {info['vectors_count']}")
                logger.info(f"  - 상태: {info['status']}")
        
        # 기본 컬렉션 확인
        from src.config import app_config as config
        logger.info(f"\n⚙️ 설정된 기본 컬렉션: {config.COLLECTION_NAME}")
        
        if config.COLLECTION_NAME in collections:
            logger.info(f"✅ 기본 컬렉션이 존재합니다")
        else:
            logger.warning(f"⚠️ 기본 컬렉션이 존재하지 않습니다!")
            logger.info(f"💡 다음 중 하나를 선택하세요:")
            logger.info(f"   1. .env에서 COLLECTION_NAME을 다음 중 하나로 변경:")
            for col in collections:
                logger.info(f"      - {col}")
            logger.info(f"   2. 새로운 '{config.COLLECTION_NAME}' 컬렉션에 데이터 업로드")
        
        manager.close()
        
    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_database())

