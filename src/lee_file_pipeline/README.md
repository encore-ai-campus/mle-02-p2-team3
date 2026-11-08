# `lee_file_pipeline` — 강사 검토 시작점

## 1분 요약

**교과목 과제 산출물:** 카드 혜택 도메인 기준의 M0–M9 상태와 남은 실행 항목은 [`과제 산출물 현황과 진행계획`](과제_산출물_현황과_진행계획.md)에서 확인한다. 추출 계약과 그래프 검토 양식은 각각 [`혜택 추출 계약`](extraction_혜택추출/과제_추출-계약.md), [`그래프 검증·시연 안내`](graph_그래프/과제_그래프-검증-안내.md)에 있다. 원문과 실제 실행 데이터는 저장소 밖에서 관리한다.

카드 상품설명서를 **문서 인덱스 → 원문 추적 → 청킹 → 혜택 추출·검증 → 그래프 → 챗봇**으로 잇는 기존 구현은 [`payment_card/file_pipeline`](../card_benefit/payment_card/file_pipeline/README.md)에 있다. 아래 내용은 작업 기록과 현재 로컬 작업 트리에서 확인한 사용자 작업 범위다. 이 폴더에는 추가 점검 코드·합성 예제·테스트·검토 기록이 있고, 기존 파이프라인 수정 코드는 기존 경로에 있다. 아래 대응 폴더 대부분은 빈 구조이며 기존 구현을 이곳으로 옮긴 것은 아니다.

- **직접 한 일:** 관계와 근거의 연결을 점검하는 [`evidence_audit.py`](evidence_audit.py), 합성 재현 [`defect_repro.py`](defect_repro.py), [사용자 테스트](tests_테스트/), [검토 기록](docs_작업기록/)을 작성했다. 기존 경로에서는 추출 이어하기·파일 저장 보호, 프롬프트 규칙, 그래프 CSV 게시, 관계 병합·출처 표시·v2 화면·호스트 백엔드를 수정했다. 위치와 범위는 [코드 변경 안내](코드-변경-안내.md)와 [현재 현황판](STATUS.md)에 구분했다.
- **대표 합성 사례:** 중복 관계 `e2`가 `e1`로 합쳐질 때, 수정 전에는 `e2`를 가리키는 근거가 남았다. 수정 후에는 근거를 `e1`에 재연결하고 원래 ID를 보존했다. [입력·전후 결과](docs_작업기록/관계-근거-연결-검토.md)는 합성 재현이며 실제 데이터에서 같은 현상이 있었는지는 미확인이다.
- **검증 경계:** 파일 기반·합성 입력 테스트와 코드 확인의 근거는 있다. 실제 PDF 정확도, 실제 DB·API, 브라우저 화면, 카드별 혜택 적용 여부는 이 근거로 검증되지 않는다. 범위별 현재 결과와 미확인 항목은 [STATUS](STATUS.md)에 있다.
- **코드 길잡이:** 변경 위치, 입력→처리→출력, 연결된 테스트와 검증 한계는 [코드 변경 안내](코드-변경-안내.md)에 정리했다.
- **다음 사람 결정:** 문서 인덱스에서 만든 카드→혜택 `OFFERS`를 **후보 연결**과 **카드별 적용 확인 연결**로 어떻게 구분하고, 누가 어떤 원문 근거로 확인할지 정해야 한다. [설계 초안과 합성 관찰](docs_작업기록/챗봇_결함_분석.md)을 먼저 검토한다. 이 폴더는 현재 Git에서 미추적이므로 강사 인계 시 명시적으로 포함해야 한다.

## 강사님 5분 검토 경로

