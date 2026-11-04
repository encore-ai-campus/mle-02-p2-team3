# 작업 범위

- 상위 폴더나 다른 경로가 필요하면 임의로 접근하지 말고, 필요한 경로와 이유를 사용자에게 먼저 요청한다.
- `.env`, 접속 문자열, API 키는 열거나 출력하지 않는다.


## 점검용 노트북

- `file_pipeline/extraction` 또는 `file_pipeline/graph`에 새 `.py` 모듈을 만들거나 공개 함수를 변경하면 `file_pipeline/notebooks/`에 입력 예시 → 모듈 호출 → 결과 표시를 포함한 점검 셀을 추가한다.
- 같은 변경 때 `file_pipeline/notebooks/모듈-점검-목록.md`에 모듈명, 노트북 파일, 셀 제목을 기록한다.
- 노트북은 출력이 비어 있는 상태로 커밋하며, PDF 원문 텍스트, `.env`, 접속 정보는 포함하지 않는다.
- 코드의 경로는 하드코딩하지 않고 노트북 상단 변수로 둔다.

## Codex 작업 공통 규칙

- 지시문에 적힌 파일 목록과 작업 범위 밖의 파일은 수정하지 않는다. 지시에서 '수정 금지'로 지정한 파일(다른 세션이나 다른 작업이 쓰는 파일 포함)은 읽기만 한다.
- git 쓰기(add/commit/push/reset/checkout 등)와 PR 작성은 하지 않는다. 커밋·푸시는 사용자가 한다.
- 지시가 없으면 공유 문서(작업이력 인덱스, 프로젝트 지도, 폴더 README, 모듈 점검 목록)를 고치지 않는다. 필요하면 보고에 '이력에 쓸 사실'로 남긴다. 이력 파일은 지시가 있을 때만 쓴다.
- 문서·테스트·보고에 PDF 원문, 청크 본문, 인용문 본문을 넣지 않는다. 건수, chunk_id, 필드 경로, enum 값 이름만 쓴다. 테스트 데이터는 합성한다.
- ~/pilot_work 쓰기는 샌드박스에서 막힐 수 있다. 막히면 우회하지 말고 실행할 명령만 보고한다. 실행 중인 결과 폴더(지시에서 지정)는 읽지도 쓰지도 않는다.
- 파이썬은 `uv run --locked --no-sync`로 실행한다(`python` 명령이 없을 수 있다. UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src:src/card_benefit). 표준 테스트 명령: `UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src:src/card_benefit uv run --locked --no-sync python -m pytest -q src/card_benefit/payment_card/tests/test_file_pipeline_extraction*.py src/card_benefit/payment_card/tests/test_file_pipeline_graph*.py src/card_benefit/payment_card/tests/test_file_pipeline_notebook_coverage.py` (끝에 `.`를 붙이지 않는다: 저장소 전체를 수집해 무관한 챗봇 테스트가 실패한다).
- 보고는 사실만: 변경·생성한 파일 목록, 테스트 마지막 줄 원문, 직접 실행한 확인(grep 등) 결과 원문, 막힌 점. 확인하지 않은 것은 '추정'이나 '미확인'으로 쓴다. 완료했다고 말하려면 근거 명령 결과를 붙인다.
- 완료 보고 전에 새로 만든 파일이 실제로 존재하는지, 인덱스 같은 문서 수정이 실제로 반영됐는지 grep 이나 ls 로 확인하고 그 결과를 보고한다.
- 이 절의 규칙을 고칠 때는 이 파일만 고친다(다른 곳에 복사하지 않는다).
