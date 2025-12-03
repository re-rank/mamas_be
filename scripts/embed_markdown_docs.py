"""
마크다운 문서 임베딩 스크립트
- .md 파일 읽기
- Voyage AI로 임베딩 생성
- Qdrant에 저장
"""

import os
import sys
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# 텍스트 분할
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 프로젝트 모듈
from src.services.embeddings.manager import EmbeddingManager
from src.infrastructure.database.qdrant_manager import QdrantManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "logs" / "md_embedding.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class MarkdownEmbedder:
    """마크다운 문서 임베딩 처리기"""

    def __init__(
        self,
        collection_name: str = "labor_standards_act_commentary",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        reset_collection: bool = False
    ):
        """
        초기화

        Args:
            collection_name: Qdrant 컬렉션 이름
            chunk_size: 청크 크기 (문자 수)
            chunk_overlap: 청크 오버랩 (문자 수)
            reset_collection: True면 컬렉션 초기화 (삭제 후 재생성)
        """
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # 텍스트 분할기
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )

        # 임베딩 매니저
        logger.info("임베딩 매니저 초기화 중...")
        self.embedding_manager = EmbeddingManager()

        # Qdrant 매니저
        logger.info("Qdrant 매니저 초기화 중...")
        self.qdrant_manager = QdrantManager()

        # 컬렉션 초기화 (선택적)
        if reset_collection:
            self._reset_collection()
        else:
            self._ensure_collection()

        logger.info(f"✅ MarkdownEmbedder 초기화 완료")
        logger.info(f"   컬렉션: {self.collection_name}")
        logger.info(f"   청크 크기: {chunk_size}")
        logger.info(f"   오버랩: {chunk_overlap}")

    def _reset_collection(self):
        """컬렉션 초기화 (삭제 후 재생성)"""
        if self.qdrant_manager.collection_exists(self.collection_name):
            logger.info(f"🗑️ 컬렉션 '{self.collection_name}' 삭제 중...")
            self.qdrant_manager.delete_collection(self.collection_name)
            logger.info(f"✅ 컬렉션 '{self.collection_name}' 삭제 완료")

        # 새로 생성
        self.qdrant_manager.create_collection(
            collection_name=self.collection_name,
            vector_size=self.embedding_manager.dimension
        )
        logger.info(f"✅ 컬렉션 '{self.collection_name}' 생성 완료")

    def _ensure_collection(self):
        """컬렉션 존재 확인 및 생성"""
        if not self.qdrant_manager.collection_exists(self.collection_name):
            self.qdrant_manager.create_collection(
                collection_name=self.collection_name,
                vector_size=self.embedding_manager.dimension
            )
            logger.info(f"✅ 컬렉션 '{self.collection_name}' 생성됨")
        else:
            logger.info(f"ℹ️ 컬렉션 '{self.collection_name}' 이미 존재")

    def read_markdown(self, md_path: Path) -> tuple[str, dict]:
        """
        마크다운 파일 읽기

        Returns:
            tuple: (텍스트 내용, 메타데이터)
        """
        md_path = Path(md_path)
        metadata = {
            "file_name": md_path.name,
            "file_path": str(md_path),
        }

        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                text = f.read()

            metadata["char_count"] = len(text)
            metadata["line_count"] = text.count('\n') + 1

            return text, metadata

        except Exception as e:
            logger.error(f"마크다운 읽기 실패 ({md_path.name}): {e}")
            raise

    def generate_doc_id(self, file_path: str, chunk_index: int) -> str:
        """문서 청크의 고유 ID 생성"""
        content = f"{file_path}:{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()

    def process_markdown(self, md_path: Path) -> int:
        """
        단일 마크다운 파일 처리 및 임베딩

        Returns:
            int: 저장된 청크 수
        """
        md_path = Path(md_path)
        logger.info(f"📄 처리 중: {md_path.name}")

        # 텍스트 읽기
        text, metadata = self.read_markdown(md_path)

        if not text.strip():
            logger.warning(f"⚠️ 텍스트 없음: {md_path.name}")
            return 0

        logger.info(f"   텍스트 크기: {len(text):,}자 ({metadata['line_count']}줄)")

        # 텍스트 분할
        chunks = self.text_splitter.split_text(text)
        logger.info(f"   생성된 청크: {len(chunks)}개")

        if not chunks:
            return 0

        # 임베딩 생성 (배치)
        logger.info(f"   임베딩 생성 중...")
        embeddings = self.embedding_manager.create_embeddings_batch(
            texts=chunks,
            input_type="document"
        )

        # 포인트 생성
        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = self.generate_doc_id(str(md_path), i)

            payload = {
                "text": chunk,
                "source": md_path.name,
                "file_path": str(md_path),
                "chunk_index": i,
                "total_chunks": len(chunks),
                "char_count": metadata["char_count"],
                "category": "근로기준법주해",
                "document_type": "legal_commentary",
                "created_at": datetime.now().isoformat()
            }

            points.append({
                "id": point_id,
                "vector": embedding,
                "payload": payload
            })

        # Qdrant에 업로드
        success = self.qdrant_manager.upsert_points(
            points=points,
            collection_name=self.collection_name
        )

        if success:
            logger.info(f"   ✅ {len(points)}개 청크 저장 완료")
            return len(points)
        else:
            logger.error(f"   ❌ 저장 실패")
            return 0

    def process_directory(self, dir_path: str) -> dict:
        """
        디렉토리의 모든 마크다운 파일 처리

        Returns:
            dict: 처리 결과 통계
        """
        dir_path = Path(dir_path)

        if not dir_path.exists():
            raise FileNotFoundError(f"디렉토리가 존재하지 않습니다: {dir_path}")

        # 마크다운 파일 찾기
        md_files = sorted(list(dir_path.glob("**/*.md")))
        logger.info(f"🔍 발견된 마크다운 파일: {len(md_files)}개")

        if not md_files:
            logger.warning("마크다운 파일이 없습니다")
            return {"total": 0, "success": 0, "failed": 0, "chunks": 0}

        stats = {
            "total": len(md_files),
            "success": 0,
            "failed": 0,
            "chunks": 0,
            "failed_files": []
        }

        # 진행 표시와 함께 처리
        for md_path in tqdm(md_files, desc="마크다운 처리"):
            try:
                chunks = self.process_markdown(md_path)
                if chunks > 0:
                    stats["success"] += 1
                    stats["chunks"] += chunks
                else:
                    stats["failed"] += 1
                    stats["failed_files"].append(str(md_path))
            except Exception as e:
                logger.error(f"❌ 처리 실패 ({md_path.name}): {e}")
                stats["failed"] += 1
                stats["failed_files"].append(str(md_path))

        return stats


