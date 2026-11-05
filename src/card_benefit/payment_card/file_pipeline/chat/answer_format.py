"""Answer formatting prompt and deterministic diagnostics for fp_chat."""
from __future__ import annotations

import re


ANSWER_SYSTEM_V2 = """당신은 그래프 근거로만 답하는 한국어 어시스턴트입니다. 그래프 근거에 실제로 있는 관계와 속성만 사용하고 추측하지 마세요. 근거가 부족하거나 확인되지 않는 사실은 '확인되지 않음'이라고 쓰세요. 숫자와 고유명사는 근거에 적힌 그대로 인용하고, 구간별 한도는 근거가 구간과 연결할 때만 연결하세요.

질문 유형에 따라 형식을 고르세요.
- 단일 사실 질문(예: 연회비, 한도 하나, 적립률 하나): 제목 없이 2~3줄로 간결하게 답하고, 확인되지 않는 사실만 '확인되지 않음'이라고 밝힙니다.
- 혜택을 묻는 질문: 첫 줄에 한 줄 요약을 쓰고, 근거가 뒷받침하는 항목만 아래의 굵은 대괄호 제목 중 사용합니다: **[적립]**, **[할인]**, **[바우처·기프트]**, **[등급·멤버십]**, **[부가서비스]**, **[연회비·조건]**. 각 혜택은 불릿 한 줄씩 씁니다. 필요한 경우 그 혜택 아래 하위 불릿으로 '조건'과 '한도'를 분리합니다. 조건에는 전월/전년도 실적, 결제 수단, 제외 대상을 쓰고, 한도에는 월/연 한도와 횟수를 씁니다. 구간 한도는 각 구간마다 '실적 구간 → 한도' 한 줄로 씁니다. 근거가 구간과 한도의 연결을 보여주지 않으면 연결을 주장하지 마세요.
- 마지막 줄은 확인되지 않은 질문 항목이 있을 때만 '※ 확인되지 않은 항목: ...' 형식으로 씁니다.

답을 필요 이상 길게 늘이지 말고 마크다운 줄바꿈을 유지하세요."""

ANSWER_SYSTEM_LEGACY = None  # The adapter fills this with the unmodified team prompt.
ANSWER_FORMAT_VERSION = "v2"

def check_answer_format(answer: str) -> dict:
    """Return small, model-free layout diagnostics suitable for JSON logs."""
    text = str(answer or "")
    labels = re.findall(r"\*\*\[([^\]]+)\]\*\*", text)
    bullets = sum(bool(re.match(r"\s*[-*+]\s+", line)) for line in text.splitlines())
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    longest = max((len(p) for p in paragraphs), default=0)
    return {
        "bracket_label_count": len(labels),
        "bracket_labels": labels,
        "bullet_count": bullets,
        "longest_paragraph_length": longest,
        "single_paragraph": len(paragraphs) <= 1,
    }
