# file_pipeline — 파일 기반 처리 방식 (담당: 이현근)

이 문서는 이 폴더의 **지도**다. 파일을 추가하거나 옮기면 같은 커밋에서 아래 3절 표와 4절 그림을 고친다.
(지도와 코드가 다르면 지도를 고친다.) 마지막 갱신: 2026-11-03

## 1. 한 줄 목적

카드 상품설명서 PDF를 Python으로 직접 처리해 분류 → 원문 추적 → 청킹 → LLM 추출 → 검증까지 수행한다.
`db_pipeline/`(김병주)과 같은 원천 문서를 다른 방식으로 처리하는 **독립 구현**이며, 서로의 결과를 입력으로 쓰지 않는다.

## 2. 전체 흐름

프로젝트 전체 11단계 중 이 폴더가 맡는 1~7단계다. 8~11단계(비교, 정규화, 지식그래프, 챗봇)와 상대 담당은 [프로젝트 지도](../../../../docs/프로젝트-지도.md)에 있다.
색: 초록 = 완료, 회색 = 예정.

```mermaid
flowchart LR
    A[1 수집<br/>src/data/*_all] --> B[2 분류·인덱스<br/>doc_index]
    B --> C[3 원문 추적<br/>traceability]
    C --> D[4 청킹<br/>chunking]
    D --> O[5 추출 스키마<br/>공통 계약]
    O --> E[6 LLM 추출<br/>실행기 작성]
    E --> F[7 검증 → 결과 A<br/>예정]
    classDef done fill:#cfe8cf,stroke:#4a8
    classDef doing fill:#fff1b8,stroke:#c90
    classDef todo fill:#eee,stroke:#999
    class A,B,C,D,E done
    class O doing
    class F todo
```

| 단계 | 입력 → 출력 | 상태 |
|---|---|---|
| 1 수집 | 카드사 사이트 → `src/data/{hana,woori}_all/` PDF와 manifest | 완료 (신용 중심, 체크는 하나만) |
| 2 분류·인덱스 | manifest → `src/card_benefit/data/index/{issuer}/documents.csv`, `product_docs.csv` | 완료 |
| 3 원문 추적 | 대표 PDF → 쪽별 원문과 청크 위치 JSON | 완료 (배치 포함) |
| 4 청킹 | 쪽 원문 → 청크(쪽 번호와 글자 위치 포함) | 완료 (`chunking/`) |
| 5 추출 스키마 | 온톨로지 v1(초안)과 인용문 위치 변환. `extraction/` | 초안 (file_pipeline 단독, 2026-11-03). 공통 계약은 8단계 비교 때 맞춤. 문서: `docs/작업이력/온톨로지-v1.md` |
| 6 LLM 추출 | 청크 → 혜택·조건·한도·관계와 원문 근거 | 실행기·이어하기 배치·표본 선정·크기 추정·지연 OpenAI 어댑터·드라이런/재집계 CLI 구현. 노트북 20개 시범 hard 실패 없는 결과 13개. 데스크탑 별도 15개 표본은 추출 성공 10, 빈 추출 2, 호출 실패 3. 7단계 검증 준비 부분 완료 |
| 7 검증 | 추출 결과 → 공통 형식 결과 A | 예정 |

## 3. 폴더 구성

