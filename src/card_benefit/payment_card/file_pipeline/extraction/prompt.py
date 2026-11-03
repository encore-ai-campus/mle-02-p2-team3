"""청크 한 개를 온톨로지 v1 형식으로 추출하도록 요청하는 프롬프트."""

from __future__ import annotations

from typing import Literal, get_args, get_origin

from .schema import ALLOWED_RELATIONS, Benefit, Condition, Limit, Relation, Target


def _literal_values(annotation: object) -> list[str]:
    """타입 표기 안에 들어 있는 Literal 값을 모은다(선택 타입 포함)."""
    if get_origin(annotation) is Literal:
        return [str(value) for value in get_args(annotation)]
    values: list[str] = []
    for argument in get_args(annotation):
        values.extend(_literal_values(argument))
    return values


def _model_fields(model: type) -> str:
    lines = []
    for name, field in model.model_fields.items():
        requirement = "필수" if field.is_required() else "선택"
        enums = _literal_values(field.annotation)
        suffix = f"; 허용값: {', '.join(enums)}" if enums else ""
        lines.append(f"- {name}: {requirement}{suffix}")
    return "\n".join(lines)


def build_prompt(chunk: dict) -> str:
    """LLM에 전달할 JSON 출력 지시와 청크 원문을 만든다."""
    schema_fields = "\n\n".join((
        f"Benefit:\n{_model_fields(Benefit)}",
        f"Condition:\n{_model_fields(Condition)}",
        f"Limit:\n{_model_fields(Limit)}",
        f"Target:\n{_model_fields(Target)}",
        f"Relation:\n{_model_fields(Relation)}",
    ))
    relation_pairs = ", ".join(f"{name}: {source}→{target}"
                                for name, (source, target) in ALLOWED_RELATIONS.items())
    return f"""카드 혜택 청크에서 혜택, 조건, 한도, 대상, 관계를 추출하세요.
원문에 없는 내용을 추측하지 마세요. 모든 엔티티와 관계의 evidence에는 원문 그대로의 인용문을 하나 이상 넣으세요.
id는 영문자, 숫자, 밑줄(_), 하이픈(-)만 사용하고 1~64자로 만드세요. 전체 엔티티에서 id는 서로 달라야 합니다.
관계는 아래 허용 쌍만 사용하고, 자기 자신을 가리키거나 존재하지 않는 id를 참조하지 마세요.
{relation_pairs}
출력은 설명이나 마크다운 없이 JSON 객체만 반환하세요. 위치 숫자는 출력하지 마세요.
최상위 키는 schema_ver(값 ONTOLOGY_V1), benefits, conditions, limits, targets, relations입니다.

필드와 허용값 (필수/선택 필드는 스키마 기준):
{schema_fields}

추출 규칙:
- 혜택 문장에 직접 붙은 한도는 그 혜택에 연결하세요.
- 여러 혜택이 함께 쓰는 통합 한도는 Limit 하나를 만들어 여러 혜택이 같은 Limit을 참조하게 하고 shared=true로 표시하세요.
- 품목 택1은 Benefit 하나에 여러 Target을 연결하고 선택 표현을 원문에 남기세요.
- 할인/적립 방식 택1은 Benefit.method=None으로 두고 선택 조건을 Condition에 기록하세요.
- 전월 실적 제외 목록은 목록 전체 문구를 보존한 Condition(kind=EXCLUDE) 하나로 기록하세요.
- 혜택에서 제외되는 가맹점/업종이 명확한 경우에만 EXCLUDES를 사용하세요.
- 표에서 분리된 한도 값/라벨 등 확정되지 않은 연결은 규칙으로 추정하지 마세요. 원문에 있는 그대로만 기록하고, 확실하지 않으면 연결하지 마세요.

청크 메타데이터:
page_no={chunk['page_no']}
start_pos={chunk['start_pos']}
청크 원문:
{chunk['text']}"""
