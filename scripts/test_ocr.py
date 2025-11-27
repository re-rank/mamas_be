"""OCR 테스트 스크립트 - PDF 첫 페이지만 테스트"""

import os
import sys
from pathlib import Path

# 윈도우 콘솔 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

# Tesseract 경로 설정
os.environ['TESSDATA_PREFIX'] = r'C:\Program Files\Tesseract-OCR\tessdata'

try:
    import pymupdf
except ImportError:
    import fitz as pymupdf

import pytesseract
from PIL import Image
import io

# Tesseract 실행 파일 경로
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def test_pdf_ocr(pdf_path: str, page_num: int = 0):
    """PDF의 특정 페이지 OCR 테스트"""

    print(f"📄 파일: {Path(pdf_path).name}")
    print(f"📃 테스트 페이지: {page_num + 1}")
    print("-" * 50)

    # PDF 열기
    doc = pymupdf.open(pdf_path)
    print(f"   총 페이지 수: {len(doc)}")

    page = doc[page_num]

    # 1. 텍스트 직접 추출 시도
    direct_text = page.get_text("text")
    print(f"\n📝 직접 추출된 텍스트 ({len(direct_text)}자):")
    print("-" * 30)
    if direct_text.strip():
        print(direct_text[:500] + "..." if len(direct_text) > 500 else direct_text)
    else:
        print("(텍스트 없음)")

    # 2. OCR 시도
    print(f"\n🔍 OCR 추출 시도...")

    # 페이지를 이미지로 변환 (300 DPI)
    mat = pymupdf.Matrix(300/72, 300/72)
    pix = page.get_pixmap(matrix=mat)

    # PIL Image로 변환
    img_data = pix.tobytes("png")
    image = Image.open(io.BytesIO(img_data))
    print(f"   이미지 크기: {image.size}")

    # OCR 수행
    ocr_text = pytesseract.image_to_string(
        image,
        lang='kor+eng',
        config='--psm 1'
    )

    print(f"\n🧠 OCR 추출된 텍스트 ({len(ocr_text)}자):")
    print("-" * 30)
    if ocr_text.strip():
        print(ocr_text[:500] + "..." if len(ocr_text) > 500 else ocr_text)
    else:
        print("(OCR 텍스트 없음)")

    doc.close()

    # 결과 비교
    print("\n" + "=" * 50)
    print("📊 결과 요약:")
    print(f"   직접 추출: {len(direct_text.strip())}자")
    print(f"   OCR 추출: {len(ocr_text.strip())}자")

    if len(direct_text.strip()) > 50:
        print("   ➡️ 텍스트 PDF (OCR 불필요)")
    elif len(ocr_text.strip()) > 50:
        print("   ➡️ 이미지 PDF (OCR 성공!)")
    else:
        print("   ⚠️ 텍스트 추출 실패")


if __name__ == "__main__":
    # 테스트할 PDF 경로
    pdf_dir = r"C:\Users\alvin\OneDrive\바탕 화면\공인노무사 자료"

    # 첫 번째 PDF 파일 찾기
    pdf_files = list(Path(pdf_dir).glob("*.pdf"))

    if not pdf_files:
        print("PDF 파일이 없습니다")
        sys.exit(1)

    print("=" * 50)
    print("🧪 OCR 테스트")
    print("=" * 50)
    print(f"발견된 PDF 파일: {len(pdf_files)}개")
    for i, f in enumerate(pdf_files):
        print(f"  {i+1}. {f.name}")
    print()

    # 테스트할 파일과 페이지 선택
    test_file = pdf_files[0]  # 근로기준법주해(1).pdf
    test_page = 10  # 본문 페이지

    print(f"테스트 대상: {test_file.name}")
    print(f"파일 크기: {test_file.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"테스트 페이지: {test_page + 1}")
    print()

    test_pdf_ocr(str(test_file), page_num=test_page)
