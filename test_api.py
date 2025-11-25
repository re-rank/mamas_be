"""
MAMAS RAG Backend 테스트 스크립트

이 스크립트는 API가 정상적으로 작동하는지 테스트합니다.
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


def test_health_check():
    """헬스 체크 테스트"""
    print("\n🔍 헬스 체크 테스트...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        response.raise_for_status()
        result = response.json()
        print(f"✅ 성공: {result}")
        return True
    except Exception as e:
        print(f"❌ 실패: {e}")
        return False


def test_document_upload():
    """문서 업로드 테스트"""
    print("\n📄 문서 업로드 테스트...")
    
    payload = {
        "content": """
        안녕하세요. 이것은 테스트 문서입니다.
        
        이 문서는 RAG 시스템의 벡터 검색 기능을 테스트하기 위해 작성되었습니다.
        문서 업로드, 임베딩 생성, 벡터 저장이 정상적으로 작동하는지 확인합니다.
        
        RAG(Retrieval-Augmented Generation)는 검색과 생성을 결합한 기술입니다.
        사용자의 질문에 대해 관련 문서를 먼저 검색한 후, 
        그 문서를 참고하여 LLM이 답변을 생성합니다.
        
        이를 통해 더 정확하고 신뢰할 수 있는 답변을 제공할 수 있습니다.
        """,
        "title": "RAG 시스템 테스트 문서",
        "metadata": {
            "category": "테스트",
            "tags": ["RAG", "테스트", "검색"]
        }
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/documents/upload", json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"✅ 성공: 문서 ID = {result.get('document_id')}, 청크 수 = {result.get('chunks_count')}")
        return result.get('document_id')
    except Exception as e:
        print(f"❌ 실패: {e}")
        return None


def test_search(query: str):
    """검색 테스트"""
    print(f"\n🔍 검색 테스트: '{query}'")
    
    payload = {
        "query": query,
        "top_k": 3
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/search", json=payload)
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ 성공: {result['total']}개 결과 발견")
        for i, item in enumerate(result['results'][:2], 1):
            print(f"\n  [{i}] 점수: {item['score']:.4f}")
            print(f"      제목: {item['title']}")
            print(f"      내용: {item['content'][:100]}...")
        
        return result
    except Exception as e:
        print(f"❌ 실패: {e}")
        return None


def test_chat(message: str):
    """채팅 테스트"""
    print(f"\n💬 채팅 테스트: '{message}'")
    
    payload = {
        "message": message,
        "top_k": 3,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/chat", json=payload)
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ 성공!")
        print(f"\n답변:")
        print(f"{result['answer']}")
        print(f"\n참고 문서: {len(result['search_results'])}개")
        print(f"토큰 사용: {result['usage'].get('total_tokens', 0)}")
        
        return result
    except Exception as e:
        print(f"❌ 실패: {e}")
        return None


def test_collections():
    """컬렉션 목록 조회 테스트"""
    print("\n📊 컬렉션 목록 조회 테스트...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/collections")
        response.raise_for_status()
        result = response.json()
        
        print(f"✅ 성공: {result['total']}개 컬렉션")
        for col in result['collections']:
            print(f"  - {col['name']}: {col.get('points_count', 0)}개 문서")
        
        return result
    except Exception as e:
        print(f"❌ 실패: {e}")
        return None


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("  MAMAS RAG Backend API 테스트")
    print("=" * 60)
    
    # 1. 헬스 체크
    if not test_health_check():
        print("\n⚠️  서버가 실행 중인지 확인해주세요.")
        return
    
    # 2. 컬렉션 목록
    test_collections()
    
    # 3. 문서 업로드
    doc_id = test_document_upload()
    
    # 4. 검색 테스트
    test_search("RAG란 무엇인가요?")
    
    # 5. 채팅 테스트
    test_chat("RAG 시스템에 대해 설명해주세요.")
    
    print("\n" + "=" * 60)
    print("  테스트 완료!")
    print("=" * 60)
    print("\n📚 API 문서: http://localhost:8000/docs")


if __name__ == "__main__":
    run_all_tests()

