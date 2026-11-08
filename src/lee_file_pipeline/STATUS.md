# `lee_file_pipeline` 현재 현황판

교과목 카드 혜택 개체·관계 추출 과제의 별도 M0–M9 현황·제출 경계는 [`과제 산출물 현황과 진행계획`](과제_산출물_현황과_진행계획.md)을 참고한다. 이 현황판의 기존 챗봇 개선 상태와 과제 제출 상태는 별도로 추적한다.

확인 기준: 2026-11-09 로컬 작업 트리와 연결 문서·코드. 현재 브랜치 `feat/file-pipeline-extraction-integrate`, HEAD `5ce52f1`. 아래 시험 결과는 각기 다른 선택 범위이며 합산하지 않는다. 이번 문서 검토 중 테스트·서버·실제 DB·API를 실행하지 않았다. 원격 반영과 실제 데이터 상태는 미확인이다.

## 강사 검토용 현재 검증 요약

- **질문 카드 코드의 마지막 기록 테스트:** 2026-11-08에 v2 UI 테스트 파일 단독 `17 passed`가 기록되어 있다. 버튼 표시와 질문 전달 확인이며 실제 답변 검증은 아니다. 별도로 패널·UI·키 테스트 3개에서 `46 passed in 11.60s`가 기록되어 있으나 다른 실행 범위·시점이다. 두 결과를 더하거나 같은 제출 스냅샷의 검사로 해석하지 않는다. 이번 문서 정리에서는 모두 재실행하지 않았다.
- **질문 카드:** 버튼 네 개의 표시와 질문 전달은 UI 시험 범위다. 바우처·원더·SHOPPER·CLUB1 질문의 실제 그래프 답변은 이번 카드 검사에서 실행·판정하지 않았다. 과거 CLUB1 인터컨티넨탈 객실 할인 질문은 실행 간 할인율이 달랐다는 별도 기록이 있으므로, 현재 질문도 답변 정확성이 확인된 것으로 간주하지 않는다.
- **사람·실데이터 판정:** 실제 PDF 원문 대조, 카드별 혜택 적용 확인, 실제 DB/API, 브라우저, 골든셋 8문항의 사람 판정은 완료 근거가 없다.
- **버전·전달:** 기준 커밋은 `5ce52f1`이고 현재 작업 트리는 수정·미추적 변경이 있다. 따라서 아래의 역사적 테스트 수치가 하나의 고정된 제출 코드 버전을 검증한다고 볼 수 없다.

