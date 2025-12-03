#!/bin/bash
# .env 파일 설정 스크립트

ENV_FILE=".env"

echo "=== .env 파일 설정 ==="
echo ""

# .env 파일이 없으면 생성
if [ ! -f "$ENV_FILE" ]; then
    echo ".env 파일이 없습니다. env.example에서 복사합니다..."
    cp env.example .env
fi

# COLLECTION_NAME 설정
if grep -q "^COLLECTION_NAME=" "$ENV_FILE"; then
    sed -i 's/^COLLECTION_NAME=.*/COLLECTION_NAME=labor_consultant_docs/' "$ENV_FILE"
    echo "✅ COLLECTION_NAME 업데이트: labor_consultant_docs"
else
    echo "COLLECTION_NAME=labor_consultant_docs" >> "$ENV_FILE"
    echo "✅ COLLECTION_NAME 추가: labor_consultant_docs"
fi

# SEARCH_SCORE_THRESHOLD 설정
if grep -q "^SEARCH_SCORE_THRESHOLD=" "$ENV_FILE"; then
    sed -i 's/^SEARCH_SCORE_THRESHOLD=.*/SEARCH_SCORE_THRESHOLD=0.3/' "$ENV_FILE"
    echo "✅ SEARCH_SCORE_THRESHOLD 업데이트: 0.3"
else
    echo "SEARCH_SCORE_THRESHOLD=0.3" >> "$ENV_FILE"
    echo "✅ SEARCH_SCORE_THRESHOLD 추가: 0.3"
fi

echo ""
echo "=== 설정 완료 ==="
echo "서버를 재시작하세요:"
echo "  Windows: start.bat"
echo "  Linux/Mac: ./start.sh"

