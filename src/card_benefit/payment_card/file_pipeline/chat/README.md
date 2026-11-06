# chat/

그래프 기반 카드 혜택 챗봇의 실행 화면, 사용자 소유 연결 어댑터, 오프라인 평가·검수 도구를 둔다. `src/graphrag_chatbot/`은 팀 코드이며 이 폴더의 어댑터로만 연결한다.

## 실행용 파일과 연결부

| 파일 | 역할 |
|---|---|
| `__init__.py` | 챗봇 관련 모듈을 패키지로 표시한다. |
| `run_fp_chat.py` | Streamlit 진입점으로 팀 화면을 띄우고 `fp_chat` 연결부와 OpenAI 어댑터를 적용한다. |
| `run_fp_chat_v2.py` | 사용자 소유 v2 화면 진입점으로 기존 OpenAI 및 그래프 어댑터를 적용한다. |
| `app_v2.py` | v2 Streamlit 화면을 구현한다. 직접 실행하면 팀 `rag`의 Anthropic 임포트 오류가 발생하므로 직접 실행하지 않고 `run_fp_chat_v2.py`로 실행한다. |
| `ui_v2.py` | 화면과 독립적인 질문 분석, 출처 및 비교표 구성 도우미다. |
| `fp_chat_patch.py` | 팀 GraphRAG 모듈에 `fp_chat` 조회, Q/A 기록, 선택적 하위 그래프 처리를 연결하는 옵트인 어댑터다. |
| `openai_llm_patch.py` | 팀 챗봇 LLM 호출을 OpenAI로 바꾸는 지연 적용 어댑터이며 모듈 임포트만으로 API를 호출하지 않는다. |
| `answer_format.py` | 답변 형식 지침과 모델 호출 없는 형식 진단을 제공한다. |
| `answer_eval.py` | 저장된 챗봇 답변 판정 함수를 제공하며, 런타임 Q/A 기록에서도 사용한다. |
| `answer_check.py` | 답변 숫자가 검색된 그래프 근거 범위에 있는지 확인하는 순수 판정 함수다. |
| `qa_log.py` | Q/A, 지연시간, 답변 형식·숫자 확인 결과를 로컬 진단 기록으로 구성하고 쓴다. |
| `db_pool.py` | `fp_chat` 어댑터의 PostgreSQL 조회를 위한 지연 초기화 풀 래퍼다. |

두 화면 실행 명령은 저장소 루트에서 사용한다.

```bash
PYTHONPATH=src:src/card_benefit uv run --locked streamlit run src/card_benefit/payment_card/file_pipeline/chat/run_fp_chat.py
PYTHONPATH=src:src/card_benefit uv run --locked streamlit run src/card_benefit/payment_card/file_pipeline/chat/run_fp_chat_v2.py
```

첫 명령은 팀 화면과 사용자 연결부를 사용하고, 둘째 명령은 사용자 v2 화면을 사용한다. `app_v2.py`를 직접 실행하지 않는다.

## 하위 폴더

| 폴더 | 내용 |
|---|---|
| [`eval/`](eval/README.md) | 질문 생성, 골든셋, 평가 실행, 판정, 검색 진단 등 오프라인 평가 도구 12개와 골든셋 템플릿이다. |
| [`retrieval/`](retrieval/README.md) | 검색 결과 병합, 시드 보완, 출처 라벨 등 검색 보조 도구 3개다. |
| [`review/`](review/README.md) | 답변과 그래프 근거를 사람이 대조하는 검수 자료 생성 도구 2개다. |

이동한 도구도 같은 패키지 아래라서 `payment_card.file_pipeline.chat.eval.<모듈>`, `payment_card.file_pipeline.chat.review.<모듈>` 로 실행하고, 검색 보조 모듈은 `payment_card.file_pipeline.chat.retrieval.<모듈>` 로 임포트한다(예: `python -m payment_card.file_pipeline.chat.eval.run_eval`). 스크립트식 임포트(`from answer_eval import ...`)가 필요한 도구는 `PYTHONPATH` 에 `chat/` 폴더를 포함한다.

## 데이터·초안 문서

| 파일 | 역할 |
|---|---|
| `카드혜택-Supabase-구조-보완-초안.md` | Supabase 카드 혜택 구조 보완을 정리한 초안 문서다. |

평가·검수 도구도 기본 데이터 경로에서 데이터베이스나 OpenAI를 자동 호출하지 않으며, 호출 기능이 있는 경우 코드에서 명시적으로 실행 경로를 선택해야 한다.