| 현재 상태 | 아티팩트 | 근거 수준·남은 한계 |
|---|---|---|
| **기존 흐름:** 파일 처리에서 그래프·챗봇까지의 구현은 별도 기존 경로에 있다. 사용자 폴더의 대응 폴더는 대부분 빈 구조다. | [기존 파이프라인 지도](../card_benefit/payment_card/file_pipeline/README.md), [이 폴더 구조](README.md#폴더-구조) | 코드·파일 구조 확인. 빈 폴더는 구현 완료를 뜻하지 않음 |
| **관계·근거:** 중복 관계의 근거를 대표 관계로 재연결하고 원래 ID를 보존한다. 제거된 자기 연결 근거는 별도로 보존한다. | [관계 병합 코드](../card_benefit/payment_card/file_pipeline/chat/retrieval/entity_dedupe.py), [점검 코드](evidence_audit.py), [합성 전후 기록](docs_작업기록/관계-근거-연결-검토.md) | 합성 입력 재현·테스트. 실제 평가 데이터의 발생 여부, 진단 CSV 소비자 호환성 미확인 |
| **출처·화면:** `FP_SOURCE_EVIDENCE=1`은 화면 출처용 별도 근거 조회를 켜며 기본값은 꺼짐이다. `FP_QA_LOG`가 설정되면 QA 기록용 근거 조회는 별도로 실행될 수 있다. | [v2 화면 코드](../card_benefit/payment_card/file_pipeline/chat/ui/app_v2.py), [UI 설명](../card_benefit/payment_card/file_pipeline/chat/ui/README.md), [결함 분석](docs_작업기록/챗봇_결함_분석.md) | 합성 DB 대체 시험만 수행. 이전 기록의 ‘앱 미연결’은 선택 경로 추가 전 상태. 실제 DB 동작·권한·지연·브라우저와 답변 근거의 정확한 연결은 미확인 |
| **v2 대화 화면:** 단독 화면은 현재 Streamlit 세션의 대화 목록·새 대화를 표시하고, 호스트 삽입 화면은 사이드바를 기본 표시하지 않는다. 영구 저장 기능은 없다. | [UI 설명](../card_benefit/payment_card/file_pipeline/chat/ui/README.md), [패널 테스트](../card_benefit/payment_card/tests/test_file_pipeline_chat_panel.py), [UI 테스트](../card_benefit/payment_card/tests/test_file_pipeline_chat_ui_v2.py), [키 분리 테스트](../card_benefit/payment_card/tests/test_file_pipeline_chat_app_v2_keys.py) | 모의 Streamlit·백엔드 검사다. 기록된 테스트 범위와 날짜는 위 [현재 검증 요약](#강사-검토용-현재-검증-요약)을 참고한다. 실제 브라우저·DB·API 결과는 아니다. |
| **카드별 혜택 적용:** 한 문서에 카드 둘과 혜택 하나가 있으면 후보 `OFFERS` 둘이 생기는 합성 사례를 확인했다. 관계 상태 계약은 초안이며 운영 경로에 적용하지 않았다. | [그래프 내보내기 코드](../card_benefit/payment_card/file_pipeline/graph/export.py), [합성 검사](../card_benefit/payment_card/tests/test_file_pipeline_graph_export.py), [계약 초안](docs_작업기록/챗봇_결함_분석.md) | 합성 관찰·설계 제안. 실제 오연결, 카드별 적용, 스키마·검색·화면 전파 미확인 |
| **골든 기대값:** 8문항의 사람 검토 기준을 준비했다. | [사람 확인 준비 기록](../../docs/작업이력/06-챗봇연결-골든셋/2026-11-08-골든기대값-사람확인준비-laptop.md) | 검토 준비만 완료. 실제 질문·기대값·원문 대조 대기 |
| **질문 카드 UI 예시 (답변 검증 아님)** | - 카드 목록은 바우처, 원더 서비스, SHOPPER 해외 호텔, CLUB1 혜택 질문이다.<br>- [정확한 문구](../card_benefit/payment_card/file_pipeline/chat/ui/ui_v2.py)<br>- [버튼 표시·질문 전달 테스트](../card_benefit/payment_card/tests/test_file_pipeline_chat_ui_v2.py) | - `17 passed`는 UI 동작 결과다(2026-11-08). 실제 그래프 답변의 정확도는 확인하지 않았다.<br>- CLUB1 인터컨티넨탈 객실 할인 질문의 과거 실행 간 수치 차이는 [별도 기록](../../docs/작업이력/06-챗봇연결-골든셋/2026-11-06-답변규칙v3-충돌탐지-재현성도구-laptop.md)에 있다. 현재 카드 질문에 대한 답도 검증된 것은 아니다. |

**Git 인계 상태:** 2026-11-09 확인 시 `src/lee_file_pipeline/`은 `??`(미추적)이었다. 기존 파이프라인·테스트·문서에도 로컬 수정이 있어 기준 커밋만으로 현재 변경 내용을 재현할 수 없다. 강사에게 실제 코드까지 전달하려면 포함 파일 범위와 작업 트리 스냅샷을 별도로 정해야 한다. 이 문서 정리에서는 스테이징·커밋·푸시를 하지 않았다.

## 다음 사람 결정과 행동

1. `OFFERS`를 문서 인덱스에서 생긴 **후보**와 카드별 적용을 원문으로 **확인한 연결**로 나눌지, 검토 주체·근거·권한·구버전 호환 정책을 정한다. [계약 초안](docs_작업기록/챗봇_결함_분석.md)은 제안이며 `verified` 상태를 실제로 부여한 결과가 아니다.
2. 허용된 환경에서 실제 문서·쪽·카드 연결과 브라우저 표시를 사람 검토표로 확인한다. [화면 검토 절차](docs_작업기록/챗봇_자료_관계도_검토.md)는 아직 실행하지 않았다. 골든셋 8문항은 원문 자료가 준비된 뒤 별도로 판정한다.
3. 기존 진단 CSV 소비자와 별도 보존 근거의 사용처를 확인한 뒤 호환 방식을 정한다. [관계·근거 기록](docs_작업기록/관계-근거-연결-검토.md)에 범위와 위험을 남겼다.

## 이전 로컬 검증 기록

아래는 **2026-11-08 수정 전 README·STATUS에 남아 있던 과거 기록**이다. 서로 다른 시점·선택 범위의 결과이며 합산하거나 이번 문서 작업의 새 시험으로 취급하지 않는다. 세 [상세 기록](docs_작업기록/관계-근거-연결-검토.md), [화면 기록](docs_작업기록/챗봇_자료_관계도_검토.md), [결함 기록](docs_작업기록/챗봇_결함_분석.md)에는 당시 관찰 일부가 있지만 아래 모든 수치·명령행 원문이 있는 것은 아니다.

| 당시 범위·시점 | 기록된 결과 | 출처·한계 |
|---|---|---|
| 기존 파이프라인 복원 뒤 추출 CLI 도움말과 관련 테스트 | CLI `--help` 성공; `478 passed, 4 subtests passed in 62.16s` | 수정 전 README에 `.venv/bin/python` 실행으로 기록. 원본 명령 로그 미확인; 당시 `uv run` 예시와 동일 명령이었다고 볼 수 없음 |
| 폴더 이름 변경 뒤 사용자 점검 코드 테스트 | `20 passed in 0.57s` | 수정 전 README·STATUS 기록. 기존 파이프라인 전체 결과가 아님 |
| 이름 변경 전 점검 코드와 기존 관련 테스트의 함께 실행 | `500 passed, 4 subtests passed in 53.01s` | 수정 전 README·STATUS 기록. 위 `20`과 합산하지 않음 |
| 챗봇 표시 검증 추가 뒤 사용자 폴더 전체 테스트 | `29 passed in 5.05s` | 수정 전 README·STATUS 기록. 당시 정확한 명령행은 보존되지 않음 |
| 같은 시기 사용자 폴더와 기존 관련 테스트의 함께 실행 | `509 passed, 4 subtests passed in 63.85s` | 수정 전 README·STATUS와 [화면 기록](docs_작업기록/챗봇_자료_관계도_검토.md). 위 `29`와 합산하지 않음 |
| 선택적 화면 근거 연결의 사용자 점검·챗봇·관계 병합 선별 테스트 | `159 passed in 68.04s (0:01:08)` | 수정 전 STATUS 기록; 원본 명령 로그 미확인. 합성 DB 대체 시험만 수행; 실제 DB·브라우저 미확인 |

다음은 **2026-11-08 문서 수정 직전 실제 관찰한 실행 명령**이다. 선택 범위는 위 세 파일이고 결과는 `46 passed in 11.60s`였다. 이 문서 정리 중에는 재실행하지 않았다. README의 다른 테스트 명령은 별도의 재현용 예시다.

```bash
UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m pytest -q src/card_benefit/payment_card/tests/test_file_pipeline_chat_panel.py src/card_benefit/payment_card/tests/test_file_pipeline_chat_ui_v2.py src/card_benefit/payment_card/tests/test_file_pipeline_chat_app_v2_keys.py
```

당시 [보조 노트북](notebooks_점검노트북/관계_근거_확인.ipynb)은 코드 셀 4개를 Python으로 순차 실행해 확인했다. Jupyter 커널·화면 실행은 소켓 제한으로 확인하지 못했고 저장된 출력은 없다. 기존 파이프라인의 파일 기반 테스트, 사용자 점검 코드 테스트, 합성 DB 대체 시험은 실제 PDF 정확도나 사람의 골든셋 판정을 대신하지 않는다.
