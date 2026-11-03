"""저장소의 OpenAI/LangChain 관례에 맞춘 지연 로딩 LLM 어댑터."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any


def create_llm_call(model: str, api_key_env: str = "OPENAI_API_KEY", *,
                    client_factory: Callable[..., Any] | None = None) -> Callable[[str], str]:
    """모델 호출 함수를 만든다. 키 값은 환경변수에서만 읽고 표시하지 않는다.

    기본 클라이언트는 저장소의 `ChatOpenAI(model=..., api_key=...)` 관례다.
    client_factory는 테스트에서 가짜 클라이언트를 주입하기 위한 선택 인자다.
    """
    if not model:
        raise ValueError("모델 이름을 지정해야 합니다.")
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise RuntimeError(f"환경변수 {api_key_env}에 API 키를 설정해야 합니다.")
    if client_factory is None:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as error:
            raise RuntimeError("OpenAI 호출에 필요한 langchain-openai SDK가 설치되어 있지 않습니다.") from None
        client_factory = ChatOpenAI
    try:
        client = client_factory(model=model, api_key=api_key)
    except Exception as error:
        raise RuntimeError(f"LLM 클라이언트 생성 실패 ({type(error).__name__}).") from None

    def llm_call(prompt: str) -> str:
        try:
            response = client.invoke(prompt)
        except Exception as error:
            # SDK 예외에는 요청 정보가 포함될 수 있어 원문 메시지를 전달하지 않는다.
            raise RuntimeError(f"LLM 호출 실패 ({type(error).__name__}).") from None
        content = getattr(response, "content", response)
        if not isinstance(content, str):
            raise RuntimeError("LLM 응답 본문이 문자열이 아닙니다.")
        return content

    return llm_call
