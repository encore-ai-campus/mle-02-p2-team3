# extraction/review/

사람이 원문과 대조하는 검토 자료를 준비하고 판정을 집계하는 도구다. 실행은 `payment_card.file_pipeline.extraction.review.<모듈>` 로 한다. 저장소 루트 계산은 `Path(__file__).resolve().parents[6]` 이다.

| 파일 | 역할 |
|---|---|
| `__init__.py` | `review`를 패키지로 표시한다. |
| `empty_review.py` | 반복 실행에서 빈 청크의 사람 검토 자료를 준비하고 집계한다. |
