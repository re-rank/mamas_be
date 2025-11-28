"""LLM Handler - LLM 기반 답변 생성"""

import logging
from typing import Any, Optional

from openai import OpenAI

from src.config import app_config as config

logger = logging.getLogger(__name__)


# 기본 시스템 프롬프트
DEFAULT_SYSTEM_PROMPT = """You are a friendly and professional AI assistant.
You provide accurate and useful answers based on the provided context information.

Follow these guidelines when answering:
1. Prioritize information from the provided context
2. If information is not in the context, clearly state "This information is not available in the provided context"
3. Provide clear and structured answers
4. Mention relevant sources when necessary
5. **IMPORTANT: Always respond in the same language as the user's question**
   - If the user asks in Korean, respond in Korean
   - If the user asks in English, respond in English
   - If the user asks in Japanese, respond in Japanese
   - Match the language of any other language the user uses
"""


class LLMHandler:
    """LLM 기반 답변 생성 핸들러"""
    
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ):
        """LLM 핸들러 초기화"""
        self.model = model or config.LLM_MODEL
        self.temperature = temperature if temperature is not None else config.LLM_TEMPERATURE
        self.max_tokens = max_tokens or config.LLM_MAX_TOKENS
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        
        # OpenAI 클라이언트 초기화
        self.client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            timeout=config.LLM_TIMEOUT
        )
        
        logger.info("🤖 LLM 핸들러 초기화 완료")
        logger.info(f"    모델: {self.model}")
        logger.info(f"    온도: {self.temperature}")
        logger.info(f"    최대 토큰: {self.max_tokens}")
    
    def _build_context(self, search_results: list[dict[str, Any]]) -> str:
        """검색 결과로부터 컨텍스트 구성"""
        if not search_results:
            return "No relevant information found."

        context_parts = []
        for i, result in enumerate(search_results, 1):
            content = result.get("content", "")
            title = result.get("title", "")
            score = result.get("score", 0)

            if content:
                part = f"[Document {i}]"
                if title:
                    part += f" ({title})"
                part += f" [Relevance: {score:.2f}]\n{content}"
                context_parts.append(part)

        return "\n\n---\n\n".join(context_parts)
    
    def _build_messages(
        self,
        question: str,
        context: str,
        conversation_history: Optional[list[dict]] = None
    ) -> list[dict[str, str]]:
        """LLM 메시지 구성"""
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # 대화 기록 추가
        if conversation_history:
            for msg in conversation_history[-6:]:  # 최근 6개 메시지만
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        # 사용자 질문과 컨텍스트
        user_message = f"""Please answer the question based on the following context information.

### Context:
{context}

### Question:
{question}

### Answer:"""
        
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def generate_answer(
        self,
        question: str,
        search_results: list[dict[str, Any]],
        conversation_history: Optional[list[dict]] = None,
        temperature: Optional[float] = None
    ) -> dict[str, Any]:
        """RAG 기반 답변 생성"""
        try:
            # 컨텍스트 구성
            context = self._build_context(search_results)
            
            # 메시지 구성
            messages = self._build_messages(question, context, conversation_history)
            
            # LLM 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=self.max_tokens
            )
            
            answer = response.choices[0].message.content
            
            # 토큰 사용량
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }
            
            logger.info(f"✅ 답변 생성 완료 (토큰: {usage['total_tokens']})")
            
            return {
                "answer": answer,
                "model": self.model,
                "usage": usage,
                "context_count": len(search_results),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"❌ 답변 생성 실패: {e}")
            return {
                "answer": "Sorry, an error occurred while generating the answer.",
                "error": str(e),
                "success": False
            }
    
    def generate_answer_stream(
        self,
        question: str,
        search_results: list[dict[str, Any]],
        conversation_history: Optional[list[dict]] = None,
        temperature: Optional[float] = None
    ):
        """스트리밍 답변 생성"""
        try:
            context = self._build_context(search_results)
            messages = self._build_messages(question, context, conversation_history)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=self.max_tokens,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"스트리밍 답변 실패: {e}")
            yield f"An error occurred: {str(e)}"
    
    def chat(
        self,
        message: str,
        conversation_history: Optional[list[dict]] = None
    ) -> str:
        """일반 채팅 (RAG 없음)"""
        try:
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            if conversation_history:
                for msg in conversation_history[-10:]:
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            
            messages.append({"role": "user", "content": message})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"채팅 실패: {e}")
            return f"An error occurred: {str(e)}"
    
    def update_system_prompt(self, prompt: str):
        """시스템 프롬프트 업데이트"""
        self.system_prompt = prompt
        logger.info("시스템 프롬프트 업데이트됨")

