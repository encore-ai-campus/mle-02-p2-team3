# file_pipeline — 파일 기반 처리 방식 (담당: 이현근)

카드 상품설명서 원본 파일을 Python으로 직접 처리해 파싱·추출·검증까지 수행하는 방식입니다.
`db_pipeline/`(김병주)과 **같은 원천 문서를 다른 방식으로 처리하는 독립 구현**이며, 서로의 결과를 입력으로 쓰지 않습니다.

현재 구현은 원문 추적성 파일럿입니다. `traceability.py`가 PDF를 읽어 해시, 페이지별 원문·추출 상태, 페이지 단위 청크를 JSON으로 저장합니다.
청크 위치는 페이지마다 1부터 세며 끝 글자도 포함합니다. 빈 페이지는 기록하지만 청크는 만들지 않습니다.
DB 접속과 혜택·조건 추출은 하지 않습니다.

명령줄에서 실행하려면 저장소 루트에서 다음처럼 입력합니다. PDF 라이브러리가 준비된 uv 환경이 필요합니다.

```bash
PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m payment_card.file_pipeline.traceability \
  --pdf /tmp/card-pilot/hana_15299.pdf \
  --output /tmp/card-pilot/traceability.json \
  --expected-sha256 4a8995350682476505589ca35cfaec8de67f3cde0dcc0e144cdc59c773afbc84 \
  --expected-page-count 2
```

JSON에는 페이지 전체 원문이 들어갑니다. 결과는 로컬 임시 폴더에 저장하고 공유하거나 Git에 올리기 전에 내용을 확인하세요. 기존 결과 파일은 기본적으로 덮어쓰지 않습니다.

`data_modify.ipynb`는 ZIP에서 대상 PDF 한 개를 임시 폴더에 꺼내고 페이지 이미지와 추출 텍스트를 확인하는 보조 노트북입니다. 처리 로직은 `.py` 파일에만 두었습니다.

향후 개발 예정:
- PDF 표 구조 인식 및 전처리
- 텍스트·표 데이터 전처리, 정규식 기반 정보 추출
- Python에서 LLM API 호출 → 엔티티·관계·카드 혜택 조건 추출
- Python 기반 결과 검증 → 공통 형식의 구조화 결과(**결과 A**)
- 참고: `graph-rag` 저장소의 `3_LLM식추출` 학습자료

규칙:
- `db_pipeline/` 을 import하지 않습니다. 공통 모델·SQL은 `payment_card/` 최상위 것을 사용하고 복사하지 않습니다.
- 첫 Python 모듈을 추가할 때 `__init__.py` 도 함께 만듭니다. 테스트는 `payment_card/tests/test_*.py` 에 둡니다.
- 원천·샘플 문서는 `src/card_benefit/data/` 에 둡니다.

상세: `src/card_benefit/docs/development_roles.md`