```
file_pipeline/
├── README.md                이 문서
├── __init__.py
├── traceability.py          3단계: PDF 1개 → 쪽별 원문 + 청크 위치 JSON
├── chunking/                4단계: 쪽 원문을 청크로 자름
│   ├── split.py             쪽 원문 + 제목 위치 → 자를 조각 (PDF를 열지 않는 순수 함수)
│   ├── headings.py          글자 크기로 제목 줄을 찾아 쪽 원문 안의 위치로 변환, 표 안 제목은 제외
│   ├── build.py             쪽 → 청크 변환과 "이어 붙이면 원문과 같은가" 검증
│   └── cli.py               카드사 1곳의 청크 JSON 생성 (실행 진입점)
├── graph/                   지식그래프 CSV 변환·적재 및 논리 설계
│   ├── README.md            엔티티·근거 규칙·CSV 적재 계약
│   ├── schema.sql           public pf_ 테이블 및 관계 검사 초안
│   ├── export.py            추출 결과와 인덱스 → 검증된 pf_ CSV
│   └── load.py              기본 드라이런, 명시적 실행 옵션의 CSV 적재기
├── extraction/              5~6단계: 추출 스키마, 청크 실행기와 시범 준비 도구
│   ├── schema.py            온톨로지 v1 데이터 구조 (위치 숫자는 받지 않음)
│   ├── evidence.py          인용문 → 쪽 원문 위치 변환
│   ├── prompt.py            청크 1개용 프롬프트 (필드·허용값은 schema.py에서 읽음)
│   ├── runner.py            프롬프트 → 응답 파싱 → 스키마 검증 → 인용문 위치 부여, 실패는 구조화해 기록
│   ├── batch.py             청크 JSON 순회, 청크별 결과·문서 요약 저장 (예외 격리, 이어하기). 출력은 저장소 밖
│   ├── parallel.py          청크 동시 실행(최대 16), 지수 재시도와 진행 숫자 출력
│   ├── verify.py            저장 결과의 숫자·관계 연결·인용 위치 신호 점검 (판정 아님)
│   ├── pilot_run.py         선택·추정·실행·요약·검증·그래프 내보내기 흐름 묶음
│   ├── diagnose.py          빈 추출 결과를 제목·길이·키워드 수로 분류 (원문은 출력하지 않음)
│   ├── review_sheet.py      추출 성공 청크 N개를 사람이 원문과 대조하는 마크다운 대조표로 만듦 (원문 포함, 저장소 밖에만 저장)
│   ├── pilot.py             OCR 제외 텍스트 PDF에서 길이·문서·표·규칙 신호를 고려해 결정적 표본 선정, 프롬프트 크기 추정
│   ├── llm_adapter.py       LangChain OpenAI 호출 어댑터. SDK 지연 import, 키 환경변수 이름 인자
│   └── cli.py               select / estimate / summarize / run / verify / pilot-run 진입점
├── doc_index/               2단계(+3단계 일괄 실행): 분류·인덱스
│   ├── core.py              인덱스 만드는 핵심 규칙 (대표 선정, 공유 문서, 연결 표)
│   ├── measure.py           PDF 1개의 해시·쪽수·글자 수 측정
│   ├── schema.py            열 이름과 허용 값
│   ├── cli.py               카드사 1곳의 인덱스 생성 (실행 진입점)
│   ├── batch.py             인덱스의 대표 문서를 traceability로 일괄 변환
│   ├── tables.py            표 보조본 추출 (아직 어디에서도 부르지 않음)
│   └── adapters/            카드사별 원본 manifest → 공통 항목 변환 (hana.py, woori.py)
├── notebooks/               눈으로 확인하는 보조용. 로직은 두지 않는다. 커밋 전 출력 삭제
│   ├── doc_index_check.ipynb    인덱스 결과 점검
│   ├── chunking_explore.ipynb   청킹 기준 탐색
│   └── data_modify.ipynb        PDF 1개의 페이지 이미지와 추출 텍스트를 보는 기존 노트북
├── pilot_hana_15299/        하나 1건으로 원문 추적을 시험한 기록 (참고용)
│   ├── 08_파일럿_결과.md  08_표본대조_결과.md  09_마감.md  check_sheet.md
│   └── traceability.json
```

## 4. 모듈 호출 관계

화살표는 "가져다 쓴다"이다. `tables.py`는 아직 연결되지 않았다.

```mermaid
flowchart TD
    CLI[doc_index/cli.py] --> AD[adapters/hana.py, woori.py]
    CLI --> CORE[core.py]
    CLI --> MEA[measure.py]
    CLI --> SCH[schema.py]
    CORE --> SCH
    BATCH[doc_index/batch.py] --> TR[traceability.py]
    CK[chunking/cli.py] --> BATCH
    CK --> BLD[chunking/build.py]
    CK --> HD[chunking/headings.py]
    BLD --> SPL[chunking/split.py]
    TR --> DR[common/document_reader]
    TAB[tables.py]:::loose
    classDef loose fill:#eee,stroke:#999,stroke-dasharray: 4
```

`core.py` 안에서 일어나는 일의 순서는 `docs/작업이력/core-단순화-계획.md`의 흐름도에 있다.

