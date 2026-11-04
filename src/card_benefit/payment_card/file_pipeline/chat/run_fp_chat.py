"""Streamlit entrypoint for the opt-in fp_chat adapter."""
from pathlib import Path
import runpy
import sys

import streamlit as st

HERE = Path(__file__).resolve().parent
CHATBOT_DIR = HERE.parents[3] / "graphrag_chatbot"
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))
from fp_chat_patch import apply

apply()
original_set_page_config = st.set_page_config

def _set_page_config_with_mode(*args, **kwargs):
    original_set_page_config(*args, **kwargs)
    st.set_page_config = original_set_page_config
    st.info("우리 카드 데이터(fp_chat) 모드")

st.set_page_config = _set_page_config_with_mode
runpy.run_path(str(CHATBOT_DIR / "app.py"), run_name="__main__")
st.set_page_config = original_set_page_config
