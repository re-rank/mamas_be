"""
간단한 문서 업로드 예제
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def upload_sample_documents():
    """샘플 문서들을 업로드합니다"""
    
    documents = [
        {
            "content": """
            파이썬(Python)은 1991년 귀도 반 로섬이 발표한 고급 프로그래밍 언어입니다.
            문법이 간결하고 표현 구조가 인간의 사고 체계와 유사하여 배우기 쉽습니다.
            
            파이썬의 주요 특징:
            - 인터프리터 언어: 소스코드를 바로 실행
            - 동적 타이핑: 변수 타입을 명시하지 않아도 됨
            - 풍부한 라이브러리: 다양한 분야의 라이브러리 제공
            - 크로스 플랫폼: Windows, Linux, macOS 등에서 실행 가능
            
            파이썬은 웹 개발, 데이터 분석, 인공지능, 자동화 등 다양한 분야에서 사용됩니다.
            """,
            "title": "파이썬 소개",
            "metadata": {"category": "프로그래밍", "language": "파이썬"}
        },
        {
            "content": """
            FastAPI는 현대적이고 빠른 웹 프레임워크입니다.
            Python 3.7+ 타입 힌트를 기반으로 API를 빌드하기 위한 프레임워크입니다.
            
            FastAPI의 장점:
            - 빠른 성능: NodeJS, Go와 대등한 성능
            - 빠른 개발: 개발 속도 약 200% 증가
            - 적은 버그: 개발자 실수 약 40% 감소
            - 직관적: 자동 완성 지원으로 생산성 향상
            - 쉬운 사용: 배우고 사용하기 쉬움
            - 짧은 코드: 코드 중복 최소화
            - 표준 기반: OpenAPI, JSON Schema 표준 지원
            
            자동 대화형 API 문서를 제공하여 개발이 매우 편리합니다.
            """,
            "title": "FastAPI 소개",
            "metadata": {"category": "프로그래밍", "framework": "FastAPI"}
        },
        {
            "content": """
            벡터 데이터베이스는 고차원 벡터 데이터를 효율적으로 저장하고 검색하는 데이터베이스입니다.
            
            주요 용도:
            - 의미론적 검색: 텍스트의 의미를 이해하여 관련 문서 검색
            - 추천 시스템: 유사한 항목 추천
            - 이미지 검색: 유사한 이미지 찾기
            - 이상 탐지: 비정상적인 패턴 감지
            
            대표적인 벡터 데이터베이스:
            - Qdrant: Rust로 작성된 고성능 벡터 검색 엔진
            - Pinecone: 완전 관리형 벡터 데이터베이스
            - Weaviate: 오픈소스 벡터 검색 엔진
            - Milvus: 대규모 벡터 데이터를 위한 오픈소스 DB
            
            벡터 데이터베이스는 RAG 시스템의 핵심 구성 요소입니다.
            """,
            "title": "벡터 데이터베이스란?",
            "metadata": {"category": "데이터베이스", "type": "벡터DB"}
        }
    ]
    
    print("📚 샘플 문서 업로드 시작...\n")
    
    for i, doc in enumerate(documents, 1):
        print(f"[{i}/{len(documents)}] '{doc['title']}' 업로드 중...")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/documents/upload",
                json=doc
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                print(f"  ✅ 성공: {result['chunks_count']}개 청크 생성\n")
            else:
                print(f"  ❌ 실패: {result.get('error')}\n")
                
        except Exception as e:
            print(f"  ❌ 에러: {e}\n")
    
    print("=" * 60)
    print("업로드 완료! 이제 다음을 시도해보세요:")
    print("1. 검색: POST /api/search")
    print("2. 채팅: POST /api/chat")
    print("\n예제:")
    print('  curl -X POST "http://localhost:8000/api/search" \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"query": "파이썬이란?", "top_k": 3}\'')
    print("=" * 60)


if __name__ == "__main__":
    upload_sample_documents()

