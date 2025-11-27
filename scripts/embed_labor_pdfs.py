"""
공인노무사 PDF 자료 임베딩 스크립트
- OCR된 PDF와 OCR 안된 PDF 모두 처리
- Voyage AI로 임베딩 생성
- Qdrant에 저장
"""

import os
import sys
import uuid
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from tqdm import tqdm

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# PDF 처리 라이브러리
try:
    import pymupdf  # PyMuPDF (fitz)
except ImportError:
    import fitz as pymupdf

try:
    import pytesseract
    from PIL import Image
    import io
    # Windows Tesseract 경로 설정
    TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(TESSERACT_PATH):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("⚠️ pytesseract 또는 Pillow가 설치되지 않음 - OCR 기능 비활성화")

# 텍스트 분할
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 프로젝트 모듈
from src.services.embeddings.manager import EmbeddingManager
from src.infrastructure.database.qdrant_manager import QdrantManager
from src.config import app_config as config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "logs" / "pdf_embedding.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class PDFEmbedder:
    """PDF 문서 임베딩 처리기"""

    def __init__(
        self,
        collection_name: str = "labor_consultant_docs",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        초기화

        Args:
            collection_name: Qdrant 컬렉션 이름
            chunk_size: 청크 크기 (문자 수)
            chunk_overlap: 청크 오버랩 (문자 수)
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

        # 컬렉션 생성 (없으면)
        self._ensure_collection()

        logger.info(f"✅ PDFEmbedder 초기화 완료")
        logger.info(f"   컬렉션: {self.collection_name}")
        logger.info(f"   청크 크기: {chunk_size}")
        logger.info(f"   오버랩: {chunk_overlap}")

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

    def extract_text_from_pdf(self, pdf_path: Path, show_progress: bool = True) -> tuple[str, dict]:
        """
        PDF에서 텍스트 추출 (OCR 포함)

        Returns:
            tuple: (추출된 텍스트, 메타데이터)
        """
        pdf_path = Path(pdf_path)
        text_parts = []
        metadata = {
            "file_name": pdf_path.name,
            "file_path": str(pdf_path),
            "page_count": 0,
            "ocr_used": False,
            "extraction_method": "text",
            "ocr_pages": 0
        }

        try:
            doc = pymupdf.open(str(pdf_path))
            metadata["page_count"] = len(doc)
            total_pages = len(doc)

            # 페이지별 진행률 표시
            page_iterator = tqdm(
                enumerate(doc),
                total=total_pages,
                desc=f"  페이지 추출",
                leave=False,
                disable=not show_progress
            )

            for page_num, page in page_iterator:
                # 먼저 텍스트 직접 추출 시도
                text = page.get_text("text")

                # 텍스트가 거의 없으면 OCR 시도
                if len(text.strip()) < 50 and OCR_AVAILABLE:
                    page_iterator.set_postfix({"OCR": f"p.{page_num + 1}"})
                    ocr_text = self._ocr_page(page)
                    if ocr_text:
                        text = ocr_text
                        metadata["ocr_used"] = True
                        metadata["extraction_method"] = "ocr"
                        metadata["ocr_pages"] += 1

                if text.strip():
                    text_parts.append(f"[페이지 {page_num + 1}]\n{text}")

            doc.close()

        except Exception as e:
            logger.error(f"PDF 읽기 실패 ({pdf_path.name}): {e}")
            raise

        full_text = "\n\n".join(text_parts)
        return full_text, metadata

    def _ocr_page(self, page) -> Optional[str]:
        """페이지 OCR 처리"""
        if not OCR_AVAILABLE:
            return None

        try:
            # 페이지를 이미지로 변환 (해상도 300 DPI)
            mat = pymupdf.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat)

            # PIL Image로 변환
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))

            # OCR 수행 (한국어 + 영어)
            text = pytesseract.image_to_string(
                image,
                lang='kor+eng',
                config='--psm 1'  # 자동 페이지 분할
            )

            return text.strip()

        except Exception as e:
            logger.warning(f"OCR 실패: {e}")
            return None

    def generate_doc_id(self, file_path: str, chunk_index: int) -> str:
        """문서 청크의 고유 ID 생성"""
        content = f"{file_path}:{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()

    def process_pdf(self, pdf_path: Path) -> int:
        """
        단일 PDF 처리 및 임베딩

        Returns:
            int: 저장된 청크 수
        """
        pdf_path = Path(pdf_path)
        logger.info(f"📄 처리 중: {pdf_path.name}")

        # 텍스트 추출
        text, metadata = self.extract_text_from_pdf(pdf_path)

        if not text.strip():
            logger.warning(f"⚠️ 텍스트 없음: {pdf_path.name}")
            return 0

        logger.info(f"   추출된 텍스트: {len(text):,}자 ({metadata['page_count']}페이지)")
        if metadata["ocr_used"]:
            logger.info(f"   OCR 사용됨: {metadata.get('ocr_pages', 0)}페이지")

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
            point_id = self.generate_doc_id(str(pdf_path), i)

            payload = {
                "text": chunk,
                "source": pdf_path.name,
                "file_path": str(pdf_path),
                "chunk_index": i,
                "total_chunks": len(chunks),
                "page_count": metadata["page_count"],
                "ocr_used": metadata["ocr_used"],
                "category": "공인노무사",
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
        디렉토리의 모든 PDF 처리

        Returns:
            dict: 처리 결과 통계
        """
        dir_path = Path(dir_path)

        if not dir_path.exists():
            raise FileNotFoundError(f"디렉토리가 존재하지 않습니다: {dir_path}")

        # PDF 파일 찾기
        pdf_files = list(dir_path.glob("**/*.pdf"))
        logger.info(f"🔍 발견된 PDF 파일: {len(pdf_files)}개")

        if not pdf_files:
            logger.warning("PDF 파일이 없습니다")
            return {"total": 0, "success": 0, "failed": 0, "chunks": 0}

        stats = {
            "total": len(pdf_files),
            "success": 0,
            "failed": 0,
            "chunks": 0,
            "failed_files": []
        }

        # 진행 표시와 함께 처리
        for pdf_path in tqdm(pdf_files, desc="PDF 처리"):
            try:
                chunks = self.process_pdf(pdf_path)
                if chunks > 0:
                    stats["success"] += 1
                    stats["chunks"] += chunks
                else:
                    stats["failed"] += 1
                    stats["failed_files"].append(str(pdf_path))
            except Exception as e:
                logger.error(f"❌ 처리 실패 ({pdf_path.name}): {e}")
                stats["failed"] += 1
                stats["failed_files"].append(str(pdf_path))

        return stats


def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="공인노무사 PDF 자료 임베딩")
    parser.add_argument(
        "--path",
        type=str,
        default=r"C:\Users\alvin\OneDrive\바탕 화면\공인노무사 자료",
        help="PDF 파일 경로 또는 디렉토리"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="labor_consultant_docs",
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

    args = parser.parse_args()

    # 로그 디렉토리 생성
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("🚀 공인노무사 PDF 임베딩 시작")
    print("=" * 60)
    print(f"📂 경로: {args.path}")
    print(f"📦 컬렉션: {args.collection}")
    print(f"📏 청크 크기: {args.chunk_size}")
    print(f"🔗 오버랩: {args.chunk_overlap}")
    print(f"🧠 OCR 가능: {OCR_AVAILABLE}")
    print("=" * 60)

    try:
        # PDFEmbedder 초기화
        embedder = PDFEmbedder(
            collection_name=args.collection,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap
        )

        path = Path(args.path)

        if path.is_file():
            # 단일 파일 처리
            chunks = embedder.process_pdf(path)
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
                for f in stats['failed_files'][:10]:  # 최대 10개만 표시
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