1. **0–1분 — 작업 범위:** 이 요약과 [소유·근거 지도](#소유근거-지도)에서 기존 파이프라인과 사용자 추가 점검물을 구분한다.
2. **1–2분 — 현재 상태:** [현황판](STATUS.md)의 검증 요약과 다음 결정을 본다. 테스트 통과와 실제 카드 혜택 정확성은 다른 판정이다.
3. **2–4분 — 대표 코드 변경:** [코드 변경 안내의 대표 변경](코드-변경-안내.md#먼저-볼-대표-변경)에서 추출 파일 보호, 관계·근거 연결, 챗봇 출처 표시를 코드·테스트와 함께 확인한다.
4. **4–5분 — 재현과 한계:** [관계·근거 전후 기록](docs_작업기록/관계-근거-연결-검토.md#합성-재현)을 읽고, 값이 합성이라는 점과 실제 자료에서의 검증이 남아 있다는 점을 확인한다.

### 문서와 증거를 읽는 기준

- **README:** 작업 목적, 코드 소유 위치, 검토 순서.
- **STATUS:** 날짜가 붙은 현재 로컬 상태. 과거 상태와 다르면 최신 기준 날짜의 표를 우선한다.
- **코드 변경 안내:** 코드·함수·테스트 위치의 지도다. 테스트를 실행했다는 기록은 STATUS나 작업이력에서 확인한다.
- **작업 기록:** 당시의 재현·검토·테스트 결과다. 결과가 현재 작업 트리에서 다시 확인됐다는 뜻은 아니다.
- **코드와 테스트:** 구현 동작의 기준이다. 합성·모의 테스트는 실제 PDF·DB·API·브라우저나 카드별 적용 사실을 증명하지 않는다.

**검토 스냅샷:** 기준 커밋은 `5ce52f1`이다. 현재 작업 트리는 수정·미추적 변경이 있고 `src/lee_file_pipeline/` 전체도 미추적이므로, 이 문서만으로 강사에게 전달된 코드 묶음이나 개인별 변경 귀속을 확정할 수 없다. 정확한 제출 범위는 현재 작업 트리를 포함하는 방식으로 따로 고정해야 한다.

## 내가 진행한 순서

1. **코드 위치를 시험하고 복원했다.** 작업이력에는 중간 이동 때 파일 337개가 있었다고 기록되어 있다. 이후 기존 실행 코드를 `src/card_benefit/payment_card/file_pipeline/`에 두도록 복원했다. 337개는 현재 `src/lee_file_pipeline/`의 파일 수나 최종 코드 위치를 뜻하지 않는다. ([경로 복원 이력](../../docs/작업이력/99-기타/2026-11-08-강사검토안내-코드경로복원-laptop.md), [폴더 이동 이력](../../docs/작업이력/99-기타/2026-11-08-프로젝트현황-폴더관리-laptop.md))
2. **강사 검토 위치를 만들었다.** 기존 구조를 이름만 대응시키고 영어 접두사와 한글 역할명을 붙였다. 현재 빈 `.gitkeep` 폴더는 안내용이며 전체 파이프라인을 이곳에서 실행하지 않는다. ([구조 대조 이력](../../docs/작업이력/99-기타/2026-11-08-사용자폴더-구조대조-laptop.md), [이름 정리 이력](../../docs/작업이력/99-기타/2026-11-08-사용자폴더-영어한글이름-laptop.md), [폴더 구조](#폴더-구조))
3. **챗봇의 관계·근거 문제를 조사했다.** 관계 병합, 문서 쪽 표시, 다중 카드 혜택 관계를 합성 입력과 코드로 점검했다. 확인된 합성 문제는 기존 `file_pipeline` 경로에서 수정하고 회귀 검사를 연결했다. 실제 자료에서도 같은 현상이 있었는지는 미확인이다. ([결함 분석](docs_작업기록/챗봇_결함_분석.md), [관계·근거 전후 재현](docs_작업기록/관계-근거-연결-검토.md), [코드 변경 지도](코드-변경-안내.md))
4. **강사 검토용 보조 자료를 추가했다.** 관계·근거 점검 CLI, 합성 예제, 테스트, 노트북과 검토 문서를 이 폴더에 두었다. 이 자료는 기존 실행 파이프라인을 대체하지 않고 운영 DB를 수정하지 않는다. ([점검 코드](evidence_audit.py), [합성 재현](defect_repro.py), [테스트](tests_테스트/), [검토 기록](docs_작업기록/))
5. **실제 검증은 남아 있다.** 카드별 혜택 연결과 답변 근거의 정확성, 브라우저·DB 동작은 사람과 허용된 환경에서 확인해야 한다. 합성 테스트 통과만으로 완료 처리하지 않았다. ([현재 현황판](STATUS.md), [사용자 검토표](docs_작업기록/챗봇_자료_관계도_검토.md#실제-연결-확인을-위한-사용자-검토표-아직-실행하지-않음))

작업이력은 같은 날짜 안의 세부 순서를 완전히 보증하지 않는다. 따라서 진행 순서는 날짜의 분 단위 순서가 아니라 **코드 경로 결정 → 강사 검토 구조 준비 → 결함 조사와 로컬 수정 → 합성 검증 자료 구성**의 단계로 읽는다.

## 소유·근거 지도

| 확인 대상 | 실제 아티팩트 | 근거 수준 |
|---|---|---|
| 기존 파일 처리·그래프·챗봇 | [`file_pipeline` 지도](../card_benefit/payment_card/file_pipeline/README.md), [`doc_index`](../card_benefit/payment_card/file_pipeline/doc_index/README.md), [`chunking`](../card_benefit/payment_card/file_pipeline/chunking/README.md), [`extraction`](../card_benefit/payment_card/file_pipeline/extraction/README.md), [`chat`](../card_benefit/payment_card/file_pipeline/chat/README.md) | 기존 코드·문서. 이 폴더의 빈 대응 폴더와 구별 |
| 이현근의 관계·근거 점검 | [`evidence_audit.py`](evidence_audit.py), [합성 입력](examples_합성예제/synthetic_graph.json), [테스트](tests_테스트/test_evidence_audit.py), [보조 노트북](notebooks_점검노트북/관계_근거_확인.ipynb) | 합성 입력·파일 기반 검사. 실제 DB·원문 판정 아님 |
| 이현근의 기존 경로 관계 병합 수정 | [`entity_dedupe.py`](../card_benefit/payment_card/file_pipeline/chat/retrieval/entity_dedupe.py), [전후 재현 기록](docs_작업기록/관계-근거-연결-검토.md) | 합성 전후 재현. 실제 발생 여부 미확인 |
| 이현근의 기존 경로 출처·v2 화면 수정 | [v2 화면](../card_benefit/payment_card/file_pipeline/chat/ui/README.md), [사용자 테스트](tests_테스트/test_chat_graph_display.py), [표시 검토 기록](docs_작업기록/챗봇_자료_관계도_검토.md) | 합성 DB 대체·화면 구성 검사. 브라우저·실 DB 미확인 |
| 카드별 혜택 연결의 남은 판단 | [합성 결함 재현](defect_repro.py), [결함 분석·계약 초안](docs_작업기록/챗봇_결함_분석.md) | 합성 관찰과 제안. 스키마·운영 정책 미적용 |

## 폴더 구조

기존 `payment_card/file_pipeline/`과 대응되는 계층에 영어 이름과 한글 역할을 붙였다. 아래의 빈 폴더는 **위치만 준비**했으며 기존 구현·데이터를 복사하지 않았다.

| 사용자 폴더 | 역할 | 현재 상태 |
|---|---|---|
| `doc_index_문서인덱스/`, `doc_index_문서인덱스/adapters_카드사변환/` | 문서 인덱스·카드사 변환 | 구조만 준비 |
| `chunking_문서분할/` | 원문 청킹 | 구조만 준비 |
| `extraction_혜택추출/` 및 하위 `eval_평가/`, `report_보고/`, `review_검토/` | 추출·평가·보고·검토 | 구조만 준비 |
| `extraction_혜택추출/pilot_hana_15299_하나파일럿/` | 기존 하나 파일럿 대응 위치 | 이름만 준비; 결과 없음 |
| `graph_그래프/`, `graph_그래프/cypher_사이퍼/` | 그래프 변환·질의 | 구조만 준비 |
| `chat_챗봇/` 및 하위 답변·평가·검색·검토·화면 폴더 | 챗봇 관련 작업 | 구조만 준비 |
| `ledger_장부/`, `sql_스키마/` | 장부 보조·SQL | 구조만 준비 |
| `notebooks_점검노트북/`, `notebooks_점검노트북/학습용/` | 보조 노트북 | 합성 노트북 1개; 개인 학습 파일 없음 |
| `docs_작업기록/`, `examples_합성예제/`, `tests_테스트/` | 사용자 검토 기록·합성 입력·테스트 | 사용 중 |

빈 최하위 폴더의 `.gitkeep`은 구조 표시용이다. 점검 코드는 이 폴더 루트에 있으며, 기존 파이프라인 구현·SQL·데이터는 이곳에 복사하지 않았다. 실행 명령은 [작업별 명령 안내](../../docs/사용법-작업별-명령.md), 전체 단계와 공동 작업 경계는 [프로젝트 지도](../../docs/프로젝트-지도.md)를 참고한다.

## 사용자 점검 코드 실행

저장소 루트에서 합성 JSON을 점검한다. 첫 명령의 `e2` 참조 끊김은 예제에 의도된 진단 결과다. `--source-refs`는 JSON 근거의 문서·쪽 위치를, `--source-refs-csv`는 지정한 근거 CSV의 위치를 분류한다. 모두 입력을 수정하지 않으며 실제 원문이나 카드별 적용을 검증하지 않는다.

```bash
UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m lee_file_pipeline.evidence_audit src/lee_file_pipeline/examples_합성예제/synthetic_graph.json
UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m lee_file_pipeline.evidence_audit --source-refs src/lee_file_pipeline/examples_합성예제/synthetic_graph.json
UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m lee_file_pipeline.evidence_audit --source-refs-csv /tmp/합성결과/fp_evidence.csv
```

CLI 판정은 `ok`/종료 코드 `0`(이 검사 범위에서 문제 없음), `findings`/`1`(끊긴·중복·불명확한 관계 근거 또는 별도 보존된 자기 연결 근거), `incomplete`/`2`(관계 ID가 없어 판정 불가)다. JSON 입력 오류도 종료 코드 `2`이며 표준 오류에 표시한다. 이 합성 예제의 첫 명령은 `dangling_edge_ids: ["e2"]`와 `findings`/`1`, 두 번째는 위치가 없는 근거 때문에 `incomplete`/`2`가 정상이다. CSV는 위치가 모두 유효하면 `0`, 미확인·입력 오류는 `2`다.

아래는 **재현용 선택 명령**이며 과거 실행의 명령행 원문이라는 뜻은 아니다. 기존 추출 CLI 도움말과 사용자 폴더 전체 테스트의 과거 결과는 [STATUS의 역사 절](STATUS.md#이전-로컬-검증-기록)에 구분해 적었다.

```bash
UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m payment_card.file_pipeline.extraction.cli --help
UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src:src/card_benefit FP_CHAT_ENV_FILE=/tmp/lee-no-env uv run --locked --no-sync python -m pytest -q src/card_benefit/payment_card/tests/test_file_pipeline*.py
UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m pytest -q src/lee_file_pipeline/tests_테스트/test_evidence_audit.py
UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src:src/card_benefit FP_CHAT_ENV_FILE=/tmp/lee-no-env uv run --locked --no-sync python -m pytest -q src/lee_file_pipeline/tests_테스트/*.py
```
