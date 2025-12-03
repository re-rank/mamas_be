@echo off
REM .env 파일 설정 스크립트 (Windows)

set ENV_FILE=.env

echo === .env 파일 설정 ===
echo.

REM .env 파일이 없으면 생성
if not exist "%ENV_FILE%" (
    echo .env 파일이 없습니다. env.example에서 복사합니다...
    copy env.example .env
)

REM PowerShell을 사용하여 파일 내용 업데이트
powershell -Command "$content = Get-Content .env; if ($content -match '^COLLECTION_NAME=') { $content = $content -replace '^COLLECTION_NAME=.*', 'COLLECTION_NAME=labor_consultant_docs'; Write-Host '✅ COLLECTION_NAME 업데이트: labor_consultant_docs' } else { $content += 'COLLECTION_NAME=labor_consultant_docs'; Write-Host '✅ COLLECTION_NAME 추가: labor_consultant_docs' }; $content | Set-Content .env"

powershell -Command "$content = Get-Content .env; if ($content -match '^SEARCH_SCORE_THRESHOLD=') { $content = $content -replace '^SEARCH_SCORE_THRESHOLD=.*', 'SEARCH_SCORE_THRESHOLD=0.3'; Write-Host '✅ SEARCH_SCORE_THRESHOLD 업데이트: 0.3' } else { $content += 'SEARCH_SCORE_THRESHOLD=0.3'; Write-Host '✅ SEARCH_SCORE_THRESHOLD 추가: 0.3' }; $content | Set-Content .env"

echo.
echo === 설정 완료 ===
echo 서버를 재시작하세요: start.bat
pause

