"""온톨로지 v1의 추출 결과 구조와 유효성 규칙.

LLM이 반환할 데이터 모양을 Pydantic 모델로 정의한다. 원문 인용문은 필수지만 페이지·문자 위치는
이 스키마의 책임이 아니며, 별도 근거 처리 단계에서 추출 결과와 원문을 연결한다.
엔티티는 혜택(Benefit), 조건(Condition), 한도(Limit), 대상(Target)이고,
관계(Relation)는 엔티티 id를 잇는다. 허용하는 관계의 출발·도착 종류는 ALLOWED_RELATIONS가 정한다.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# 추출 JSON의 버전. 필드 구조가 호환되지 않게 바뀌면 새 버전으로 구분한다.
SCHEMA_VER = "ONTOLOGY_V1"

# 엔티티와 관계가 함께 참조하는 ID 형식: 1~64자, 영문자·숫자·밑줄·하이픈.
Id = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_\-]+$")]

# 모델이 받을 수 있는 분류값. Literal로 제한해 임의 문자열 입력을 막는다.
ConditionKind = Literal["SPEND_REQ", "EXCLUDE", "USAGE", "PAYMENT", "MERCHANT", "OTHER"]
LimitPeriod = Literal["TXN", "DAY", "MONTH", "YEAR", "UNKNOWN"]
TargetKind = Literal["MERCHANT", "INDUSTRY", "CHANNEL", "SERVICE", "OTHER"]
RelationType = Literal["HAS_CONDITION", "HAS_LIMIT", "APPLIES_TO", "EXCLUDES", "MUTUALLY_EXCLUSIVE"]

# 관계 유형마다 허용하는 (출발, 도착) 엔티티 종류. 모델 검증에서 실제 ID의 종류와 대조한다.
ALLOWED_RELATIONS: dict[str, tuple[str, str]] = {
    "HAS_CONDITION": ("Benefit", "Condition"),
    "HAS_LIMIT": ("Benefit", "Limit"),
    "APPLIES_TO": ("Benefit", "Target"),
    "EXCLUDES": ("Benefit", "Target"),
    "MUTUALLY_EXCLUSIVE": ("Benefit", "Benefit"),   # "장기할부 청구할인과 중복 제공 안됨"
}


class _Strict(BaseModel):
    # 명세에 없는 필드를 거부한다. 페이지·문자 위치는 별도 근거 처리 단계에서 붙인다.
    model_config = ConfigDict(extra="forbid")


class Quote(_Strict):
    # 원문에서 그대로 가져온 근거 문구. 빈 인용문은 허용하지 않는다.
    text: str = Field(min_length=1)


class _Entity(_Strict):
    # 모든 엔티티는 고유 ID와 하나 이상의 원문 근거를 가진다.
    id: Id
    evidence: list[Quote] = Field(min_length=1)


# 혜택 방식: 할인, 청구 시 현금성 적립, 포인트 적립.
BenefitMethod = Literal["DISCOUNT", "CASHBACK", "POINT"]


class Benefit(_Entity):
    # 혜택의 이름과 방식, 혜택 자체의 비율·금액. 값은 원문 표현을 보존한다.
    name: str = Field(min_length=1)
    method: BenefitMethod | None = None   # 할인/적립 구분. 원문에 "할인 또는 적립 택1"이면 None으로 두고 Condition에 적는다
    rate: str | None = None      # 원문 표기 그대로 (예: "5%", "리터당 50원", "0.5%")
    amount: str | None = None    # 할인·적립 혜택 금액 자체의 원문 표기. 실적·결제 기준과 반복 한도는 제외


class Condition(_Entity):
    # 혜택 적용에 필요한 조건. min_amount는 실적·결제 기준 금액을 원 단위 정수로 담는다.
    text: str = Field(min_length=1)
    kind: ConditionKind
    min_amount: int | None = Field(default=None, ge=0)   # 실적·결제 기준 금액(원). "30만원 이상" -> 300000


class Limit(_Entity):
    # 혜택 한도. amount는 원문에 숫자로 제시된 금액 또는 횟수이며 period와 함께 해석한다.
    text: str = Field(min_length=1)    # 원문 표기 그대로 (예: "월 할인한도 5천원")
    period: LimitPeriod
    amount: int | None = Field(default=None, ge=0)   # 금액·횟수. 원문에 숫자가 있을 때만
    unlimited: bool = False   # "할인한도 제한 없음"
    shared: bool = False      # "통합 월 2회"처럼 여러 혜택·회원이 나눠 쓰는 한도

    @model_validator(mode="after")
    def check_amount_or_unlimited(self) -> "Limit":
        if self.unlimited and self.amount is not None:
            raise ValueError("unlimited 한도는 amount를 가질 수 없습니다")
        return self


class Target(_Entity):
    # 혜택이 적용되거나 제외되는 가맹점·업종·채널·서비스 등의 대상.
    text: str = Field(min_length=1)
    kind: TargetKind


class Relation(_Strict):
    # source와 target은 Extraction 안에 정의된 엔티티 ID를 가리켜야 한다.
    source: Id
    target: Id
    type: RelationType
    evidence: list[Quote] = Field(min_length=1)


class Extraction(_Strict):
    # 온톨로지 버전과 네 종류의 엔티티, 엔티티 간 관계를 담는 최상위 결과 모델.
    schema_ver: Literal["ONTOLOGY_V1"] = SCHEMA_VER
    # 항목이 없을 수 있으므로 빈 목록을 기본값으로 둔다.
    benefits: list[Benefit] = Field(default_factory=list)
    conditions: list[Condition] = Field(default_factory=list)
    limits: list[Limit] = Field(default_factory=list)
    targets: list[Target] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_ids_and_relations(self) -> "Extraction":
        """ID 중복·미정의 참조·자기 참조와 관계별 엔티티 종류를 확인한다."""
        kinds: dict[str, str] = {}
        for kind, items in (("Benefit", self.benefits), ("Condition", self.conditions),
                            ("Limit", self.limits), ("Target", self.targets)):
            for item in items:
                if item.id in kinds:
                    raise ValueError(f"id가 겹칩니다: {item.id}")
                kinds[item.id] = kind
        for rel in self.relations:
            if rel.source not in kinds or rel.target not in kinds:
                raise ValueError(f"관계가 없는 id를 가리킵니다: {rel.source} -> {rel.target}")
            if rel.source == rel.target:
                raise ValueError(f"관계가 자기 자신을 가리킵니다: {rel.source}")
            want_from, want_to = ALLOWED_RELATIONS[rel.type]
            if kinds[rel.source] != want_from or kinds[rel.target] != want_to:
                raise ValueError(f"{rel.type}은 {want_from}->{want_to}만 허용합니다: {rel.source} -> {rel.target}")
        return self


def all_quotes(extraction: Extraction) -> list[str]:
    """모든 엔티티와 관계의 인용문을 모은다. 후속 근거 위치 확인에 사용한다."""
    quotes: list[str] = []
    for group in (extraction.benefits, extraction.conditions, extraction.limits, extraction.targets, extraction.relations):
        for item in group:
            quotes.extend(q.text for q in item.evidence)
    return quotes
