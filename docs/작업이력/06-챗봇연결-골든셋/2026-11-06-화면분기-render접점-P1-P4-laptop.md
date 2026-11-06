# 2026-11-06 팀 화면 탭 분기: file_pipeline 쪽 render 접점 (P1~P4)

- PC: laptop
- 확인: `hostname`과 `/etc/machine-id` 앞 8자가 `CLAUDE.local.md`의 HOST·MACHINE_ID_PREFIX와 일치함(직접 확인).
- 브랜치: `feat/streamlit-pipeline-split` (폴더 정리 U 단계 병합 `4c0f623` 위, 로컬 전용, 푸시 안 함)
- 설계 문서: [탭-분기-렌더링-설계.md](../../설계/탭-분기-렌더링-설계.md)
- 관련 이력: [폴더 정리 T·E·R·A·U](2026-11-06-폴더정리-T-E-R-A단계-laptop.md)

## 배경

팀 Streamlit 앱의 탭(또는 좌우 분할)에서 `db_pipeline`과 `file_pipeline`을 따로 보여주기로 했다. 이쪽(`file_pipeline`)은 호스트가 함수 두 개만 부르면 화면이 뜨게 만든다. 로직(`rag`, `fp_chat_patch`, `answer/` 등)은 바꾸지 않았고, 상대 쪽 코드와 호스트 앱은 읽지 않았다.

## 한 일

| 단계 | 내용 | 커밋 |
|---|---|---|
| 설계 | 공개 접점, 키 네임스페이스, 호스트 소유 항목, 위험, 검증 계획 문서 | 66c900a |
| P1 | `chat/ui/app_v2.py` 화면 본문을 `render(*, key_prefix)`로 감싸고 `set_page_config`를 단독 실행으로 한정 | 7cacf1f |
| P2 | 세션·위젯 키에 `key_prefix` 적용(기본 접두어 `v2`에서는 기존 키 유지), 사이드바를 본문 컨테이너로 이동, 두 번 렌더 AppTest 추가 | 1ef1d08 |
| 보정 | 폴더 정리 위로 리베이스한 뒤 테스트 임포트·설계 문서 위치 수정 | 0ead382 |
| P3·P4 | `chat/panel.py`(`prepare_backend()`, `render()`) 추가, `run_fp_chat_v2.py`를 `set_page_config → prepare_backend() → render(key_prefix="v2")`로 단순화, 계약 테스트 5개 | 41a39b5 |

- 호스트가 부를 접점: `from payment_card.file_pipeline.chat.panel import prepare_backend, render`
- 작업 방식: 파일 수정·테스트는 Codex가 하고(쓰기 권한 별도 지침), diff와 테스트는 직접 다시 확인한 뒤 커밋했다. Codex 샌드박스는 `.git`이 읽기 전용이라 git은 직접 했다.

## 실행한 검증과 결과

- 관련 테스트(chat·평가·extraction·graph·노트북 점검·chunking·doc_index·traceability + 새 테스트): **397개 통과**(직접 재실행).
- 새 테스트: 임포트 부수효과 없음, 키 없음 안내(어댑터 미호출), 멱등(`install`·`apply` 각 한 번), `render` 위임, 단독 진입점. 두 번 렌더(`key_prefix="a"`, `"b"`)에서 예외 0건·위젯 키 비중복·상태 분리.
- 테스트는 실제 `.env`를 읽지 않도록 `FP_CHAT_ENV_FILE`을 존재하지 않는 경로로 지정함(직접 확인).
- 사용자가 2026-11-06 23:34에 Streamlit 서버를 띄워 챗봇이 정상이라고 확인했다. 서버 기동 시각 기준이며 어느 작업 폴더인지와 질문 기록은 확인하지 못했다. **P3 이후 코드로는 아직 실행해 보지 않았다.**

## 직접 확인한 사실과 추측

- 직접 확인: `install()`은 사용량(`_USAGE`)을 초기화하지 않고, 사용량은 모듈 전역이라 프로세스 수명 동안 누적된다. 이전에는 화면 동작마다 `install()`·`apply()`가 다시 실행됐고 지금은 프로세스당 한 번이다.
- 추측(실행 검증 안 함): 위 변경이 비용 상한(`FP_MAX_COST_USD`)의 의미를 바꾸지 않는다는 판단. 코드 읽기 기준이다.

## 못 한 것과 남은 위험

- **실제 Streamlit 화면(브라우저) 미실행.** 탭 안의 입력창 위치, 그래프 높이, 다른 탭 영향은 사용자가 확인해야 한다. 이 브랜치 작업 폴더에는 `.env`가 없어 `FP_CHAT_ENV_FILE`로 지정하거나 환경 변수를 넣어야 한다.
- 호스트(팀 앱)와의 연결, 함수 이름 합의는 하지 않았다. 호스트가 `rag`·`llm`·`db`·`ui` 같은 최상위 이름을 쓰면 충돌할 수 있고(`sys.path`에 `src/graphrag_chatbot`, `chat/`이 들어감), `openai_llm_patch.install()`이 전역 `sys.modules["llm"]`를 교체한다.
- `st.rerun()`은 앱 전체 스크립트를 다시 실행한다(Streamlit 동작 기준 추정). `@st.fragment`로 범위를 좁히는 방법은 검증하지 않았다.
- wheel 패키징 목록(`pyproject.toml`)에 `file_pipeline`이 없다(Codex 읽기 전용 진단). 소스 경로를 `PYTHONPATH`로 쓰는 실행만 가정했다.
- 같은 접두어를 두 번 쓰는 오용은 테스트로 막지 않았다.

## 다음에 할 일

1. 이 브랜치 작업 폴더에서 `run_fp_chat_v2.py`를 실행해 화면 확인(사용자).
2. 팀원과 함수 이름(`prepare_backend`, `render`), 최상위 이름 충돌, `llm` 교체 합의.
3. 팀 호스트 앱에 연결하고 탭·좌우 분할 레이아웃 확인.
4. 이 브랜치를 어디로 병합할지와 푸시 여부 결정.