## 5. 실행 방법

저장소 루트에서 실행한다. PDF 라이브러리가 준비된 uv 환경이 필요하다.

```bash
# 2단계: 카드사 1곳의 인덱스 만들기
PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m payment_card.file_pipeline.doc_index.cli --issuer woori --overwrite

# 3단계: 대표 문서를 쪽별 원문 JSON으로 변환 (출력 폴더는 직접 지정)
PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m payment_card.file_pipeline.doc_index.batch --issuer woori --output-dir <저장 폴더>

# 4단계: 3단계 JSON을 청크 JSON으로 (입력은 3단계 출력 폴더, 출력 폴더는 직접 지정)
PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m payment_card.file_pipeline.chunking.cli --issuer woori --trace-dir <3단계 출력 폴더> --output-dir <저장 폴더>

# 6단계: 하나카드 청크 표본을 고르고 프롬프트 크기를 추정 (경로는 저장소 밖)
PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m payment_card.file_pipeline.extraction.cli select --index-csv src/card_benefit/data/index/hana/documents.csv --chunk-dir <하나 청크 폴더> --output <저장소 밖>/pilot.json --count 5
PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m payment_card.file_pipeline.extraction.cli estimate --chunk-dir <하나 청크 폴더> --chunk-ids <저장소 밖>/pilot.json

# 기존 결과 재집계 (LLM 호출 없이 기존 result.json만 읽음)
PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m payment_card.file_pipeline.extraction.cli summarize --chunk-dir <하나 청크 폴더> --output-dir <저장소 밖>/results --chunk-ids <저장소 밖>/pilot.json

# 기본 run은 드라이런. 실제 호출에는 --execute와 모델 이름이 필요하며 키는 OPENAI_API_KEY에서 읽음
PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m payment_card.file_pipeline.extraction.cli run --chunk-dir <하나 청크 폴더> --chunk-ids <저장소 밖>/pilot.json --output-dir <저장소 밖>/results --max-chunks 5

# 실제 호출 예시: 먼저 OPENAI_API_KEY를 셸 환경에 설정하고, 모델명을 정한 뒤 명시적으로 실행
PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m payment_card.file_pipeline.extraction.cli run --chunk-dir <하나 청크 폴더> --chunk-ids <저장소 밖>/pilot.json --output-dir <저장소 밖>/results --max-chunks 5 --workers 1 --retries 2 --max-estimated-tokens 200000 --model <모델명> --execute

# 저장 결과 자동 신호 점검 (원문이나 인용문은 출력하지 않음)
PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m payment_card.file_pipeline.extraction.cli verify --result-dir <저장소 밖>/results --chunk-dir <하나 청크 폴더> --output-dir <저장소 밖>/verification

# 한 명령으로 계획 출력. 실행 시에만 --execute 추가 (최대 추정 200000 토큰)
PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m payment_card.file_pipeline.extraction.cli pilot-run --index-csv src/card_benefit/data/index/hana/documents.csv --chunk-dir <하나 청크 폴더> --work-dir <저장소 밖>/pilot_run --count 5 --model <모델명> --workers 1

# 저장된 청크 결과만으로 요약 다시 만들기 (LLM 호출 없음)
PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m payment_card.file_pipeline.extraction.cli summarize --chunk-dir <하나 청크 폴더> --output-dir <저장소 밖>/results

# 빈 추출 결과 분류 (LLM 호출 없음, 결과에는 청크 원문을 저장하지 않음)
PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m payment_card.file_pipeline.extraction.cli diagnose-empty --chunk-dir <하나 청크 폴더> --results-dir <저장소 밖>/results --output-dir <저장소 밖>/diagnosis

# 테스트
PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m pytest -q src/card_benefit/payment_card/tests/
```

