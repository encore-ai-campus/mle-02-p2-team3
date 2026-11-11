"""문서 인덱스 CSV의 열 이름과 분류·판정에 쓰는 공통 값.

열 목록은 CSV 헤더와 행의 출력 순서를 정한다. 아래 분류 값은 입력 항목을
표준화하고, 출처 순위와 OCR 기준은 대표 문서 및 검토 대상을 판정할 때 쓴다.
"""

# documents.csv의 열 순서. 한 행은 PDF 파일 하나를 나타낸다.
DOCUMENT_COLUMNS = [
    # 카드사, 문서 식별자(sha256 앞 16자리), 전체 파일 해시, 원본 파일 경로
    "issuer", "doc_id", "sha256", "file_path", "card_type", "doc_role",
    # 대표 문서 여부, 대표로 연결된 중복 문서 경로
    "canonical", "duplicate_of", "pages", "text_chars", "ocr_needed",
    # PDF 출처 URL, 출처 분류, 게시일, 검토 필요 여부와 사유
    "source_url", "origin", "board_date", "needs_review", "review_reason",
]
# product_docs.csv의 열 순서. 한 행은 상품과 문서 사이의 연결 하나를 나타낸다.
PRODUCT_DOC_COLUMNS = [
    # 카드사, 상품명, 원본 목록에서 제공된 상품 ID들(JSON 문자열), 카드 구분
    "issuer", "product_name", "product_ids", "card_type", "doc_id",
    # 연결 문서 경로와 관계 유형(예: 대표 설명서, 약관, 브랜드 안내)
    "file_path", "relation",
]

# 문서의 용도 분류. 어댑터가 항목에 지정하며, 미분류 문서는 검토 대상으로 표시된다.
DOC_ROLES = {"product_guide", "web_capture", "brand_service", "terms", "other", "unclassified"}
# 파일을 확보한 경로의 분류. ORIGIN_RANK에도 같은 값이 있어야 대표 선정에 사용할 수 있다.
ORIGINS = {"official_download", "official_url_inferred", "web_capture", "existing_unverified"}
# 같은 내용의 파일 중 대표를 고를 때 쓰는 출처 우선순위. 숫자가 작을수록 먼저 선택한다.
ORIGIN_RANK = {
    "official_download": 0,
    "official_url_inferred": 1,
    "web_capture": 2,
    "existing_unverified": 3,
}
# 쪽당 평균 추출 글자 수(chars / pages)가 이 값보다 작으면 OCR 필요 후보로 표시한다.
# 스캔 여부를 확정하는 값은 아니며, 사람이 확인할 문서를 찾기 위한 기준이다.
OCR_MIN_CHARS_PER_PAGE = 50
