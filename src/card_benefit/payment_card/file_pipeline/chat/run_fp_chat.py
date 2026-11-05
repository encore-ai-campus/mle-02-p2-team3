"""Streamlit entrypoint for the opt-in fp_chat adapter."""
import os
from pathlib import Path
import runpy
import sys

import streamlit as st

HERE = Path(__file__).resolve().parent
CHATBOT_DIR = HERE.parents[3] / "graphrag_chatbot"
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))
from fp_chat_patch import apply

# 팀 llm.py는 Anthropic을 쓰므로, 팀 코드가 import되기 전에 OpenAI 어댑터를 먼저 끼운다(D2, D3).
# 키는 환경 변수로만 받는다. .env는 열지 않는다.
if not os.environ.get("OPENAI_API_KEY"):
    st.set_page_config(page_title="GraphRAG 챗봇")
    st.error("OPENAI_API_KEY 환경 변수가 필요합니다. 터미널에서 export 한 뒤 다시 실행하세요.")
    st.stop()
from openai_llm_patch import install

install()
apply()
original_set_page_config = st.set_page_config

def _set_page_config_with_mode(*args, **kwargs):
    original_set_page_config(*args, **kwargs)
    st.set_page_config = original_set_page_config
    st.info("우리 카드 데이터(fp_chat) 모드")

st.set_page_config = _set_page_config_with_mode
runpy.run_path(str(CHATBOT_DIR / "app.py"), run_name="__main__")
st.set_page_config = original_set_page_config