JSON에는 쪽 전체 원문이 들어간다. 로컬 임시 폴더에 저장하고 공유하거나 Git에 올리기 전에 내용을 확인한다.
시범 표본의 표/규칙 키워드 탐지는 거친 선정 신호다. `run`은 `--execute`가 없으면 네트워크를 호출하지 않으며 기본 최대 새 호출 수는 5다. 기본 예상 토큰 한도는 200000이며 초과 시 실행을 거부하고 `--allow-large`로 해제한다. `--workers`는 1~16 범위로 제한하고 호출 예외는 기본 2회 재시도한다. `summarize`는 기존 결과 폴더의 청크별 JSON만 다시 집계하고, 아직 결과가 없는 청크는 `missing_results`로 표시한다. 청크 폴더에 없는 요청 ID는 오류로 중단한다. 프롬프트 버전을 비교할 때는 결과 폴더를 구분해 각각 집계한다. `verify`는 원문 근거를 판정하지 않는 신호이며 숫자·단위 비교도 거친 검사다. `pilot-run` 계획 모드는 DB/LLM 호출 없이 선택과 추정만 수행한다.

## 6. 읽는 순서 (처음 보는 사람)

1. 이 README의 2절 흐름도
2. `docs/작업이력/2026-11-02-카드사-문서-인덱스.md` — 무엇을 왜 했는지
3. `doc_index/core.py` 맨 위 설명과 맨 아래 `build_index` — 인덱스가 만들어지는 순서
4. `notebooks/doc_index_check.ipynb` — 결과를 표로 보기
5. `traceability.py` — 원문 추적 JSON 구조
6. `chunking/split.py` — 쪽을 어디서 자르는지(35줄)

## 7. 결정 기록

| 날짜 | 결정 | 이유 |
|---|---|---|
| 2026-11-02 | 범위는 신용카드와 common. 체크카드는 2단계 | 우리 `debit/`이 비어 있고 하나 체크는 변환본만 있는 카드가 있음 |
| 2026-11-02 | 같은 해시는 한 문서, 대표 1개만 `canonical=Y` | 같은 내용이 경로만 달라 여러 벌 있음(우리 107그룹) |
| 2026-11-02 | 웹 변환본은 공식 PDF가 있으면 대표에서 제외 | 같은 카드가 두 번 추출되는 것을 막음 |
| 2026-11-02 | 표는 평문을 원문으로 두고 검사 통과한 것만 보조본 | 표 추출기가 병합 셀을 비우거나 글자를 쪼갬 |
| 2026-11-02 | 청킹은 쪽 4000자 이하는 쪽 단위, 초과는 글자 크기 제목 기준, 400자 미만은 앞에 붙임 | 193개 문서 814쪽으로 24가지 기준값 비교 |
| 2026-11-02 | 제목 줄이 감지된 표 안에 있으면 그 앞에서 자르지 않음 | 자를 위치 270곳 중 24곳(9%)이 표 안. 대가로 4000자 초과 청크가 21 → 29개 |
| 2026-11-02 | 제목 없는 긴 쪽(카드의정석2 7쪽 7,935자 등)은 쪼개지 않음 | 길이가 실제 문제인지 5단계에서 확인한 뒤 문단 규칙 추가 여부 결정 |
| 2026-11-02 | OCR 도구는 아직 설치하지 않음 | 대표 문서 기준 우리 44개, 하나 2개가 대상. 텍스트 PDF로 먼저 끝까지 시험 |
| 2026-11-02 | 사람이 PDF를 열어 확인한 결과는 `review_decisions.csv`에 기록(이름 일치, 혜택 내용이 그림인지) | 확인 결과를 코드가 아니라 파일에 남기고, 자동 판정과 사람 판정을 `decided_by`로 구분 |
| 2026-11-02 | 공유 문서는 RAG에서 청크 1개 + 상품 목록 | 같은 내용이 검색 결과에 여러 번 나오는 것을 막음 |

## 규칙

- `db_pipeline/`을 import하지 않는다. 공통 모델·SQL은 `payment_card/` 최상위 것을 쓰고 복사하지 않는다.
- 새 Python 폴더를 만들면 `__init__.py`도 함께 만든다. 테스트는 `payment_card/tests/test_*.py`에 둔다.
- 원천·샘플 문서는 `src/card_benefit/data/`에 둔다. `src/data/*_all/`은 `.gitignore` 대상이다.
- 코드를 쓰기 전에 쉬운 말로 설명하고 흐름도를 보여 준 뒤 승인받는다. 승인 전에는 커밋하지 않는다.
- 상세: `src/card_benefit/docs/development_roles.md`