def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="마크다운 문서 임베딩")
    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="마크다운 파일 경로 또는 디렉토리"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="labor_standards_act_commentary",
        help="Qdrant 컬렉션 이름"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="청크 크기 (문자 수)"
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=200,
        help="청크 오버랩 (문자 수)"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="컬렉션 초기화 (삭제 후 재생성)"
    )

    args = parser.parse_args()

    # 로그 디렉토리 생성
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("🚀 마크다운 문서 임베딩 시작")
    print("=" * 60)
    print(f"📂 경로: {args.path}")
    print(f"📦 컬렉션: {args.collection}")
    print(f"📏 청크 크기: {args.chunk_size}")
    print(f"🔗 오버랩: {args.chunk_overlap}")
    print(f"🗑️ 컬렉션 초기화: {args.reset}")
    print("=" * 60)

    try:
        # MarkdownEmbedder 초기화
        embedder = MarkdownEmbedder(
            collection_name=args.collection,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            reset_collection=args.reset
        )

        path = Path(args.path)

        if path.is_file():
            # 단일 파일 처리
            chunks = embedder.process_markdown(path)
            print(f"\n✅ 완료: {chunks}개 청크 저장")
        else:
            # 디렉토리 처리
            stats = embedder.process_directory(path)

            print("\n" + "=" * 60)
            print("📊 처리 결과")
            print("=" * 60)
            print(f"   전체 파일: {stats['total']}개")
            print(f"   성공: {stats['success']}개")
            print(f"   실패: {stats['failed']}개")
            print(f"   총 청크: {stats['chunks']}개")

            if stats['failed_files']:
                print("\n❌ 실패한 파일:")
                for f in stats['failed_files'][:10]:
                    print(f"   - {f}")
                if len(stats['failed_files']) > 10:
                    print(f"   ... 외 {len(stats['failed_files']) - 10}개")

        # 컬렉션 정보 출력
        info = embedder.qdrant_manager.get_collection_info(args.collection)
        if info:
            print(f"\n📦 컬렉션 '{args.collection}' 현재 상태:")
            print(f"   총 포인트: {info['points_count']:,}개")
            print(f"   상태: {info['status']}")

    except Exception as e:
        logger.error(f"실행 오류: {e}")
        raise


if __name__ == "__main__":
    main()
