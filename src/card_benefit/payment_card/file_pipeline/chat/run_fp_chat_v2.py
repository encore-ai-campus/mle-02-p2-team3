"""Launch the v2 fp_chat screen with the existing OpenAI and graph adapters."""
from __future__ import annotations

import os
from pathlib import Path
import runpy
import sys

import streamlit as st
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[4]
CHATBOT_DIR = REPO_ROOT / "src" / "graphrag_chatbot"
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from fp_chat_patch import apply
from openai_llm_patch import install

# Existing exported variables take precedence; otherwise dotenv loads the repository setting at runtime.
load_dotenv(os.environ.get("FP_CHAT_ENV_FILE") or REPO_ROOT / ".env", override=False)
# 셸 source 로 .env(CRLF)를 읽은 터미널에서는 값 끝에 '\r' 이 남아 DB 이름이 'postgres\r' 이 된다. 앞뒤 공백·줄바꿈을 제거한다.
for _name in ("DB_URL", "FP_DATABASE_URL", "DB_URI", "OPENAI_API_KEY"):
    if os.environ.get(_name):
        os.environ[_name] = os.environ[_name].strip()
if not os.environ.get("DB_URL"):
    for name in ("FP_DATABASE_URL", "DB_URI"):
        if os.environ.get(name):
            os.environ["DB_URL"] = os.environ[name]
            break

if not os.environ.get("OPENAI_API_KEY"):
    st.set_page_config(page_title="카드 혜택 챗봇")
    st.error("OPENAI_API_KEY 환경 변수가 필요합니다.")
    st.stop()

install(
    max_cost_usd=float(os.environ.get("FP_MAX_COST_USD", "0.10")),
    sleep=float(os.environ.get("FP_LLM_SLEEP", "0.3")),
)
apply()
runpy.run_path(str(HERE / "ui" / "app_v2.py"), run_name="__main__")
