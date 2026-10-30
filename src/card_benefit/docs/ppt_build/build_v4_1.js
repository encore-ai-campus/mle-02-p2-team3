// 카드 혜택 GraphRAG 발표 deck V4.1 생성기 (pptxgenjs) — build_v4.js 기반 수정본
// V4.1: 표지에 MCP 연결 동기 한 줄, 신한 사례→MCP 연결, 외부 AI 최종 답변 추적 범위 명시
// build_v2_base.js 의 팔레트·마스터·헬퍼를 그대로 쓰고, 슬라이드 구성은 v4_work_checkpoint.md §5 를 따른다.
// 사용: node build_v4.js <out.pptx> [notes_body.md]
const pptxgen = require("pptxgenjs");
const fs = require("fs");

const OUT = process.argv[2];
const NOTES_OUT = process.argv[3];
const F = "Malgun Gothic";
const MONO = "Courier New";

// palette
const INK = "0E1A2B", INK2 = "1F3350", TXT = "1A2433", MUTED = "5B6778", LINE = "D5DBE3", MIST = "F3F5F8";
const AMBER = "E8A33D", AMBER_D = "8F5208", AMBER_T = "FDF0DC";
const TEAL = "159A8C", TEAL_D = "0D6F64", TEAL_T = "E3F4F1";
const RED = "D9472B", RED_D = "A8311A", RED_T = "FBE6E2";
const VIO = "6A4FB0", VIO_T = "EFE9F8";
const SLATE = "3A4A60", SLATE_T = "E8ECF2";
const DARK_SUB = "A9B7C9";

const THEME = {
  name: "CardEngine",
  headFontFace: F,
  bodyFontFace: F,
  colors: {
    dk1: TXT, lt1: "FFFFFF", dk2: INK, lt2: MIST,
    accent1: AMBER, accent2: TEAL, accent3: RED, accent4: VIO, accent5: SLATE, accent6: INK2,
    hlink: TEAL_D, folHlink: VIO,
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.theme = { headFontFace: F, bodyFontFace: F };
pres.title = "AI 판단 근거를 검증하는 카드 혜택 GraphRAG 엔진 — 하나카드 상품설명서 기반";
pres.author = "mle-02-p2-team3";

const W = 13.333, L = 0.6, R = 12.733, CW = R - L;

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: "FFFFFF" },
  objects: [
    { placeholder: { options: { name: "kicker", type: "body", x: L, y: 0.36, w: 8.2, h: 0.32, fontFace: F, fontSize: 12, bold: true, color: AMBER_D, margin: 0, valign: "middle" }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: L, y: 0.72, w: CW, h: 0.95, fontFace: F, fontSize: 24, bold: true, color: INK, margin: 0, valign: "top", align: "left" }, text: "" } },
  ],
  slideNumber: { x: 12.33, y: 7.04, w: 0.4, h: 0.26, fontFace: F, fontSize: 10, color: "8A94A3", align: "right" },
});
pres.defineSlideMaster({
  title: "DARK",
  background: { color: INK },
  objects: [],
  slideNumber: { x: 12.33, y: 7.04, w: 0.4, h: 0.26, fontFace: F, fontSize: 10, color: "6F7F96", align: "right" },
});

// ---------- helpers ----------
function T(s, text, o) {
  s.addText(text, Object.assign({ isTextBox: true, fontFace: F, margin: 0, color: TXT, fontSize: 14, valign: "top" }, o));
}
function boxT(s, text, o) {
  const opt = Object.assign({ isTextBox: true, shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.08, fontFace: F, fontSize: 13, color: TXT, margin: 6, valign: "middle", align: "center", fill: { color: MIST }, line: { color: MIST, width: 0.75 } }, o);
  s.addText(text, opt);
}
function rect(s, o) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, Object.assign({ rectRadius: 0.1, fill: { color: MIST }, line: { color: MIST, width: 0.75 } }, o));
}
function arrow(s, x, y, w, h, color, o) {
  s.addShape(pres.shapes.LINE, Object.assign({ x, y, w, h, line: { color: color || "8A94A3", width: 1.5, endArrowType: "triangle" } }, o || {}));
}
function line(s, x, y, w, h, color, o) {
  s.addShape(pres.shapes.LINE, Object.assign({ x, y, w, h, line: { color: color || "8A94A3", width: 1.5 } }, o || {}));
}
const PILL = {
  "공식 확인": [TEAL_T, TEAL_D], "원문 확인": [TEAL_T, TEAL_D], "구현 완료": [TEAL_T, TEAL_D], "프로젝트 목적": [TEAL_T, TEAL_D],
  "시연 예정": [AMBER_T, AMBER_D], "검증 예정": [AMBER_T, AMBER_D], "가설 · 검증 예정": [AMBER_T, AMBER_D], "시연 예상 화면": [AMBER_T, AMBER_D],
  "설계안": [SLATE_T, SLATE], "팀 해석": [SLATE_T, SLATE], "팀 가설": [SLATE_T, SLATE], "목표": [SLATE_T, SLATE],
  "확장 제안": [VIO_T, VIO], "미실행": [RED_T, RED_D], "가상 시나리오": [RED_T, RED_D],
};
function pills(s, list) {
  let x = R;
  for (let i = list.length - 1; i >= 0; i--) {
    const t = list[i];
    const w = 0.34 + t.replace(/\s/g, "").length * 0.15;
    x -= w;
    const [bg, fg] = PILL[t];
    s.addText(t, { isTextBox: true, shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.15, x, y: 0.36, w, h: 0.32, fontFace: F, fontSize: 11, bold: true, color: fg, fill: { color: bg }, line: { color: bg }, align: "center", valign: "middle", margin: 0 });
    x -= 0.1;
  }
}
function footer(s, text) {
  T(s, text, { x: L, y: 7.0, w: 11.5, h: 0.32, fontSize: 10, color: "6B7686", valign: "middle" });
}
function content(kicker, title, section) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(kicker, { placeholder: "kicker" });
  s.addText(title, { placeholder: "title" });
  s._v4 = { kicker, title };
  return s;
}
function chip(s, text, x, y, w, h, bg, fg, o) {
  boxT(s, text, Object.assign({ x, y, w, h, fill: { color: bg }, line: { color: bg }, color: fg, fontSize: 12, bold: true, rectRadius: 0.06, margin: 3 }, o || {}));
}
const NODE = { card: [INK, "FFFFFF"], benefit: [TEAL, "FFFFFF"], cond: [AMBER, INK], item: [RED, "FFFFFF"], clause: [VIO, "FFFFFF"], grey: [SLATE_T, SLATE] };
function node(s, text, kind, x, y, w, h, o) {
  const [bg, fg] = NODE[kind];
  boxT(s, text, Object.assign({ x, y, w, h, fill: { color: bg }, line: { color: bg }, color: fg, fontSize: 12, bold: true, rectRadius: 0.12, margin: 3 }, o || {}));
}
const tblBorder = { type: "solid", pt: 0.75, color: LINE };
const edge = (s, t, x, y, w, o) => T(s, t, Object.assign({ x, y, w, h: 0.24, fontSize: 9, bold: true, color: SLATE, fontFace: MONO }, o || {}));

// 발표 노트: 슬라이드 addNotes 와 노트 문서(md)에 같은 대본을 쓴다
const NOTES = [];
function notes(s, label, meta, script) {
  s.addNotes(script);
  NOTES.push(Object.assign({ label, script }, meta));
}

// ===================== MAIN =====================
pres.addSection({ title: "도입" });

// ---- 1 hook ----
{
  const s = pres.addSlide({ masterName: "DARK", sectionTitle: "도입" });
  T(s, "하나카드 상품설명서 기반 GraphRAG  ·  AI 판단 근거 검증 엔진", { x: 0.7, y: 0.55, w: 9, h: 0.35, fontSize: 13, color: DARK_SUB });
  T(s, "AI가 고객에게 카드 혜택을\n잘못 안내했다면,", { x: 0.7, y: 1.35, w: 7.4, h: 1.5, fontSize: 34, bold: true, color: "FFFFFF", lineSpacingMultiple: 1.05 });
  T(s, "카드사는 그 이유를\n설명할 수 있을까요?", { x: 0.7, y: 2.95, w: 7.4, h: 1.4, fontSize: 30, bold: true, color: AMBER, lineSpacingMultiple: 1.05 });
  T(s, "그럴듯한 답과 정확한 답은 다릅니다.\n이 발표는 AI 판단에 쓰인 조건과 근거를 카드사가 확인하는 방법에 대한 제안입니다.", { x: 0.7, y: 4.65, w: 7.3, h: 0.9, fontSize: 15, color: "D5DEEA", lineSpacingMultiple: 1.15 });
  T(s, [
    { text: "고객이 외부 AI에게 물어도 같은 판단 근거가 나가야 합니다.", options: { color: DARK_SUB, breakLine: true } },
    { text: "→ 검증한 판단을 여러 AI에 연결하는 방법: 공통 엔진 + MCP (14쪽)", options: { color: AMBER, bold: true } },
  ], { x: 0.7, y: 5.75, w: 7.4, h: 0.62, fontSize: 13, lineSpacingMultiple: 1.15 });
  T(s, "mle-02-p2-team3  ·  2026.10  ·  2차 팀 프로젝트", { x: 0.7, y: 6.75, w: 6, h: 0.3, fontSize: 11, color: "7F8FA6" });

  const cx = 8.45, cw = 4.28;
  T(s, "고객 → AI   (가상 대화)", { x: cx, y: 1.2, w: cw, h: 0.28, fontSize: 11, color: "7F8FA6" });
  boxT(s, "ONE PICK STYLE로 지난달 상품권 8만원, 버스비 2만원 썼어요. 이번 달 대중교통 캐시백 받나요?", { x: cx, y: 1.52, w: cw, h: 1.05, fill: { color: "FFFFFF" }, line: { color: "FFFFFF" }, color: INK, fontSize: 13, align: "left", margin: 9, rectRadius: 0.14 });
  boxT(s, "네, 지난달 10만원을 채우셨으니 대중교통 5% 캐시백을 받으실 수 있어요.", { x: cx, y: 2.7, w: cw, h: 0.85, fill: { color: INK2 }, line: { color: INK2 }, color: "FFFFFF", fontSize: 13, align: "left", margin: 9, rectRadius: 0.14 });
  boxT(s, [
    { text: "원문 기준: 상품권은 실적 제외", options: { bold: true, breakLine: true } },
    { text: "→ 인정 실적 최대 2만원 → 원칙상 미적용", options: { bold: true, breakLine: true } },
    { text: "예외: 최초 사용 등록일~다음 달 말일은 실적 무관", options: { fontSize: 11 } },
  ], { x: cx, y: 3.68, w: cw, h: 1.1, fill: { color: RED }, line: { color: RED }, color: "FFFFFF", fontSize: 12, align: "left", margin: 9, rectRadius: 0.1 });
  T(s, "담당자가 확인해야 할 것", { x: cx, y: 4.95, w: cw, h: 0.28, fontSize: 11, color: "7F8FA6" });
  ["AI는 어떤 조건을 적용했나?", "상품권은 실적에 들어가나?", "근거 조항은 어디인가?"].forEach((q, i) => boxT(s, q, { x: cx, y: 5.27 + i * 0.46, w: cw, h: 0.38, fill: { color: INK }, line: { color: AMBER, width: 1 }, color: AMBER, fontSize: 12, bold: true, align: "left", margin: 8, rectRadius: 0.1 }));
  T(s, "가상 대화 · 정답 근거: ONE PICK STYLE 상품설명서(15650_20260429) 1쪽", { x: cx, y: 6.72, w: cw, h: 0.3, fontSize: 10, color: "7F8FA6" });
  notes(s, "표지 — AI가 잘못 안내했다면", {
    purpose: "청중을 '담당자 입장'에 세운다. 그럴듯한 오답 하나로 발표 전체의 질문(판단 근거를 확인할 수 있는가)을 던진다.",
    status: "가상 시나리오 (대화는 가상, 정답 판정은 STYLE 상품설명서 원문 확인)",
    rebuttal: "“그런 오답이 실제로 나오나요?” → 실제 AI 실행 로그가 아니라 원문에서 확인한 함정으로 만든 가상 대화라고 먼저 밝힌다. 실제 오답 로그는 구현 후 교체한다.",
  }, "한 고객이 AI에게 묻습니다. ONE PICK STYLE 카드로 지난달 상품권 8만원, 버스비 2만원을 썼는데 이번 달 대중교통 캐시백을 받느냐고요. AI는 10만원을 채웠으니 5% 캐시백을 받는다고 답합니다. 그럴듯하지만, 상품설명서 원문에서 상품권 구매는 전월실적 산정에서 제외됩니다. 인정되는 실적은 많아야 2만원이고, 원칙적으로 혜택 대상이 아닙니다. 단, 카드 사용 등록 직후 다음 달 말일까지는 실적과 관계없이 제공하는 예외가 있습니다. 이 대화는 가상입니다. 그런데 이런 답이 실제로 나갔다면, 카드사는 AI가 어떤 조건을 적용했는지, 상품권을 실적으로 봤는지, 어느 조항을 근거로 삼았는지 확인할 수 있을까요? 이 질문은 자사 앱에만 해당하지 않습니다. 고객이 외부 AI에게 물어도 같은 판단 근거가 나가야 하고, 그 연결 방법이 뒤에서 볼 공통 엔진과 MCP입니다. 다만 오늘 발표의 중심은 먼저 판단 근거를 검증할 수 있느냐입니다.");
}

// ---- 2 six questions ----
{
  const s = content("프로젝트의 출발점", "AI가 ‘적용 가능’이라고 답했습니다. 담당자는 무엇을 확인할 수 있어야 할까요?", "도입");
  pills(s, ["프로젝트 목적"]);
  const qs = [
    ["1", "AI가 어떤 카드와 혜택을 선택했는가", 0],
    ["2", "어떤 전월실적·할인·적립·제외 조건을 적용했는가", 0],
    ["3", "그 조건은 카드 전체에 걸리는가, 특정 혜택에만 걸리는가", 0],
    ["4", "어떤 공식 상품설명서 조항을 근거로 판단했는가", 0],
    ["5", "잘못된 답변이라면 어느 단계에서 오류가 생겼는가", 1],
    ["6", "조건이 바뀌면 어떤 카드·혜택·판단을 다시 검토해야 하는가", 2],
  ];
  const tags = [["판단 근거 검증 · 핵심", TEAL_T, TEAL_D, TEAL], ["오류 원인 추적 · 확장①", RED_T, RED_D, RED], ["변경 영향 · 확장②", AMBER_T, AMBER_D, AMBER]];
  const cw = (CW - 0.5) / 3, ch = 1.42;
  qs.forEach((q, i) => {
    const x = L + (i % 3) * (cw + 0.25), y = 1.85 + Math.floor(i / 3) * (ch + 0.2);
    const tg = tags[q[2]];
    rect(s, { x, y, w: cw, h: ch, fill: { color: q[2] === 0 ? "FFFFFF" : MIST }, line: { color: q[2] === 0 ? TEAL : MIST, width: 1.25 } });
    boxT(s, q[0], { shape: pres.shapes.OVAL, x: x + 0.2, y: y + 0.18, w: 0.44, h: 0.44, fill: { color: tg[3] }, line: { color: tg[3] }, color: q[2] === 2 ? INK : "FFFFFF", fontSize: 14, bold: true, margin: 0 });
    chip(s, tg[0], x + 0.78, y + 0.22, 2.3, 0.34, tg[1], tg[2], { fontSize: 11 });
    T(s, q[1], { x: x + 0.2, y: y + 0.72, w: cw - 0.4, h: 0.62, fontSize: 15, bold: true, color: INK, valign: "middle" });
  });
  boxT(s, [{ text: "+ 확장③  ", options: { bold: true, color: VIO } }, { text: "이렇게 검증된 판단을 여러 AI 채널(내부 검토·자사 앱·외부 AI)에서 재사용 — 공통 엔진·MCP", options: { color: TXT } }], { x: L, y: 5.12, w: CW, h: 0.5, fill: { color: VIO_T }, line: { color: VIO_T }, fontSize: 14, align: "left", margin: 14 });
  boxT(s, [
    { text: "그럴듯함 ≠ 정확함.  ", options: { bold: true, color: AMBER } },
    { text: "원문을 찾아 보여주는 것만으로는 부족합니다. 핵심은 ", options: { color: "FFFFFF" } },
    { text: "혜택별 조건과 판단 결과의 연결", options: { bold: true, color: AMBER } },
    { text: "을 남기는 것입니다.", options: { color: "FFFFFF" } },
  ], { x: L, y: 5.8, w: CW, h: 0.8, fill: { color: INK }, line: { color: INK }, fontSize: 16, align: "left", margin: 14 });
  footer(s, "최초 기획 의도: “AI가 카드 혜택을 판단하고 안내할 때, 카드사 담당자가 그 판단의 과정과 근거를 확인할 수 있어야 한다.”");
  notes(s, "프로젝트 목적 — 담당자가 확인할 6가지", {
    purpose: "최초 기획 의도를 6개 질문으로 못 박고, 이후 발표 구조(핵심 → 확장①②③)를 미리 보여준다.",
    status: "프로젝트 목적 (팀이 정의한 요구사항)",
    rebuttal: "“결국 RAG에 출처 붙이는 것 아닌가?” → 출처 문서 위치(4번)는 6개 중 하나일 뿐이고, 2·3번(어떤 조건을 어느 범위로 적용했나)이 남지 않으면 오답 원인을 찾을 수 없다고 답한다.",
  }, "저희 프로젝트의 최초 목적은 하나입니다. AI가 카드 혜택을 판단했다면, 카드사 담당자가 그 판단의 과정과 근거를 확인할 수 있어야 한다는 것입니다. 담당자가 확인해야 할 것을 여섯 가지로 정리했습니다. 어떤 카드와 혜택을 골랐는지, 어떤 실적·할인·제외 조건을 적용했는지, 그 조건이 카드 전체인지 특정 혜택에만 걸리는지, 어느 약관 조항을 근거로 했는지. 이 네 가지가 판단 근거 검증, 저희의 핵심입니다. 여기서 두 가지가 자연스럽게 따라 나옵니다. 틀렸다면 어느 단계에서 틀렸는지, 그리고 조건이 바뀌면 무엇을 다시 봐야 하는지입니다. 마지막으로 이렇게 검증된 판단을 여러 AI 채널이 재사용하는 것이 세 번째 확장입니다. 원문을 찾아 보여주는 것만으로는 부족합니다. 혜택별 조건과 판단 결과가 연결돼 있어야 합니다.");
}

// ---- 3 Shinhan ----
{
  const s = content("01   업계의 신호", "업계도 같은 문제를 말합니다 — AI 접점 확장과 조건 판단 엔진 개발", "도입");
  pills(s, ["공식 확인"]);
  const cards = [
    { x: L, date: "2026-09-09  ·  신한금융그룹 보도자료", head: "복합 금융상품 조건을 판단하는 AI 엔진 공동 개발 착수 (커넥셔너리)", lab: "회사가 밝힌 기존 생성형 AI의 문제", chips: ["환각(정보 왜곡)", "답변 비일관성", "복합 조건 누락", "정책·규정 미반영"], bg: RED_T, fg: RED_D, foot: "“조건 자체를 구조화해 탐색 가능한 형태로 정의하면 … 조건 수정만으로 실시간 반영될 수 있다”", it: true },
    { x: 6.78, date: "2026-09-13  ·  신한카드 보도자료", head: "카드사 최초 ‘ChatGPT for Kakao’ 연계 대화형 금융 서비스", lab: "외부 AI 대화창에서 제공하는 기능", chips: ["카드 추천", "인기카드 조회", "카드 상세혜택 조회", "소비 인사이트"], bg: TEAL_T, fg: TEAL_D, foot: "카카오 ‘PlayMCP’ 기반 ‘카카오 툴즈’에 신한카드 툴을 연동 — 외부 AI가 카드사 도구를 호출하는 구조", it: false },
  ];
  cards.forEach((c) => {
    rect(s, { x: c.x, y: 1.85, w: 5.95, h: 3.6 });
    T(s, c.date, { x: c.x + 0.25, y: 2.03, w: 5.5, h: 0.3, fontSize: 12, bold: true, color: MUTED });
    T(s, c.head, { x: c.x + 0.25, y: 2.38, w: 5.5, h: 0.75, fontSize: 17, bold: true, color: INK });
    T(s, c.lab, { x: c.x + 0.25, y: 3.2, w: 5.5, h: 0.28, fontSize: 12, color: MUTED });
    c.chips.forEach((t, i) => chip(s, t, c.x + 0.25 + (i % 2) * 2.78, 3.52 + Math.floor(i / 2) * 0.45, 2.68, 0.37, c.bg, c.fg, { fontSize: 13 }));
    T(s, c.foot, { x: c.x + 0.25, y: 4.5, w: 5.5, h: 0.8, fontSize: 13, color: SLATE, italic: c.it });
  });
  boxT(s, "외부 AI 채널은 MCP 같은 도구 연결로 넓어지고, 그 답의 판단 근거를 확인하는 일은 카드사의 과제로 남습니다.", { x: L, y: 5.65, w: CW, h: 0.82, fill: { color: INK }, line: { color: INK }, color: "FFFFFF", fontSize: 15, bold: true, align: "left", margin: 14 });
  T(s, "두 시스템의 내부 연계 여부, GraphRAG 사용 여부는 공개 자료에 없습니다. 우리 기술의 검증 근거가 아니라 ‘실재하는 문제’의 근거로 인용합니다.", { x: L, y: 6.57, w: CW, h: 0.32, fontSize: 11, color: RED_D });
  footer(s, "출처: shinhangroup.com/kr/archive/press/detail/966 (2026-09-09) · press1.newswire.co.kr/newsRead.php?no=1042468 (2026-09-13) — 2026-10-30 원문 재확인");
  notes(s, "01 업계의 신호 — 신한카드 사례", {
    purpose: "문제가 팀의 상상이 아니라 업계가 공식적으로 말한 과제임을 보인다.",
    status: "공식 확인 (2026-10-30 보도자료 원문 재확인)",
    rebuttal: "“신한이 이미 만들고 있지 않나?” → 차별점 주장이 아니라 문제의 실재 근거로 인용한다. 신한 엔진이 GraphRAG인지, 두 서비스가 연결됐는지는 공개되지 않았다.",
  }, "업계도 같은 문제를 말하고 있습니다. 신한카드는 2026년 9월 9일 복잡한 금융상품 조건을 판단하는 AI 엔진 공동 개발을 발표했고, 나흘 뒤에는 ChatGPT for Kakao에 카드 추천과 혜택 조회를 연결했습니다. 신한이 직접 꼽은 기존 생성형 AI의 문제는 환각, 답변 비일관성, 복합 조건 누락, 정책·규정 미반영입니다. 외부 AI 채널은 넓어지는데, 그 답이 어떤 조건과 근거로 나왔는지 확인하는 일은 여전히 카드사의 몫입니다. 이 사례는 저희 기술이 검증됐다는 근거가 아니라 문제가 실재한다는 근거로 인용합니다. 두 시스템이 내부적으로 연결됐는지, GraphRAG를 쓰는지는 공개되지 않았습니다. 한 가지 기억해 두실 점은, 신한이 외부 AI에 카드사 기능을 연결한 방식이 MCP라는 것입니다. 저희 구조에서 MCP가 어떤 역할을 하는지는 14쪽에서 이어서 말씀드리겠습니다.");
}

// ---- 4 problem ----
{
  const s = content("02   문제 정의", "AI 채널이 다양해질수록, 판단 근거는 어디서 검증해야 할까요?", "도입");
  pills(s, ["팀 해석"]);
  boxT(s, "상품설명서\n약관\n(공식 원문)", { x: L, y: 2.75, w: 1.85, h: 1.55, fill: { color: INK }, line: { color: INK }, color: "FFFFFF", fontSize: 15, bold: true });
  const ch = ["상품·준법 검토", "상담원 지원", "자사 앱 AI 상담", "외부 AI 서비스"];
  const cy = [1.95, 2.85, 3.75, 4.65];
  line(s, 2.45, 3.525, 0.45, 0);
  line(s, 2.9, cy[0] + 0.36, 0, cy[3] - cy[0]);
  ch.forEach((t, i) => {
    arrow(s, 2.9, cy[i] + 0.36, 0.38, 0);
    boxT(s, t, { x: 3.3, y: cy[i], w: 2.95, h: 0.72, align: "left", fontSize: 15, bold: true, color: INK, margin: 12 });
  });
  boxT(s, "채널마다\n다른 사본,\n다른 해석", { x: 6.45, y: 1.95, w: 1.35, h: 3.42, fill: { color: RED_T }, line: { color: RED_T }, color: RED_D, fontSize: 15, bold: true });

  T(s, "흩어지면 생기는 위험 → 그래서 필요한 것", { x: 8.2, y: 1.95, w: 4.53, h: 0.35, fontSize: 15, bold: true, color: INK });
  const rows = [
    ["근거 검증", "조건이 빠진 답, 출처 없는 답", "→ 답마다 적용 조건·원문 조항 확인"],
    ["오류 추적", "틀린 답의 발생 단계를 모름", "→ 단계별 기록으로 원인 위치 확인"],
    ["변경 영향", "바뀐 조건이 일부 채널에만 반영", "→ 다시 검토할 혜택·판단 목록"],
    ["재사용", "채널마다 판단 로직을 다시 구현", "→ 검증한 판단을 여러 채널이 호출"],
  ];
  rows.forEach((r, i) => {
    const y = 2.4 + i * 0.82;
    boxT(s, String(i + 1), { shape: pres.shapes.OVAL, x: 8.2, y: y + 0.05, w: 0.46, h: 0.46, fill: { color: i === 0 ? TEAL : AMBER }, line: { color: i === 0 ? TEAL : AMBER }, color: i === 0 ? "FFFFFF" : INK, fontSize: 15, bold: true, margin: 0 });
    T(s, [
      { text: r[0] + "  ", options: { bold: true, color: INK, fontSize: 15 } },
      { text: r[1], options: { color: MUTED, fontSize: 12, breakLine: true } },
      { text: r[2], options: { color: TEAL_D, bold: true, fontSize: 13 } },
    ], { x: 8.8, y: y, w: 3.93, h: 0.75, valign: "top", lineSpacingMultiple: 1.1 });
  });
  boxT(s, "이 발표의 질문: AI 판단의 근거를 한곳에서 검증하고, 여러 AI 채널에 같은 근거를 공급할 수 있는가?", { x: L, y: 5.75, w: CW, h: 0.75, fill: { color: AMBER_T }, line: { color: AMBER_T }, color: INK, fontSize: 16, bold: true, align: "left", margin: 14 });
  footer(s, "위험 유형은 신한카드 2026-09-09 발표의 문제 정의(환각·비일관성·조건 누락·규정 미반영)를 채널·검증 관점으로 재구성한 팀 해석입니다.");
  notes(s, "02 문제 정의 — 판단 근거는 어디서 검증하나", {
    purpose: "채널이 늘수록 판단 근거 검증 지점이 흩어진다는 문제를 4개 축(근거 검증·오류 추적·변경 영향·재사용)으로 정리한다.",
    status: "팀 해석",
    rebuttal: "“카드사는 이미 상품 DB로 통제하지 않나?” → 내부 시스템 구조는 확인하지 못했다. 이 발표는 고지된 원문과 AI 판단의 일치를 점검하는 보완 계층을 제안한다.",
  }, "하나의 카드 상품 조건이 상품·준법 검토, 상담원, 자사 앱 AI, 외부 AI로 흘러갑니다. 채널마다 사본과 해석을 따로 가지면 네 가지 문제가 생깁니다. 조건이 빠지거나 출처가 없는 답, 틀린 답이 어느 단계에서 생겼는지 모르는 문제, 바뀐 조건이 일부 채널에만 반영되는 문제, 채널마다 판단 로직을 다시 만드는 비용입니다. 그래서 필요한 것을 근거 검증, 오류 추적, 변경 영향, 재사용으로 정리했습니다. 첫 번째가 핵심이고 나머지 셋은 그 위에서 확장됩니다. 이 네 단어가 이후 발표의 축입니다.");
}

pres.addSection({ title: "왜 어려운가" });

// ---- 5 Hana scope ----
{
  const s = content("03   실제 약관에서 본 어려움 ①", "AI가 틀리기 쉬운 지점: 같은 ‘상품권 제외’도 걸리는 곳이 다릅니다", "왜 어려운가");
  pills(s, ["원문 확인"]);
  boxT(s, "Q.  상품권 구매는 실적에서 빠지는가, 할인에서 빠지는가 — AI는 이 둘을 구분해서 답하고 있을까요?", { x: L, y: 1.8, w: CW, h: 0.62, fill: { color: AMBER_T }, line: { color: AMBER_T }, color: AMBER_D, fontSize: 17, bold: true, align: "left", margin: 14 });
  const H = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: INK }, fontSize: 13 } });
  const dot = (t) => ({ text: t, options: { color: RED_D, bold: true, align: "center" } });
  const rows = [
    [H("하나카드 상품"), H("실적 산정 제외"), H("혜택 제외"), H("실적 조건이 걸린 혜택"), H("실적 조건이 없는 혜택")],
    ["ONE PICK STYLE (체크)", dot("●"), dot("● 서비스 공통"), "ONE MORE 대중교통 (10만원)\nONE MORE 놀이공원 (20만원)", "ONE PICK · STYLE 영역"],
    ["ONE PICK PLAY (체크)", dot("●"), dot("● 서비스 공통"), "ONE MORE 대중교통 (10만원)\nONE MORE 놀이공원 (20만원)", "ONE PICK · PLAY 영역"],
    ["BT (신용)", dot("●"), dot("● BIG TICKET"), "인천공항 라운지 (50만원)", "BIG TICKET 청구할인"],
    ["에너지 더블 (신용)", dot("●"), dot("● 대형마트 할인"), "에너지 공과금 청구할인 (40/80만원)\n일상생활 청구할인 (40만원)", "—"],
  ];
  s.addTable(rows, { x: L, y: 2.6, w: CW, colW: [2.25, 1.6, 1.75, 3.9, 2.63], rowH: [0.45, 0.6, 0.6, 0.45, 0.6], fontFace: F, fontSize: 13, color: TXT, border: tblBorder, valign: "middle", margin: [3, 6, 3, 6] });
  const ins = [
    ["① 실적 제외 ≠ 혜택 제외", "상품권은 ‘실적에 잡히지 않는 금액’이기도 하고 ‘할인되지 않는 결제’이기도 합니다. 한쪽만 연결하면 1장 같은 오답이 나옵니다."],
    ["② 조건은 카드가 아니라 혜택에 걸립니다", "BT의 BIG TICKET은 지난달 실적 조건이 ‘없음’, 라운지는 50만원. 카드 단위로 묶으면 조건을 잘못 넓힙니다."],
  ];
  ins.forEach((t, i) => {
    const x = L + i * 6.18;
    rect(s, { x, y: 5.68, w: 5.95, h: 1.18 });
    T(s, [{ text: t[0], options: { bold: true, color: INK, fontSize: 15, breakLine: true } }, { text: t[1], options: { fontSize: 13, color: SLATE } }], { x: x + 0.2, y: 5.78, w: 5.6, h: 1.02, lineSpacingMultiple: 1.1 });
  });
  footer(s, "원문: 하나카드 상품설명서 ONE PICK STYLE(15650_20260429)·PLAY(15651_20260429)·BT(14324_20260310)·에너지 더블(14422_20251224) 1쪽, 2026-10-30 대조");
  notes(s, "03 어려움 ① — 상품권 제외의 적용 범위", {
    purpose: "AI가 틀리는 이유가 '정보가 없어서'가 아니라 '조건의 적용 범위를 섞어서'임을 실제 약관으로 보인다.",
    status: "원문 확인 (4종 상품설명서 1쪽 대조)",
    rebuttal: "“4종은 너무 적지 않나?” → 이 표는 현재 원문 대조를 마친 4종의 사례이며 약 10종 확대는 목표(5장)라고 구분한다.",
  }, "AI가 왜 틀리기 쉬운지 실제 약관으로 보겠습니다. 원문 대조를 마친 하나카드 4종, 체크카드 STYLE·PLAY와 신용카드 BT·에너지 더블에는 모두 상품권 제외 문구가 있습니다. 그런데 같은 상품권이 전월실적 산정 제외로도, 할인 제외로도 쓰입니다. 1장의 오답은 바로 이 둘 중 하나만 연결했을 때 나옵니다. 또 실적 조건은 카드 전체가 아니라 혜택마다 걸립니다. BT의 BIG TICKET은 원문 표에 지난달 실적이 ‘없음’이고, 인천공항 라운지만 50만원입니다. 카드 단위로 조건을 묶으면 조건을 잘못 넓히게 됩니다. 이것이 담당자가 확인해야 할 세 번째 질문, 적용 범위입니다.");
}

// ---- 6 PDF ----
{
  const s = content("04   실제 약관에서 본 어려움 ②", "PDF는 숫자는 남기고, 조건 사이의 관계는 잃어버립니다", "왜 어려운가");
  pills(s, ["원문 확인"]);
  const xs = [L, 4.75, 8.9], cw = 3.83;
  const heads = ["표가 표로 읽히지 않습니다", "같은 숫자, 다른 혜택", "같은 문장, 다른 결론"];
  heads.forEach((h, i) => {
    rect(s, { x: xs[i], y: 1.85, w: cw, h: 3.35 });
    T(s, h, { x: xs[i] + 0.22, y: 2.0, w: cw - 0.44, h: 0.4, fontSize: 16, bold: true, color: INK });
  });
  boxT(s, "1.5%\n1.2%\n1.0%\n0.5%", { shape: pres.shapes.RECTANGLE, x: xs[0] + 0.3, y: 2.55, w: 1.2, h: 1.2, fill: { color: "FFFFFF" }, line: { color: SLATE, width: 1 }, color: INK, fontSize: 12 });
  boxT(s, "300만원\n한도 없음", { shape: pres.shapes.RECTANGLE, x: xs[0] + 1.5, y: 2.55, w: 1.2, h: 1.2, fill: { color: "FFFFFF" }, line: { color: SLATE, width: 1 }, color: INK, fontSize: 12 });
  boxT(s, "구간\n기준\n열\n소실", { x: xs[0] + 2.82, y: 2.55, w: 0.75, h: 1.2, fill: { color: RED_T }, line: { color: RED_T }, color: RED_D, fontSize: 11, bold: true, margin: 2 });
  T(s, "BT BIG TICKET 표: 할인율 4개가 한 셀로 추출되고 이용금액 구간 열이 빠집니다. STYLE·PLAY는 기본 표 탐지 0개.", { x: xs[0] + 0.22, y: 3.95, w: cw - 0.44, h: 1.5, fontSize: 13, color: SLATE, lineSpacingMultiple: 1.1 });
  ["ONE PICK  월 5천원", "STYLE  월 5천원", "PLAY  월 5천원"].forEach((t, i) => chip(s, t, xs[1] + 0.3, 2.55 + i * 0.42, 3.23, 0.34, AMBER_T, AMBER_D));
  T(s, "‘5천원’ 검색은 세 혜택을 모두 찾지만, 어느 혜택의 한도인지는 표 구조가 있어야 확정됩니다.", { x: xs[1] + 0.22, y: 3.95, w: cw - 0.44, h: 1.5, fontSize: 13, color: SLATE, lineSpacingMultiple: 1.1 });
  T(s, "“PG·간편결제 가맹점으로 분류되는 경우 …”", { x: xs[2] + 0.22, y: 2.5, w: cw - 0.44, h: 0.3, fontSize: 12, italic: true, color: MUTED });
  [["하나 ONE PICK", "혜택 제공", TEAL_T, TEAL_D], ["KB Youth Club", "제외", RED_T, RED_D], ["KB 첵첵", "제외될 수 있음", AMBER_T, AMBER_D]].forEach((r, i) => {
    const y = 2.85 + i * 0.37;
    T(s, r[0], { x: xs[2] + 0.3, y, w: 1.6, h: 0.31, fontSize: 12, color: INK, valign: "middle" });
    chip(s, r[1], xs[2] + 1.95, y, 1.6, 0.31, r[2], r[3]);
  });
  T(s, "문구가 같다고 같은 규칙으로 합치면 틀린 답이 됩니다. (타사는 비교용, 프로젝트 범위는 하나카드)", { x: xs[2] + 0.22, y: 3.95, w: cw - 0.44, h: 1.5, fontSize: 13, color: SLATE, lineSpacingMultiple: 1.1 });
  boxT(s, "필요한 것:  원문 위치 보존(M1) · 근거 문장 필수 추출(M3·M4) · 정책 단위 정규화(M5) · 원문 대조 검증(M8)", { x: L, y: 5.45, w: CW, h: 0.72, fill: { color: INK }, line: { color: INK }, color: "FFFFFF", fontSize: 14, bold: true, align: "left", margin: 14 });
  footer(s, "card_pdf_structuring_validation.md (PyMuPDF 1.28.2·pdfplumber 0.11.10 기본 옵션 표본 검증) · card_scope_comparison_claude.md §5-3");
  notes(s, "04 어려움 ② — PDF 구조 손실", {
    purpose: "원문 근거를 남기려면 PDF 단계부터 위치·구조를 보존해야 함을 보인다(오류 추적 ① 단계의 근거).",
    status: "원문 확인 (팀 표본 검증 기록)",
    rebuttal: "“더 좋은 파서를 쓰면 되지 않나?” → 기본 옵션 표본 검증 결과이며 파서 튜닝·수작업 보정이 필요하다는 점을 그대로 공개한다.",
  }, "두 번째 어려움은 원문 자체입니다. PDF에서 글자와 숫자는 거의 다 나옵니다. 그런데 BT의 BIG TICKET 표는 할인율 4개가 한 셀로 뭉치고 구간 열이 사라집니다. STYLE과 PLAY는 기본 표 탐지가 0개였습니다. ONE PICK, STYLE, PLAY에 모두 월 5천원이 있어 숫자만으로는 어느 혜택의 한도인지 알 수 없습니다. 그리고 PG·간편결제 재분류 문장은 카드사마다 거의 같지만 결론은 정반대입니다. 그래서 원문 위치 보존, 근거 문장 필수, 정책 단위 정규화, 원문 대조 검증이 필요합니다. 이 단계들이 뒤에서 볼 오류 추적의 단계이기도 합니다.");
}

// ---- 7 scope ----
{
  const s = content("05   분석 범위", "현재 4종 원문 대조, 목표는 체크·신용 약 10종입니다", "왜 어려운가");
  pills(s, ["원문 확인", "목표"]);
  T(s, "완료 — 상품설명서 원문 대조 4종", { x: L, y: 1.85, w: 5.4, h: 0.32, fontSize: 14, bold: true, color: TEAL_D });
  const done = [["체크", "ONE PICK STYLE", "15650_20260429"], ["체크", "ONE PICK PLAY", "15651_20260429"], ["신용", "BT", "14324_20260310"], ["신용", "에너지 더블", "14422_20251224"]];
  done.forEach((d, i) => {
    const x = L + (i % 2) * 2.75, y = 2.28 + Math.floor(i / 2) * 1.05;
    rect(s, { x, y, w: 2.6, h: 0.92, fill: { color: TEAL_T }, line: { color: TEAL, width: 1 } });
    chip(s, d[0], x + 0.15, y + 0.14, 0.62, 0.3, d[0] === "체크" ? TEAL : INK, "FFFFFF", { fontSize: 11 });
    T(s, d[1], { x: x + 0.85, y: y + 0.12, w: 1.7, h: 0.34, fontSize: 13, bold: true, color: INK, valign: "middle" });
    T(s, d[2], { x: x + 0.15, y: y + 0.55, w: 2.3, h: 0.28, fontSize: 11, color: TEAL_D, fontFace: MONO });
  });
  boxT(s, [
    { text: "추가 약 6종 — 미정", options: { bold: true, color: SLATE, fontSize: 14, breakLine: true } },
    { text: "공식 상품설명서 확인 후 아래 기준으로 선정합니다. 선정 전이므로 카드 이름을 쓰지 않습니다.", options: { color: MUTED, fontSize: 12 } },
  ], { x: L, y: 4.45, w: 5.35, h: 1.05, fill: { color: "FFFFFF" }, line: { color: "A0AAB8", width: 1.25, dashType: "dash" }, align: "left", margin: 12 });

  const rx = 6.3, rw = R - rx;
  rect(s, { x: rx, y: 1.85, w: rw, h: 1.05, fill: { color: AMBER_T }, line: { color: AMBER_T } });
  T(s, [
    { text: "선정 기준", options: { bold: true, color: AMBER_D, fontSize: 14, breakLine: true } },
    { text: "무작위가 아니라, 유사한 혜택은 있지만 조건은 다른 체크·신용카드 — 같은 질문에 다른 판단이 나와야 하는 조합", options: { color: TXT, fontSize: 13 } },
  ], { x: rx + 0.2, y: 1.95, w: rw - 0.4, h: 0.9, lineSpacingMultiple: 1.1 });
  T(s, "비교 축 8개", { x: rx, y: 3.1, w: rw, h: 0.32, fontSize: 14, bold: true, color: INK });
  const axes = ["공통·유사 혜택", "체크·신용 조건 차이", "전월실적", "실적 제외", "할인·적립 제외", "월 한도", "혜택별 적용 범위", "원문 근거"];
  const aw = (rw - 0.15) / 2;
  axes.forEach((a, i) => chip(s, (i + 1) + "  " + a, rx + (i % 2) * (aw + 0.15), 3.5 + Math.floor(i / 2) * 0.5, aw, 0.4, MIST, INK, { fontSize: 13, align: "left", margin: 8 }));
  boxT(s, "발표의 수치·시연은 모두 4종 원문 기준입니다. 약 10종은 목표이며, 선정·적재·검증은 완료 전입니다.", { x: L, y: 5.75, w: CW, h: 0.75, fill: { color: INK }, line: { color: INK }, color: "FFFFFF", fontSize: 16, bold: true, align: "left", margin: 14 });
  footer(s, "card_scope_comparison.md: 하나카드 PDF 9종 확보 기록(문서에 따라 12종 표기) · 약 10종 최종 선정 미완료 · 원문 PDF는 저장소에 넣지 않음");
  notes(s, "05 분석 범위 — 4종 완료 vs 약 10종 목표", {
    purpose: "실제 검증한 범위(4종)와 목표 범위(약 10종)를 한 장에서 분리해, 이후 모든 수치가 4종 기준임을 못 박는다.",
    status: "원문 확인(4종) · 목표(약 10종, 선정 전)",
    rebuttal: "“10종을 한다면서 왜 4종만 보여주나?” → 4종으로 판단 구조와 함정을 먼저 확인했고, 추가 6종은 같은 8개 축으로 선정한다. 선정 전 카드 이름은 만들지 않는다.",
  }, "분석 범위를 분명히 하겠습니다. 지금까지 상품설명서 원문을 직접 대조한 카드는 4종입니다. 체크카드 ONE PICK STYLE과 PLAY, 신용카드 BT와 에너지 더블입니다. 목표는 체크·신용 약 10종입니다. 나머지 약 6종은 무작위로 고르지 않고, 혜택은 비슷하지만 조건이 다른 카드를 고를 계획입니다. 같은 질문에 서로 다른 판단이 나와야 하는 조합이어야 판단 근거 검증이 의미가 있기 때문입니다. 비교 축은 여기 여덟 가지입니다. 아직 선정 전이라 추가 카드 이름은 쓰지 않았습니다. 오늘 발표의 수치와 시연은 모두 4종 원문 기준입니다.");
}

pres.addSection({ title: "왜 GraphRAG인가" });

// ---- 8 comparison ----
{
  const s = content("06   왜 GraphRAG인가", "“SQL이나 일반 RAG로도 되지 않나요?” — 됩니다. 차이는 관계 경로를 다루는 방식입니다", "왜 GraphRAG인가");
  pills(s, ["가설 · 검증 예정"]);
  const sym = { o: ["○ ", TEAL_D], t: ["△ ", AMBER_D], x: ["× ", RED_D] };
  const c = (k, t) => ({ text: [{ text: sym[k][0], options: { bold: true, color: sym[k][1] } }, { text: t, options: { color: TXT } }] });
  const H = (t, bg) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: bg }, fontSize: 13 } });
  const lab = (t) => ({ text: t, options: { bold: true, color: INK, fill: { color: MIST } } });
  const rows = [
    [H("비교 기준", SLATE), H("일반 벡터 RAG", SLATE), H("PostgreSQL + 구조화 조건 + LLM", SLATE), H("Neo4j GraphRAG", INK)],
    [lab("단순 혜택 검색"), c("o", "유사 청크 검색으로 충분"), c("o", "정규화된 조건 조회"), c("o", "패턴 매칭 — 차이 작음")],
    [lab("혜택별 조건 적용 범위"), c("x", "청크 문맥 의존, 실적/혜택 제외 혼동 위험"), c("o", "scope 컬럼으로 표현 가능"), c("o", "관계 속성(scope)으로 표현")],
    [lab("복수 제외 조건–조항 연결"), c("t", "청크 출처는 남지만 조건–조항 연결 없음"), c("o", "근거 키 JOIN으로 연결 가능"), c("o", "조건·조항이 경로로 함께 반환")],
    [lab("판단 근거 경로의 명시적 표현"), c("x", "생성 답변에 경로가 남지 않음"), c("t", "결과는 남지만 경로는 쿼리로 재구성"), c("o", "카드→혜택→조건→조항 경로가 결과")],
    [lab("조건 변경 영향 탐색"), c("x", "영향 목록의 완전성 보장 불가"), c("t", "다중 JOIN·재귀 CTE, 관계 유형이 늘수록 복잡"), c("o", "가변 길이 경로 탐색으로 표현")],
    [lab("오류 원인 추적"), c("t", "검색된 청크 로그만 남음"), c("t", "쿼리 로그 + JOIN 재현 필요"), c("o", "관계별 근거 속성으로 잘못된 관계 특정")],
    [lab("모델링·구현·유지보수 비용"), c("o", "가장 낮음"), c("o", "팀 기존 역량, DB 설계 초안 보유"), c("x", "Neo4j 인프라·온톨로지·추출 품질 관리")],
  ];
  s.addTable(rows, { x: L, y: 1.8, w: CW, colW: [2.5, 3.33, 3.15, 3.15], rowH: 0.47, fontFace: F, fontSize: 12, color: TXT, border: tblBorder, valign: "middle", margin: [3, 6, 3, 6] });
  T(s, "○ 적합 예상  △ 조건부  × 어려움 예상 — 설계·문헌 기반 예상이며 실험 전입니다 (정확도·성능 우위를 주장하지 않음)", { x: L, y: 5.72, w: CW, h: 0.28, fontSize: 11, color: MUTED, align: "right" });
  boxT(s, [
    { text: "우리의 주장은 ‘GraphRAG가 항상 더 정확하다’가 아닙니다. ", options: { bold: true, color: INK } },
    { text: "판단 근거 경로를 결과로 함께 남기고, 변경 영향과 오류 위치를 경로로 찾는 일이 더 단순해지는지를 같은 질문으로 세 방식에 던져 확인합니다 (부록 C).", options: { color: TXT } },
  ], { x: L, y: 6.05, w: CW, h: 0.85, fill: { color: AMBER_T }, line: { color: AMBER_T }, fontSize: 14, align: "left", margin: 14 });
  footer(s, "현재 4종 대조·약 10종 목표 · SQL 대비 우위는 미검증 · 비교안: sql/hana_card_db_design.md (설계 초안, DB 미적용)");
  notes(s, "06 왜 GraphRAG인가 — SQL·일반 RAG 비교", {
    purpose: "가장 먼저 나올 반박을 먼저 꺼내고, 차이를 '정확도'가 아니라 '관계 경로를 남기는 방식'으로 한정한다.",
    status: "가설 · 검증 예정 (표 기호는 예상, 실험 전)",
    rebuttal: "“그래프 없이 SQL로 충분하지 않나?” → 동의한다. 단순 검색은 차이가 작고 비용은 GraphRAG가 가장 높다. 차이가 예상되는 곳은 근거 경로 표현·변경 영향·오류 추적이며, 부록 C 실험으로 확인한다.",
  }, "심사위원께서 가장 먼저 물으실 질문을 먼저 꺼내겠습니다. SQL이나 일반 RAG로도 되지 않나요? 됩니다. 단순 혜택 검색은 세 방식 모두 가능하고 차이가 작습니다. 비용은 GraphRAG가 가장 높습니다. 차이가 예상되는 곳은 저희 목적과 맞닿은 부분입니다. 판단에 쓰인 카드, 혜택, 조건, 조항의 경로를 결과 자체로 남길 수 있는지, 조건이 바뀌었을 때 영향을 경로로 따라갈 수 있는지, 그리고 틀렸을 때 어느 관계가 잘못 붙었는지 근거 속성으로 특정할 수 있는지입니다. 표의 기호는 실험 결과가 아니라 예상입니다. 정확도나 성능이 더 낫다고 주장하지 않고, 같은 질문으로 세 방식을 비교해 확인하겠습니다.");
}

pres.addSection({ title: "제안 구조와 시연" });

// ---- 9 architecture ----
{
  const s = content("07   제안 구조", "질문에서 원문 근거까지, 하나의 엔진이 판단 경로를 남깁니다", "제안 구조와 시연");
  pills(s, ["설계안"]);
  const top = 2.2, hh = 3.0, mid = top + hh / 2;
  const hdr = (t, x, w) => T(s, t, { x, y: 1.82, w, h: 0.3, fontSize: 12, bold: true, color: MUTED });
  hdr("원천", L, 1.7);
  boxT(s, "하나카드\n약관 PDF\n4종 대조\n\n체크·신용\n약 10종 목표", { x: L, y: top, w: 1.7, h: hh, fill: { color: MIST }, color: INK, fontSize: 14, bold: true });
  arrow(s, 2.33, mid, 0.3, 0);
  hdr("지식화 파이프라인", 2.68, 2.35);
  ["M1 전처리·청크\n원문 위치 보존", "M3·M4 LLM 관계 추출\n근거 문장 필수", "M5 정규화\n정책 단위 병합", "M8 검증\nA·B 교차 대조"].forEach((t, i) => {
    boxT(s, t, { x: 2.68, y: top + i * 0.78, w: 2.35, h: 0.66, fill: { color: "FFFFFF" }, line: { color: LINE, width: 1 }, color: INK, fontSize: 12 });
  });
  arrow(s, 5.06, mid, 0.27, 0);
  hdr("판단 엔진 · GraphRAG (M6·M7)", 5.36, 3.2);
  rect(s, { x: 5.36, y: top, w: 3.2, h: hh, fill: { color: INK }, line: { color: INK } });
  node(s, "Card", "card", 5.55, top + 0.2, 1.25, 0.42, { line: { color: "6F7F96", width: 1 } });
  node(s, "Benefit", "benefit", 7.12, top + 0.2, 1.25, 0.42);
  node(s, "Condition", "cond", 7.12, top + 0.82, 1.25, 0.42);
  node(s, "Clause", "clause", 5.55, top + 0.82, 1.25, 0.42);
  arrow(s, 6.8, top + 0.41, 0.32, 0, "C9D3E0");
  arrow(s, 7.745, top + 0.62, 0, 0.2, "C9D3E0");
  arrow(s, 6.8, top + 1.03, 0.32, 0, "C9D3E0", { flipH: true });
  T(s, [
    { text: "Neo4j 적재 — 근거 속성 보존", options: { breakLine: true } },
    { text: "Cypher: 혜택 조회·영향 추적·경로", options: { breakLine: true } },
    { text: "판정: 적용 / 미적용 / 판단 불가(사유)", options: { color: AMBER, bold: true, breakLine: true } },
    { text: "판단 실행 기록: 질의·경로·판정·버전", options: { color: "7FD6C9", bold: true } },
  ], { x: 5.55, y: top + 1.42, w: 2.95, h: 1.5, fontSize: 12, color: "FFFFFF", lineSpacingMultiple: 1.2 });
  arrow(s, 8.59, mid, 0.27, 0);
  hdr("연결 계층", 8.9, 1.55);
  boxT(s, "내부 API\n어댑터", { x: 8.9, y: top, w: 1.55, h: 1.25, fill: { color: "FFFFFF" }, line: { color: SLATE, width: 1.25 }, color: INK, fontSize: 13, bold: true });
  boxT(s, [{ text: "MCP 서버", options: { bold: true, fontSize: 14, color: INK, breakLine: true } }, { text: "얇은 어댑터\n판단 로직 없음", options: { fontSize: 11, color: AMBER_D } }], { x: 8.9, y: top + 1.4, w: 1.55, h: 1.6, fill: { color: "FFFFFF" }, line: { color: AMBER, width: 2 } });
  hdr("AI 채널", 10.73, 2.0);
  const chs = [["내부 상품·준법 검토", top, 0.85], ["자사 앱 AI 상담", top + 1.0, 0.85], ["외부 AI 서비스\n(MCP 클라이언트)", top + 2.0, 1.0]];
  chs.forEach((c) => boxT(s, c[0], { x: 10.73, y: c[1], w: 2.0, h: c[2], fill: { color: MIST }, color: INK, fontSize: 13, bold: true }));
  arrow(s, 10.45, top + 0.42, 0.27, 0);
  arrow(s, 10.45, top + 1.08, 0.27, 0.32);
  arrow(s, 10.45, top + 2.4, 0.27, 0.1);
  T(s, "+ 마케팅 정책 계층 (확장 제안)", { x: 10.73, y: top + 3.08, w: 2.1, h: 0.3, fontSize: 10, color: VIO, bold: true });
  boxT(s, [{ text: "카드사가 보장할 수 있는 것   ", options: { bold: true, color: TEAL_D } }, { text: "어느 채널이든 같은 조건·근거·판단 경로를 공급하고, 공급 내역을 기록", options: { color: TXT } }], { x: L, y: 5.65, w: 7.96, h: 0.95, fill: { color: TEAL_T }, line: { color: TEAL_T }, fontSize: 14, align: "left", margin: 14 });
  boxT(s, [{ text: "보장할 수 없는 것", options: { bold: true, color: RED_D, breakLine: true } }, { text: "외부 AI의 호출 여부·요약·문구 표시", options: { color: TXT } }], { x: 8.73, y: 5.65, w: 4.0, h: 0.95, fill: { color: RED_T }, line: { color: RED_T }, fontSize: 14, align: "left", margin: 14 });
  footer(s, "설계안 · 4종 원문 대조 / 약 10종 확대 목표 · 엔진·MCP 미구현 · 현재 구현: 카드 등록·조회 CLI, 쿼리 로그 포매터(QueryLogger)");
  notes(s, "07 제안 구조 — 하나의 엔진이 판단 경로를 남긴다", {
    purpose: "원문 → 지식화 → 판단 엔진 → 연결 계층 → AI 채널 흐름을 보이고, 판단 실행 기록이 엔진 안에 있음을 강조한다.",
    status: "설계안 (엔진·MCP 미구현)",
    rebuttal: "“이 구조가 이미 돌아가나?” → 아니다. 현재 구현은 PostgreSQL 카드 등록·조회 CLI와 쿼리 로그 포매터까지다.",
  }, "저희가 제안하는 구조입니다. 왼쪽에서 하나카드 상품설명서를 원문 위치를 보존해 나누고, LLM이 근거 문장과 함께 관계를 추출하고, 정책 단위로 정규화한 뒤 원문과 대조해 검증합니다. 그 결과가 Neo4j의 카드-혜택-조건-조항 그래프이고, 판단은 엔진의 Cypher 쿼리가 합니다. V4에서 추가한 것은 엔진 안의 판단 실행 기록입니다. 어떤 질의로 어떤 경로를 따라 어떤 판정을 냈는지, 어떤 데이터 버전이었는지를 남깁니다. 오른쪽의 내부 API와 MCP 서버는 연결 계층일 뿐, 판단 로직을 갖지 않습니다. 그래서 채널이 달라도 같은 근거가 나가고, 카드사 쪽에는 무엇을 공급했는지 기록이 남습니다. 다만 외부 AI가 도구를 호출할지, 어떻게 요약할지는 카드사가 보장할 수 없습니다. 이 구조는 설계안입니다.");
}

// ---- 10 verification targets ----
{
  const s = content("08   검증 대상", "원문 근거와 AI 판단 과정은 다릅니다 — 둘 다 남겨야 검증할 수 있습니다", "제안 구조와 시연");
  pills(s, ["설계안"]);
  const top = 1.85, hh = 3.25;
  // A
  const ax = L, aw = 5.1;
  rect(s, { x: ax, y: top, w: aw, h: hh, fill: { color: "FFFFFF" }, line: { color: TEAL, width: 1.25 } });
  boxT(s, [{ text: "A. 원문 근거 추적", options: { bold: true, fontSize: 16, color: TEAL_D, breakLine: true } }, { text: "PDF에 있음 · 지식화 단계에서 저장", options: { fontSize: 12, color: TEAL_D } }], { x: ax, y: top, w: aw, h: 0.78, fill: { color: TEAL_T }, line: { color: TEAL_T }, align: "left", margin: 14, rectRadius: 0.1 });
  T(s, [
    { text: "문서 ID · 판 · 페이지", options: { bullet: true, breakLine: true } },
    { text: "조항 위치 (표·항목 이름)", options: { bullet: true, breakLine: true } },
    { text: "원문 문장 (evidence)", options: { bullet: true, breakLine: true } },
    { text: "추출된 조건과 그 적용 범위(scope)", options: { bullet: true, breakLine: true } },
    { text: "조건 ↔ 혜택 ↔ 카드 관계", options: { bullet: true } },
  ], { x: ax + 0.25, y: top + 0.95, w: aw - 0.5, h: 2.5, fontSize: 14, color: TXT, paraSpaceAfter: 6 });
  // B
  const bx = 7.63, bw = R - bx;
  rect(s, { x: bx, y: top, w: bw, h: hh, fill: { color: "FFFFFF" }, line: { color: AMBER, width: 1.25 } });
  boxT(s, [{ text: "B. 판단 실행 기록", options: { bold: true, fontSize: 16, color: AMBER_D, breakLine: true } }, { text: "PDF에 없음 · 질문마다 실행 시 기록", options: { fontSize: 12, color: AMBER_D } }], { x: bx, y: top, w: bw, h: 0.78, fill: { color: AMBER_T }, line: { color: AMBER_T }, align: "left", margin: 14, rectRadius: 0.1 });
  T(s, [
    { text: "질문과 해석 결과", options: { bullet: true, breakLine: true } },
    { text: "검색된 카드·혜택·조건", options: { bullet: true, breakLine: true } },
    { text: "사용한 그래프 관계와 조회 결과", options: { bullet: true, breakLine: true } },
    { text: "적용한 조건·제외 규칙", options: { bullet: true, breakLine: true } },
    { text: "판정(적용/미적용/판단 불가)과 사유", options: { bullet: true, breakLine: true } },
    { text: "답변–근거 일치 여부", options: { bullet: true, breakLine: true } },
    { text: "프롬프트·모델·데이터 버전, 실행 로그", options: { bullet: true } },
  ], { x: bx + 0.25, y: top + 0.92, w: bw - 0.5, h: 2.58, fontSize: 13, color: TXT, paraSpaceAfter: 3 });
  // link
  const mx = ax + aw + 0.12, mw = bx - mx - 0.12;
  T(s, "판정마다 연결", { x: mx, y: 2.55, w: mw, h: 0.28, fontSize: 11, bold: true, color: MUTED, align: "center" });
  chip(s, "evidence_id", mx + 0.1, 2.95, mw - 0.2, 0.42, VIO, "FFFFFF", { fontFace: MONO, fontSize: 11 });
  chip(s, "trace_id", mx + 0.1, 3.55, mw - 0.2, 0.42, AMBER, INK, { fontFace: MONO, fontSize: 11 });
  arrow(s, mx - 0.1, 3.16, 0.18, 0, VIO, { flipH: true });
  arrow(s, mx + mw - 0.08, 3.76, 0.18, 0, AMBER_D);
  T(s, "B의 각 판정이\nA의 어느 근거를\n썼는지 가리킴", { x: mx, y: 4.15, w: mw, h: 0.85, fontSize: 11, color: MUTED, align: "center" });
  boxT(s, [
    { text: "그래프 경로 제시 ≠ LLM 내부 사고 과정 설명.  ", options: { bold: true, color: RED_D } },
    { text: "검증 대상은 실행 시 기록 가능한 검색 경로·적용 규칙·근거, 그리고 최종 응답과의 일치 여부입니다.", options: { color: TXT } },
  ], { x: L, y: 5.35, w: CW, h: 0.82, fill: { color: RED_T }, line: { color: RED_T }, fontSize: 15, align: "left", margin: 14 });
  T(s, "구현 현황: src/common/query_logger.py — SQL·Cypher 원문·파라미터·결과를 로그로 남기는 포매터는 구현됨. trace 저장 구조와 evidence/trace id 연결은 설계안입니다.", { x: L, y: 6.3, w: CW, h: 0.4, fontSize: 11, color: SLATE });
  footer(s, "외부 AI 경유 시 B의 ‘질문 원문·답변–근거 일치’는 플랫폼이 요청·응답 기록을 제공해야 남길 수 있음 · A·B 저장 설계는 부록 B");
  notes(s, "08 검증 대상 — 원문 근거 vs 판단 실행 기록", {
    purpose: "'근거를 보여준다'를 두 층으로 나눈다. A(PDF 안의 근거)만으로는 오답 원인을 찾을 수 없고, B(실행 기록)가 있어야 한다는 점을 정의한다.",
    status: "설계안 (QueryLogger 포매터만 구현, trace 저장 구조는 미구현)",
    rebuttal: "“AI가 왜 그렇게 생각했는지 설명할 수 있나?” → 아니다. LLM 내부 추론은 설명 대상이 아니다. 기록 가능한 검색 경로·적용 규칙·근거와 최종 응답의 일치만 검증한다.",
  }, "여기서 중요한 구분을 하나 하겠습니다. 원문 근거와 AI의 판단 과정은 다릅니다. 왼쪽 A는 PDF 안에 있는 것입니다. 문서 ID, 페이지, 조항, 원문 문장, 그리고 거기서 뽑은 조건과 적용 범위입니다. 오른쪽 B는 PDF에 없습니다. 고객 질문 하나가 들어올 때마다 실행하면서 남겨야 하는 기록입니다. 질문을 어떻게 해석했는지, 어떤 카드와 조건을 찾았는지, 어떤 그래프 관계를 썼는지, 어떤 제외 규칙을 적용해 어떤 판정을 냈는지, 그리고 최종 답변이 그 근거와 일치하는지입니다. 둘을 evidence id와 trace id로 연결해야, 틀린 답이 나왔을 때 어디서 틀렸는지 찾을 수 있습니다. 한 가지 분명히 할 것은, 그래프 경로를 보여주는 것이 LLM의 내부 사고 과정을 설명하는 것은 아니라는 점입니다. 저희가 검증하는 것은 기록할 수 있는 경로와 규칙, 근거입니다. 쿼리 로그 포매터는 구현돼 있고, trace 저장 구조는 설계 단계입니다. 그리고 외부 AI를 거친 질문이라면, 고객의 질문 원문과 최종 답변은 플랫폼이 기록을 넘겨줄 때만 남길 수 있습니다.");
}

// ---- 11 demo 1 ----
{
  const s = content("09   핵심 시연 ①  판단 과정과 원문 근거", "답만이 아니라, 판단 경로와 원문 조항을 함께 돌려줍니다", "제안 구조와 시연");
  pills(s, ["원문 확인", "시연 예상 화면"]);
  boxT(s, "Q.  ONE PICK STYLE 카드로 대중교통 혜택을 받으려면 전월실적이 얼마나 필요한가요?", { x: L, y: 1.78, w: CW, h: 0.5, fill: { color: AMBER_T }, line: { color: AMBER_T }, color: AMBER_D, fontSize: 16, bold: true, align: "left", margin: 14 });
  const steps = ["질문", "해석", "조건 조회", "관계 경로", "원문 근거", "판단 결과"];
  const sw = 1.78, sg = (CW - sw * 6) / 5;
  steps.forEach((t, i) => {
    const x = L + i * (sw + sg);
    chip(s, (i + 1) + " " + t, x, 2.4, sw, 0.34, i === 5 ? INK : SLATE_T, i === 5 ? "FFFFFF" : INK, { fontSize: 12 });
    if (i < 5) arrow(s, x + sw + 0.03, 2.57, sg - 0.06, 0);
  });
  // graph
  const gy = 3.35;
  node(s, "ONE PICK\nSTYLE", "card", L, gy, 1.05, 0.8);
  node(s, "ONE MORE 대중교통\n버스·지하철 5% 캐시백\n월 최대 1천원", "benefit", 2.45, gy - 0.1, 1.9, 1.0, { fontSize: 11 });
  node(s, "지난달 국내외\n일시불 10만원", "cond", 5.05, gy - 0.05, 1.55, 0.9, { fontSize: 12 });
  node(s, "상품권·공과금 등\n(실적 제외)", "item", 7.0, 2.98, 1.6, 0.62, { fontSize: 11 });
  arrow(s, L + 1.07, gy + 0.4, 2.45 - L - 1.11, 0, SLATE);
  edge(s, "HAS_BENEFIT", L + 1.06, gy + 0.13, 0.8, { fontSize: 8, align: "center" });
  arrow(s, 4.37, gy + 0.4, 0.66, 0, SLATE);
  edge(s, "REQUIRES", 4.36, gy + 0.13, 0.68, { fontSize: 8, align: "center" });
  arrow(s, 6.62, gy + 0.2, 0.36, -0.24, SLATE);
  edge(s, "EXCLUDES{실적}", 7.0, gy + 0.3, 1.6, { align: "center" });
  // second row
  const g2 = 4.75;
  node(s, "시외·고속버스·철도\n(혜택 제외)", "item", 2.45, g2, 1.9, 0.62, { fontSize: 11 });
  arrow(s, 3.4, gy + 0.92, 0, g2 - gy - 0.95, SLATE);
  edge(s, "EXCLUDES{혜택}", 3.47, gy + 1.0, 1.4);
  boxT(s, "예외 (실적 무관)\n최초 사용 등록일~\n다음 달 말일", { x: 5.05, y: g2, w: 1.55, h: 0.62, fill: { color: AMBER_T }, line: { color: AMBER, width: 1.25, dashType: "dash" }, color: AMBER_D, fontSize: 9, bold: true, margin: 2 });
  arrow(s, 5.825, gy + 0.87, 0, g2 - gy - 0.9, AMBER_D);
  edge(s, "EXCEPT", 5.89, gy + 1.0, 0.7, { color: AMBER_D });
  node(s, "ONE PICK·STYLE 영역\n실적 조건 없음", "grey", 7.0, g2, 1.6, 0.62, { fontSize: 10, line: { color: "A0AAB8", width: 1, dashType: "dash" } });
  T(s, "경로 밖", { x: 7.0, y: g2 - 0.27, w: 1.6, h: 0.24, fontSize: 9, color: MUTED, align: "center" });
  boxT(s, [
    { text: "SOURCED_FROM → 15650_20260429 1쪽", options: { bold: true, fontFace: MONO, breakLine: true } },
    { text: "ONE MORE 표 · 실적 산정 기준 · 실적 제외 대상 · 실적과 관계없이 서비스 제공 · 서비스 제외 대상", options: {} },
  ], { x: L, y: 5.6, w: 8.0, h: 0.75, fill: { color: VIO }, line: { color: VIO }, color: "FFFFFF", fontSize: 11, align: "left", margin: 10 });
  // result card
  const rx = 8.95, rw = R - rx;
  rect(s, { x: rx, y: 2.98, w: rw, h: 3.37, fill: { color: "FFFFFF" }, line: { color: INK, width: 1.25 } });
  T(s, "판단 결과 (예상 화면)", { x: rx + 0.2, y: 3.08, w: rw - 0.4, h: 0.3, fontSize: 13, bold: true, color: INK });
  T(s, [
    { text: "조건  ", options: { bold: true, color: TEAL_D } }, { text: "지난달 국내외 일시불 10만원 이상", options: { breakLine: true } },
    { text: "범위  ", options: { bold: true, color: TEAL_D } }, { text: "ONE MORE 대중교통에만 적용 (카드 전체 조건 아님)", options: { breakLine: true } },
    { text: "제외  ", options: { bold: true, color: TEAL_D } }, { text: "상품권 등은 실적 미산입, 시외·고속버스·철도는 캐시백 제외", options: { breakLine: true } },
    { text: "예외  ", options: { bold: true, color: TEAL_D } }, { text: "최초 사용 등록일~다음 달 말일은 10만원 미만도 제공", options: {} },
  ], { x: rx + 0.2, y: 3.42, w: rw - 0.4, h: 1.95, fontSize: 11, color: TXT, paraSpaceAfter: 4 });
  boxT(s, [{ text: "판단 불가 예  ", options: { bold: true } }, { text: "“이번 달 받나요?” + 지난달 실적·등록일 정보 없음 → 필요 정보 요청", options: {} }], { x: rx + 0.15, y: 5.2, w: rw - 0.3, h: 0.95, fill: { color: SLATE_T }, line: { color: SLATE_T }, color: SLATE, fontSize: 11, align: "left", margin: 8 });
  footer(s, "판정 값은 STYLE 상품설명서 원문으로 확인 · 그래프·응답 화면은 시연 예상 화면(M7-①③ 미구현) · 등록 가맹점·업종 기준은 PDF 밖 정보");
  notes(s, "09 핵심 시연 ① — 판단 과정과 원문 근거", {
    purpose: "담당자 질문 1~4(카드·혜택 / 조건 / 적용 범위 / 근거 조항)에 한 화면으로 답하는 모습을 보인다.",
    status: "원문 확인(판정 값) · 시연 예상 화면(그래프·응답 미구현)",
    rebuttal: "“이 정도는 원문 PDF를 직접 읽어도 되지 않나?” → 사람은 가능하지만 AI 답변마다 매번 할 수 없다. 핵심은 같은 구조가 모든 답에 기록으로 남는 것이다. “등록일 예외까지 그래프로 표현하나?” → EXCEPT 관계로 설계했지만 추출 품질은 검증 예정이다.",
  }, "첫 번째 핵심 시연입니다. 질문은 ONE PICK STYLE로 대중교통 혜택을 받으려면 전월실적이 얼마나 필요한가입니다. 엔진은 질문을 해석하고, 조건을 조회하고, 관계 경로를 따라 원문 근거까지 간 뒤 판단 결과를 냅니다. 그래프를 보시면 STYLE 카드에서 ONE MORE 대중교통 혜택, 버스·지하철 5% 캐시백 월 최대 1천원으로 가고, 이 혜택이 요구하는 조건이 지난달 국내외 일시불 10만원입니다. 이 조건은 상품권, 공과금 등을 실적에서 제외합니다. 혜택 자체에서는 시외버스, 고속버스, 철도가 제외됩니다. 그리고 최초 사용 등록일부터 다음 달 말일까지는 실적과 관계없이 제공하는 예외가 있습니다. ONE PICK·STYLE 영역은 실적 조건이 없어서 이 경로 밖에 있습니다. 이 모든 노드는 STYLE 상품설명서 1쪽의 다섯 군데 조항을 가리킵니다. 오른쪽 결과 카드는 조건, 범위, 제외, 예외를 함께 보여주고, 지난달 실적이나 등록일 정보 없이 이번 달 받느냐고 물으면 추측하지 않고 필요한 정보를 요청합니다. 판정 값은 원문으로 확인했고, 화면은 구현 후 시연할 예상 화면입니다.");
}

// ---- 12 demo 2 error trace ----
{
  const s = content("10   핵심 시연 ②  오답 원인 추적", "AI가 틀렸을 때, 어느 단계에서 틀렸는지 찾아 고치고 다시 확인합니다", "제안 구조와 시연");
  pills(s, ["가상 시나리오", "검증 예정"]);
  boxT(s, "가상 오류 시나리오 — 실제 실행 로그 재현이 아닙니다 (구현 후 실제 로그로 교체)", { x: L, y: 1.78, w: CW, h: 0.42, fill: { color: RED_T }, line: { color: RED, width: 1 }, color: RED_D, fontSize: 14, bold: true, align: "left", margin: 12 });
  const y1 = 2.35, h1 = 1.15;
  boxT(s, [{ text: "원래 질문 (1장)", options: { bold: true, color: MUTED, fontSize: 11, breakLine: true } }, { text: "상품권 8만원 + 버스비 2만원, 대중교통 캐시백 받나요?", options: { color: INK } }], { x: L, y: y1, w: 3.3, h: h1, fill: { color: MIST }, fontSize: 13, align: "left", margin: 10 });
  arrow(s, L + 3.32, y1 + h1 / 2, 0.26, 0);
  boxT(s, [{ text: "AI 오답", options: { bold: true, color: AMBER, fontSize: 11, breakLine: true } }, { text: "“네, 10만원을 채워 5% 캐시백”", options: { color: "FFFFFF" } }], { x: 4.2, y: y1, w: 2.75, h: h1, fill: { color: INK2 }, line: { color: INK2 }, fontSize: 13, align: "left", margin: 10 });
  arrow(s, 6.97, y1 + h1 / 2, 0.26, 0);
  const cw2 = (R - 7.25 - 0.15) / 2;
  boxT(s, [{ text: "잘못 적용된 조건", options: { bold: true, color: RED_D, fontSize: 12, breakLine: true } }, { text: "상품권 → ‘혜택 제외’에만 연결, ‘실적 제외’ 누락 → 10만원 충족으로 오판", options: { color: TXT } }], { x: 7.25, y: y1, w: cw2, h: h1, fill: { color: RED_T }, line: { color: RED_T }, fontSize: 12, align: "left", margin: 9 });
  boxT(s, [{ text: "실제 약관 조건", options: { bold: true, color: TEAL_D, fontSize: 12, breakLine: true } }, { text: "상품권은 실적 제외이면서 서비스 제외 → 인정 실적 최대 2만원", options: { color: TXT } }], { x: 7.25 + cw2 + 0.15, y: y1, w: cw2, h: h1, fill: { color: TEAL_T }, line: { color: TEAL_T }, fontSize: 12, align: "left", margin: 9 });

  T(s, "오류 위치 추적 — 판단 실행 기록(trace)과 단계별 산출물을 원문과 대조", { x: L, y: 3.7, w: CW, h: 0.3, fontSize: 14, bold: true, color: INK });
  const st = ["① PDF 추출", "② 조건·적용 범위 추출", "③ 관계 정규화", "④ 검색 (그래프 조회)", "⑤ LLM 답변 생성"];
  const tag = ["원문 문장 있음", "오류 지점: scope 누락", "②의 오류가 전파", "잘못된 관계를 그대로 조회", "다른 유형: 근거를 무시한 답변"];
  const bw = 2.2, bg = (CW - bw * 5) / 4;
  st.forEach((t, i) => {
    const x = L + i * (bw + bg);
    const err = i === 1, alt = i === 4;
    boxT(s, t, { x, y: 4.08, w: bw, h: 0.72, fill: { color: err ? RED_T : MIST }, line: err ? { color: RED, width: 2.5 } : alt ? { color: AMBER, width: 1.25, dashType: "dash" } : { color: MIST }, color: err ? RED_D : INK, fontSize: 13, bold: true, margin: 4 });
    T(s, tag[i], { x, y: 4.86, w: bw, h: 0.42, fontSize: 10, bold: err || alt, color: err ? RED_D : alt ? AMBER_D : MUTED, align: "center" });
    if (i < 4) arrow(s, x + bw + 0.02, 4.44, bg - 0.04, 0);
  });
  const fx = ["수정: 상품권에 실적 제외 관계(scope) 보정", "재적재", "같은 질문 재검증", "판정: 미적용 (등록일 예외 확인 필요)"];
  const fw = [3.6, 1.6, 2.3, 3.73], fg = (CW - fw.reduce((a, b) => a + b, 0)) / 3;
  let fxx = L;
  fx.forEach((t, i) => {
    const last = i === 3;
    chip(s, t, fxx, 5.42, fw[i], 0.5, last ? TEAL : AMBER_T, last ? "FFFFFF" : AMBER_D, { fontSize: 12 });
    if (i < 3) arrow(s, fxx + fw[i] + 0.02, 5.67, fg - 0.04, 0);
    fxx += fw[i] + fg;
  });
  boxT(s, "목표는 ‘전부 맞힌다’가 아니라 ‘틀린 지점을 찾을 수 있다’입니다. 고치지 못한 항목은 판단 보류로 공개합니다.", { x: L, y: 6.12, w: CW, h: 0.72, fill: { color: INK }, line: { color: INK }, color: "FFFFFF", fontSize: 15, bold: true, align: "left", margin: 14 });
  footer(s, "시나리오는 STYLE 원문에서 확인한 함정(상품권이 실적 제외·서비스 제외에 모두 등장)으로 구성 · 단계 구분은 M1·M3~M5·M7·M8 · 오류 6분류는 부록 D");
  notes(s, "10 핵심 시연 ② — 오답 원인 추적", {
    purpose: "담당자 질문 5(어느 단계에서 틀렸나)에 답한다. 1장의 오답을 그대로 가져와 원인 위치 → 수정 → 재검증 루프를 보인다.",
    status: "가상 시나리오 · 검증 예정 (실제 LLM 실행 로그 아님)",
    rebuttal: "“오류를 일부러 만든 것 아닌가?” → 맞다. 가상 시나리오라고 슬라이드에 명시했다. 다만 원문에서 실제로 확인한 함정이며, 구현 후 실제 로그로 교체한다. “⑤ 단계 오류는 어떻게 잡나?” → 판단 실행 기록의 '답변–근거 일치 여부'로 탐지하는 것이 설계 목표이며 아직 검증 전이다.",
  }, "두 번째 핵심 시연은 오답 원인 추적입니다. 먼저 분명히 하면, 이것은 가상 오류 시나리오이고 실제 실행 로그를 재현한 것이 아닙니다. 1장의 질문을 다시 가져왔습니다. AI는 10만원을 채웠다고 답했는데, 원인은 상품권을 혜택 제외에만 연결하고 실적 제외에는 연결하지 않은 데 있습니다. 실제 약관에서 상품권은 둘 다에 해당합니다. 판단 실행 기록과 단계별 산출물을 원문과 대조하면 다섯 단계 중 어디서 틀렸는지 찾을 수 있습니다. PDF 추출 단계에는 원문 문장이 있었고, 조건과 적용 범위를 추출하는 두 번째 단계에서 scope가 빠졌습니다. 이 오류가 정규화와 검색으로 그대로 전파된 것입니다. 다섯 번째처럼 근거는 맞게 찾았는데 LLM이 답변에서 무시하는 다른 유형도 있습니다. 원인을 찾으면 관계를 보정하고, 다시 적재하고, 같은 질문으로 재검증합니다. 이번에는 미적용, 단 등록일 예외는 확인이 필요하다는 판정이 나와야 합니다. 목표는 전부 맞히는 것이 아니라 틀린 지점을 찾을 수 있는 것입니다.");
}

// ---- 13 demo 3 change impact ----
{
  const s = content("11   핵심 시연 ③  조건 변경 영향", "조건 하나가 바뀌면, 다시 검토할 혜택이 경로로 드러납니다", "제안 구조와 시연");
  pills(s, ["원문 확인", "시연 예정"]);
  boxT(s, "가정:  ‘상품권·기프트카드 구매’를 전월실적 산정에 포함하도록 조항이 바뀐다면?", { x: L, y: 1.8, w: CW, h: 0.55, fill: { color: AMBER_T }, line: { color: AMBER_T }, color: AMBER_D, fontSize: 16, bold: true, align: "left", margin: 14 });
  T(s, "검토 후보 — 4종 · 혜택 7개", { x: L, y: 2.5, w: 4.2, h: 0.32, fontSize: 14, bold: true, color: TEAL_D });
  const left = [
    ["ONE PICK STYLE", "ONE MORE 대중교통(10만) · 놀이공원(20만)"],
    ["ONE PICK PLAY", "ONE MORE 대중교통(10만) · 놀이공원(20만)"],
    ["BT", "인천공항 라운지(50만)"],
    ["에너지 더블", "에너지 공과금(40/80만) · 일상생활(40만)"],
  ];
  const ly = [2.88, 3.56, 4.24, 4.92];
  left.forEach((r, i) => {
    boxT(s, [{ text: r[0], options: { bold: true, color: INK, fontSize: 13, breakLine: true } }, { text: r[1], options: { color: TEAL_D, fontSize: 12 } }], { x: L, y: ly[i], w: 4.05, h: 0.6, fill: { color: TEAL_T }, line: { color: TEAL, width: 1 }, align: "left", margin: 8 });
    line(s, 4.65, ly[i] + 0.3, 0.3, 0, TEAL);
  });
  line(s, 4.95, ly[0] + 0.3, 0, ly[3] - ly[0], TEAL);
  arrow(s, 4.95, 4.12, 0.33, 0, TEAL);
  T(s, "REQUIRES → EXCLUDES {scope: 실적}", { x: 4.7, y: 2.53, w: 3.6, h: 0.28, fontSize: 10, color: TEAL_D, bold: true, fontFace: MONO });
  node(s, "상품권·\n기프트카드 구매\n(실적 제외 항목)", "item", 5.3, 3.37, 2.35, 1.5, { fontSize: 14 });
  T(s, "같은 단어, 다른 범위 — 별도 표시", { x: 8.45, y: 2.5, w: 4.28, h: 0.32, fontSize: 14, bold: true, color: SLATE });
  const right = ["BT · BIG TICKET 할인 제외", "에너지 더블 · 대형마트 할인 제외", "STYLE·PLAY · 서비스 공통 제외"];
  const ry = [2.88, 3.56, 4.24];
  right.forEach((t, i) => {
    boxT(s, t, { x: 8.45, y: ry[i], w: 4.28, h: 0.6, fill: { color: MIST }, color: SLATE, fontSize: 13, align: "left", margin: 10 });
    line(s, 8.1, ry[i] + 0.3, 0.35, 0, "A0AAB8", { line: { color: "A0AAB8", width: 1.25, dashType: "dash" } });
  });
  line(s, 8.1, ry[0] + 0.3, 0, ry[2] - ry[0], "A0AAB8", { line: { color: "A0AAB8", width: 1.25, dashType: "dash" } });
  line(s, 7.65, 4.12, 0.45, 0, "A0AAB8", { line: { color: "A0AAB8", width: 1.25, dashType: "dash" } });
  T(s, "scope:\n혜택", { x: 7.72, y: 3.55, w: 0.4, h: 0.5, fontSize: 9, color: MUTED });
  boxT(s, "영향 없음: ONE PICK·STYLE/PLAY 영역, BIG TICKET (지난달 실적 조건 없음)", { x: 8.45, y: 4.92, w: 4.28, h: 0.6, fill: { color: "FFFFFF" }, line: { color: "A0AAB8", width: 1, dashType: "dash" }, color: MUTED, fontSize: 12, align: "left", margin: 10 });
  boxT(s, [
    { text: "‘상품권’ 검색 → ", options: { color: DARK_SUB } },
    { text: "상품권 문구 전부", options: { color: "FFFFFF", bold: true } },
    { text: "      그래프 경로 → ", options: { color: DARK_SUB } },
    { text: "실적 조건에 걸린 7개 혜택 + 범위 다른 조항 분리", options: { color: AMBER, bold: true } },
  ], { x: L, y: 5.75, w: CW, h: 0.7, fill: { color: INK }, line: { color: INK }, fontSize: 15, align: "left", margin: 14 });
  T(s, "결과는 자동 정책 변경이나 법적 효력 판정이 아니라, 사람이 확인할 검토 후보 목록입니다.", { x: L, y: 6.53, w: CW, h: 0.32, fontSize: 12, bold: true, color: RED_D });
  footer(s, "4종 원문 수작업 검토로 도출한 기대 결과 · 약 10종 확대 시 재검토 · Cypher·MCP 미실행");
  notes(s, "11 핵심 시연 ③ — 조건 변경 영향", {
    purpose: "담당자 질문 6(조건이 바뀌면 무엇을 다시 보나)에 답한다. 판단 근거 그래프가 있으면 변경 영향도 같은 경로로 찾을 수 있음을 보인다.",
    status: "원문 확인(기대 결과 수작업 도출) · 시연 예정(Cypher·MCP 미실행)",
    rebuttal: "“검색으로도 상품권 문구는 다 찾는다” → 찾지만 범위를 구분하지 못해 영향 없는 혜택까지 끌려온다. “이 목록대로 정책을 바꾸나?” → 아니다. 사람이 확인할 검토 후보다.",
  }, "세 번째 핵심 시연은 조건 변경 영향입니다. 상품권 구매를 전월실적에 포함하도록 조항이 바뀐다고 가정합니다. 단순히 ‘상품권’을 검색하면 4종의 모든 상품권 문구가 다 나옵니다. 그래프는 카드에서 혜택, 혜택이 요구하는 실적 조건, 그 조건이 제외하는 항목까지 경로를 따라갑니다. 그래서 실적 조건에 연결된 7개 혜택만 검토 후보로 나오고, BIG TICKET 할인 제외처럼 같은 단어지만 범위가 다른 조항은 따로 표시됩니다. 시연 ①에서 판단 근거로 쓰던 바로 그 관계가 변경 영향 분석에도 그대로 쓰입니다. 이 목록은 4종 원문을 손으로 검토해 도출한 기대 결과이고, 같은 결과를 Cypher와 MCP로 재현하는 것이 시연 목표입니다. 그리고 이것은 자동 정책 변경이나 법적 효력 판단이 아니라 사람이 확인할 검토 후보입니다.");
}

// ---- 14 MCP ----
{
  const s = content("12   MCP 연동", "검증된 판단을 다른 AI에도: MCP는 판단 로직이 아닌 연결 어댑터입니다", "제안 구조와 시연");
  pills(s, ["설계안", "시연 예정"]);
  T(s, "같은 질문 · 두 경로 · 결과 일치 여부 검증", { x: L, y: 1.85, w: 6.3, h: 0.32, fontSize: 14, bold: true, color: INK });
  const bw = 1.9, ag = 0.25;
  const rowsA = [["Neo4j Browser", "Cypher 쿼리\n(M7-②)", "결과 A"], ["로컬 MCP\n클라이언트", "MCP 서버 →\n같은 쿼리 함수", "결과 B"]];
  rowsA.forEach((r, i) => {
    const y = 2.3 + i * 0.88;
    r.forEach((t, j) => {
      const x = L + j * (bw + ag);
      const fill = j === 2 ? TEAL_T : (i === 1 && j === 1 ? "FFFFFF" : MIST);
      const ln = i === 1 && j === 1 ? { color: AMBER, width: 1.5 } : { color: fill };
      boxT(s, t, { x, y, w: bw, h: 0.72, fill: { color: fill }, line: ln, color: j === 2 ? TEAL_D : INK, fontSize: 13, bold: true, margin: 3 });
      if (j < 2) arrow(s, x + bw + 0.02, y + 0.36, ag - 0.04, 0);
    });
  });
  boxT(s, [{ text: "결과 A = 결과 B ?  ", options: { bold: true, color: TEAL_D } }, { text: "구조화 응답·근거 일치 검증 · 최종 자연어 답변의 정확성은 별도 평가", options: { color: TXT } }], { x: L, y: 4.12, w: 6.2, h: 0.6, fill: { color: "FFFFFF" }, line: { color: TEAL, width: 1.25 }, fontSize: 13, align: "left", margin: 10 });
  const tb = [
    [{ text: "MCP 도구(안)", options: { bold: true, color: "FFFFFF", fill: { color: SLATE } } }, { text: "내부 동작", options: { bold: true, color: "FFFFFF", fill: { color: SLATE } } }, { text: "우선순위", options: { bold: true, color: "FFFFFF", fill: { color: SLATE } } }],
    ["get_card_benefits(card)", "M7-① 혜택·조건·근거", { text: "필수", options: { bold: true, color: TEAL_D } }],
    ["find_affected_by_condition(condition)", "M7-② 영향 추적", { text: "가능하면", options: { bold: true, color: AMBER_D } }],
    ["explain_judgment(card, benefit)", "M7-③ 판단 경로", { text: "후속", options: { color: MUTED } }],
  ];
  s.addTable(tb, { x: L, y: 4.95, w: 6.2, colW: [3.4, 1.85, 0.95], rowH: 0.38, fontFace: F, fontSize: 11, color: TXT, border: tblBorder, valign: "middle", margin: [2, 5, 2, 5] });

  const rx = 7.2, rw = R - 7.2;
  rect(s, { x: rx, y: 1.85, w: rw, h: 2.15, fill: { color: TEAL_T }, line: { color: TEAL_T } });
  T(s, [
    { text: "MCP가 하는 일", options: { bold: true, color: TEAL_D, fontSize: 15, breakLine: true } },
    { text: "기존 조회 함수를 AI 클라이언트에 연결", options: { bullet: true, breakLine: true } },
    { text: "판정 로직을 따로 만들지 않는 얇은 어댑터", options: { bullet: true, breakLine: true } },
    { text: "반환값에 근거 조항·trace id 포함 (설계)", options: { bullet: true, breakLine: true } },
    { text: "자사 AI는 MCP 없이 내부 API를 직접 써도 됩니다", options: { bullet: true } },
  ], { x: rx + 0.22, y: 1.95, w: rw - 0.4, h: 1.98, fontSize: 14, color: TXT, paraSpaceAfter: 4 });
  rect(s, { x: rx, y: 4.12, w: rw, h: 1.34, fill: { color: "FFFFFF" }, line: { color: AMBER, width: 1.25 } });
  T(s, [
    { text: "외부 AI 경유 시 카드사가 확인할 수 있는 범위", options: { bold: true, color: INK, fontSize: 14, breakLine: true } },
    { text: "기록 가능  ", options: { bold: true, color: TEAL_D } }, { text: "MCP로 공급한 조건·근거·trace id (카드사 측 로그)", options: { breakLine: true } },
    { text: "조건부  ", options: { bold: true, color: AMBER_D } }, { text: "최종 답변–근거 대조 — 플랫폼이 응답 기록을 줄 때만", options: { breakLine: true } },
    { text: "보장 불가  ", options: { bold: true, color: RED_D } }, { text: "호출 여부 · 요약·변형 · 브랜드 문구 표시", options: {} },
  ], { x: rx + 0.22, y: 4.2, w: rw - 0.4, h: 1.2, fontSize: 12, color: TXT, paraSpaceAfter: 4 });
  rect(s, { x: rx, y: 5.62, w: rw, h: 0.9, fill: { color: MIST }, line: { color: MIST } });
  T(s, [
    { text: "시연 범위: ", options: { bold: true, color: INK } },
    { text: "로컬 MCP 클라이언트까지 (외부 플랫폼 실연동 제외)", options: { breakLine: true } },
    { text: "컷라인: ", options: { bold: true, color: INK } },
    { text: "3일차 오전까지 M8 미완료 시 get_card_benefits만 구현", options: {} },
  ], { x: rx + 0.22, y: 5.69, w: rw - 0.4, h: 0.78, fontSize: 12, color: SLATE, lineSpacingMultiple: 1.1 });
  footer(s, "업계 사례: 신한카드, 카카오 PlayMCP 기반 ‘카카오 툴즈’ 연동 발표(2026-09-13) — 연결 방식의 실사례일 뿐, 우리 구현과의 동등성 근거는 아닙니다");
  notes(s, "12 MCP — 검증된 판단의 재사용", {
    purpose: "확장③. 1장(외부 AI도 같은 근거를 받아야 함)과 3장(신한의 MCP 연결 사례)을 회수한다. 판단 로직은 엔진 하나에 두고 MCP는 연결만 하며, 카드사가 확인할 수 있는 범위가 플랫폼에 따라 달라진다는 점을 분명히 한다.",
    status: "설계안 · 시연 예정 (MCP 미구현, 외부 플랫폼 연동은 범위 밖)",
    rebuttal: "“MCP로 외부 AI 답을 통제하나?” → 아니다. 구조화된 조건·근거를 공급할 뿐, 호출 여부·요약·문구 노출은 외부 AI가 결정한다. “trace id가 있으면 외부 AI 답변도 다 추적되나?” → 아니다. 카드사가 공급한 내용은 항상 기록되지만, 최종 답변과의 대조는 플랫폼이 응답 기록을 줄 때만 가능하다.",
  }, "1장에서 고객이 외부 AI에게 물어도 같은 근거가 나가야 한다고 말씀드렸고, 3장에서 신한카드가 MCP로 외부 AI에 연결한 사례를 봤습니다. 저희 구조에서 MCP는 판단을 하지 않습니다. 이미 검증한 조회 함수를 다른 AI 클라이언트가 호출할 수 있게 연결할 뿐입니다. 반환값에는 근거 조항과 trace id를 함께 담도록 설계했습니다. 그러면 카드사는 어떤 요청에 어떤 조건과 근거를 공급했는지는 항상 기록할 수 있습니다. 하지만 외부 AI가 그것을 받아 고객에게 최종적으로 뭐라고 답했는지는 다릅니다. 플랫폼이 응답 기록을 제공할 때만 근거와 대조할 수 있고, 그렇지 않으면 저희가 검증할 수 있는 범위는 공급한 내용까지입니다. 시연은 같은 질문을 Neo4j Browser의 Cypher와 로컬 MCP 클라이언트로 각각 실행해 구조화된 결과와 근거가 같은지 확인하는 것입니다. 외부 AI가 그 결과를 어떻게 요약하는지는 따로 평가해야 하고, 카카오 같은 외부 플랫폼 연동은 범위 밖입니다. 일정이 밀리면 도구는 get_card_benefits 하나만 남깁니다.");
}

pres.addSection({ title: "가치와 결론" });

// ---- 15 value ----
{
  const s = content("13   카드사 도입 가치", "AI 안내를 확인하고, 설명하고, 고칠 수 있는 기반", "가치와 결론");
  pills(s, ["팀 가설", "확장 제안"]);
  T(s, "담당자 상황별 가치", { x: L, y: 1.85, w: 7.5, h: 0.32, fontSize: 15, bold: true, color: INK });
  const rows = [
    ["고객 문의\n“AI가 된다고 했어요”", "판단 실행 기록·근거 경로로 적용 조건과 오류 위치 확인 (외부 AI는 응답 기록 확보 시)", TEAL],
    ["약관·상품 조건 변경", "다시 검토할 카드·혜택·판단 결과를 검토 후보 목록으로 산출", AMBER],
    ["새 AI 채널 추가", "판단 로직을 다시 만들지 않고 같은 엔진을 호출 (내부 API·MCP)", SLATE],
    ["고지 문구 점검", "고객에게 고지된 원문과 AI 안내 내용이 일치하는지 점검", VIO],
  ];
  rows.forEach((r, i) => {
    const y = 2.28 + i * 0.84;
    boxT(s, r[0], { x: L, y, w: 2.55, h: 0.72, fill: { color: r[2] }, line: { color: r[2] }, color: r[2] === AMBER ? INK : "FFFFFF", fontSize: 13, bold: true, align: "left", margin: 10 });
    arrow(s, L + 2.58, y + 0.36, 0.3, 0);
    boxT(s, r[1], { x: L + 2.95, y, w: 4.75, h: 0.72, fill: { color: MIST }, color: TXT, fontSize: 13, align: "left", margin: 10 });
  });
  const rx = 8.6, rw = R - rx;
  rect(s, { x: rx, y: 1.85, w: rw, h: 3.81, fill: { color: VIO_T }, line: { color: VIO_T } });
  T(s, [
    { text: "보조 · 확장 제안", options: { bold: true, color: VIO, fontSize: 14, breakLine: true } },
    { text: "마케팅·피드백 계층", options: { bold: true, color: INK, fontSize: 13, breakLine: true } },
    { text: "카드사 승인 문구 관리", options: { bullet: true, breakLine: true } },
    { text: "혜택–광고 문구 정합성 점검", options: { bullet: true, breakLine: true } },
    { text: "조건 변경 시 재검토할 문구 식별", options: { bullet: true, breakLine: true } },
    { text: "질문·오답·검토 피드백 개선 루프", options: { bullet: true } },
  ], { x: rx + 0.2, y: 2.0, w: rw - 0.4, h: 3.55, fontSize: 13, color: TXT, paraSpaceAfter: 8 });
  boxT(s, [
    { text: "객관성 원칙  ", options: { bold: true, color: RED_D } },
    { text: "광고·마케팅 데이터는 판단 입력과 분리합니다. 마케팅 출력은 GraphRAG의 차별성이 아닙니다.", options: { color: TXT } },
  ], { x: L, y: 5.85, w: CW, h: 0.72, fill: { color: RED_T }, line: { color: RED_T }, fontSize: 14, align: "left", margin: 14 });
  T(s, "기대 효과는 실측 전인 팀 가설입니다 — 처리 시간 단축 등 수치는 주장하지 않습니다.", { x: L, y: 6.63, w: CW, h: 0.3, fontSize: 11, color: MUTED });
  footer(s, "자사 AI vs 외부 AI 통제권 비교는 부록 E · 마케팅 계층: 최종_카드사_자체AI혜택서비스_사업적개발명분_20261029.md (팀 가설, 미구현)");
  notes(s, "13 카드사 도입 가치", {
    purpose: "도입 명분을 '담당자가 실제로 겪는 상황' 4개로 바꿔 말한다. 마케팅은 보조 확장으로 낮춘다.",
    status: "팀 가설 · 확장 제안 (효과 실측 전)",
    rebuttal: "“효과가 얼마나 되나?” → 측정하지 않았다. 수치를 주장하지 않고, 어떤 상황에서 무엇을 확인할 수 있게 되는지만 말한다.",
  }, "카드사 입장에서 이 기반이 왜 필요한지, 담당자가 실제로 겪는 상황으로 말씀드리겠습니다. 첫째, 고객이 AI가 된다고 했다며 문의할 때입니다. 판단 실행 기록과 근거 경로가 있으면 AI가 어떤 조건을 적용했고 어디서 틀렸는지 확인할 수 있습니다. 외부 AI를 통한 문의라면, 플랫폼에서 응답 기록을 받을 수 있는 경우에 한해 최종 답변까지 대조할 수 있습니다. 둘째, 약관이나 상품 조건이 바뀔 때 다시 볼 카드와 혜택, 판단 결과를 검토 후보로 받을 수 있습니다. 셋째, 새 AI 채널을 붙일 때 판단 로직을 다시 만들지 않고 같은 엔진을 호출합니다. 넷째, 고객에게 고지된 원문과 AI 안내가 일치하는지 점검할 수 있습니다. 오른쪽의 마케팅·피드백 계층은 보조적인 확장 제안입니다. 다만 원칙이 있습니다. 광고 데이터는 판단에 들어가지 않고, 마케팅 출력은 GraphRAG의 차별성이 아닙니다. 이 효과들은 아직 측정하지 않은 팀 가설입니다.");
}

// ---- 16 conclusion ----
{
  const s = pres.addSlide({ masterName: "DARK", sectionTitle: "가치와 결론" });
  T(s, "결론", { x: 0.7, y: 0.6, w: 3, h: 0.32, fontSize: 13, bold: true, color: AMBER });
  T(s, "AI가 카드 혜택을 판단했다면, 카드사는 그 판단에 사용된\n조건과 공식 약관 근거를 확인할 수 있어야 합니다.", { x: 0.7, y: 1.1, w: 12, h: 1.55, fontSize: 30, bold: true, color: "FFFFFF", lineSpacingMultiple: 1.1 });
  const p = [
    ["핵심", "근거 검증", "적용한 조건·범위·\n원문 조항을 판단마다 기록"],
    ["확장①", "오류 추적", "틀린 답이 생긴 단계를\n찾아 고치고 재검증"],
    ["확장②", "변경 영향", "조건이 바뀌면\n다시 볼 혜택을 경로로 산출"],
    ["확장③", "재사용", "검증된 판단을 여러 AI\n채널이 같은 엔진으로 호출"],
  ];
  const pw = (11.93 - 3 * 0.3) / 4;
  p.forEach((t, i) => {
    const x = 0.7 + i * (pw + 0.3);
    rect(s, { x, y: 3.0, w: pw, h: 1.85, fill: { color: i === 0 ? TEAL_D : INK2 }, line: { color: i === 0 ? TEAL_D : INK2 } });
    T(s, t[0], { x: x + 0.22, y: 3.15, w: pw - 0.44, h: 0.28, fontSize: 12, bold: true, color: i === 0 ? "BFEDE6" : AMBER });
    T(s, t[1], { x: x + 0.22, y: 3.45, w: pw - 0.44, h: 0.45, fontSize: 20, bold: true, color: "FFFFFF", valign: "middle" });
    T(s, t[2], { x: x + 0.22, y: 4.0, w: pw - 0.44, h: 0.75, fontSize: 13, color: "D5DEEA", lineSpacingMultiple: 1.1 });
    if (i < 3) arrow(s, x + pw + 0.03, 3.92, 0.24, 0, AMBER);
  });
  T(s, "판단 근거를 검증하고, 오류 원인을 추적하며, 변경 영향을 확인할 수 있는\n공통 GraphRAG 엔진을 여러 AI 채널에서 재사용합니다.", { x: 0.7, y: 5.15, w: 12, h: 0.9, fontSize: 19, bold: true, color: AMBER, lineSpacingMultiple: 1.1 });
  T(s, "현재: 하나카드 4종 원문 대조·설계  /  목표: 체크·신용 약 10종 · GraphRAG 엔진·MCP는 구현 전", { x: 0.7, y: 6.3, w: 12, h: 0.35, fontSize: 13, color: DARK_SUB });
  notes(s, "결론", {
    purpose: "결론 메시지 두 문장으로 닫고, 현재 범위와 목표 범위를 마지막에 한 번 더 구분한다.",
    status: "—",
    rebuttal: "“결국 아직 아무것도 없지 않나?” → 원문 대조·판단 구조·검증 기준·시연 기대 결과까지 준비했고, 구현은 M1~M9 일정으로 진행한다고 범위를 그대로 말한다.",
  }, "처음 질문으로 돌아가겠습니다. AI가 고객에게 카드 혜택을 잘못 안내했다면, 카드사는 그 이유를 설명할 수 있을까요. 저희의 답은 이것입니다. AI가 카드 혜택을 판단했다면, 카드사는 그 판단에 사용된 조건과 공식 약관 근거를 확인할 수 있어야 합니다. 그것이 핵심인 근거 검증이고, 여기서 오류 추적, 변경 영향, 재사용이 차례로 확장됩니다. 판단 근거를 검증하고, 오류 원인을 추적하며, 변경 영향을 확인할 수 있는 공통 GraphRAG 엔진을 여러 AI 채널에서 재사용하는 것. 현재는 하나카드 4종의 원문 대조와 설계까지이고, 체크·신용 약 10종과 엔진·MCP 구현이 다음 단계입니다. 감사합니다.");
}

// ===================== APPENDIX =====================
pres.addSection({ title: "부록" });

// A — task mapping
{
  const s = content("부록 A   과제 수행 증빙", "M0~M9는 발표의 어느 장면을 만드는가 — 현재 상태 포함", "부록");
  const H = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: INK } } });
  const st = (t, k) => ({ text: t, options: { color: k === "d" ? TEAL_D : k === "p" ? AMBER_D : RED_D, bold: true } });
  const rows = [
    [H("과제"), H("카드 엔진에서 할 일"), H("관련 장(좌상단 번호)"), H("현재 상태 (2026-10-30)")],
    ["M0 주제·문서", "체크·신용 유사 혜택 약 10종 선정 목표; 4종부터 시연", "05, 11", st("4종 원문 대조 완료 / 약 10종 최종 선정·적재는 예정", "p")],
    ["M1 전처리", "텍스트 추출·청크·원문 위치 ID", "04", st("추출 가능성 표본 검증 완료 / 파이프라인 미구현", "p")],
    ["M2 온톨로지", "Card·Benefit·Condition·Merchant·Clause", "07, 부록 B", st("설계안 (과제 매핑표)", "p")],
    ["M3·M4 LLM 추출", "근거 문장·clause_id 필수 JSON, 실패 처리", "04, 10", st("미구현", "x")],
    ["M5 정규화", "정책 단위 병합, 오병합 점검", "04, 10", st("미구현 — 오병합 위험 사례 확인", "x")],
    ["M6 Neo4j 적재", "MERGE 재적재, 근거 속성 보존", "07", st("미구현", "x")],
    ["M7 Cypher", "혜택 조회 · 영향 추적 · 판단 경로", "09, 11", st("미구현 — 기대 결과는 원문으로 도출", "x")],
    ["M8 검증", "원문–트리플–그래프 대조, 오류 6분류", "10, 부록 D", st("미구현 — 기준 정의", "x")],
    ["M9 통합·MCP", "문서 → 그래프 → MCP 한 흐름", "12", st("미구현 — 도구 3안, 컷라인 설정", "x")],
    ["판단 실행 기록", "질의·경로·적용 규칙·판정·버전, evidence/trace id", "08, 10", st("QueryLogger 포매터 구현 / trace 저장 구조 설계안", "p")],
    ["구현 완료", "PostgreSQL 카드 등록·조회 CLI + 단위 테스트", "—", st("완료 (payment_card)", "d")],
  ];
  s.addTable(rows, { x: L, y: 1.8, w: CW, colW: [2.1, 4.0, 1.95, 4.08], rowH: 0.4, fontFace: F, fontSize: 12, color: TXT, border: tblBorder, valign: "middle", margin: [2, 6, 2, 6] });
  footer(s, "출처: 과제_매핑표_10.29.md · README.md · architecture.md · src/common/query_logger.py · sql/hana_card_db_design.md (DB 설계 초안, 미적용)");
  notes(s, "부록 A 과제 수행 증빙", { purpose: "과제 M0~M9와 발표 장면, 현재 상태를 대응시킨다.", status: "현재 상태 그대로 공개", rebuttal: "—" },
    "과제 M0부터 M9까지가 발표의 어느 장면을 만드는지와 현재 상태입니다. 구현 완료는 PostgreSQL 카드 등록·조회 CLI와 쿼리 로그 포매터이고, 판단 실행 기록의 저장 구조와 그래프 엔진, MCP는 아직 미구현입니다.");
}

// B — ontology
{
  const s = content("부록 B   그래프 설계안 (M2)", "카드 → 혜택 → 조건 → 약관 조항, 모든 관계에 근거를 붙입니다", "부록");
  pills(s, ["설계안"]);
  const y1 = 2.25, y2 = 3.85, nh = 0.7, nw = 2.15;
  const xs = [L, 3.75, 6.9, 10.05];
  node(s, "Card\n카드 상품", "card", xs[0], y1, nw, nh);
  node(s, "Benefit\n혜택", "benefit", xs[1], y1, nw, nh);
  node(s, "Condition\n전월실적·한도", "cond", xs[2], y1, nw, nh);
  node(s, "Condition\n제외 항목", "item", xs[3], y1, 2.68, nh);
  ["HAS_BENEFIT", "REQUIRES", "EXCLUDES {scope}"].forEach((t, i) => {
    arrow(s, xs[i] + nw + 0.03, y1 + nh / 2, xs[i + 1] - xs[i] - nw - 0.06, 0, SLATE);
    T(s, t, { x: xs[i] + nw - 0.2, y: y1 - 0.32, w: 1.6, h: 0.26, fontSize: 10, bold: true, color: SLATE, fontFace: MONO, align: "center" });
  });
  node(s, "Copy\n승인 문구 (확장 제안)", "grey", xs[0], y2, nw, nh, { fill: { color: VIO_T }, line: { color: VIO, width: 1.25, dashType: "dash" }, color: VIO });
  node(s, "Condition\n월 한도", "cond", xs[1], y2, nw, nh);
  node(s, "Clause\n약관 조항", "clause", xs[2], y2, nw, nh);
  node(s, "Merchant\n가맹점·업종", "grey", xs[3], y2, 2.68, nh);
  arrow(s, xs[1] + nw / 2, y1 + nh + 0.03, 0, y2 - y1 - nh - 0.06, SLATE);
  T(s, "LIMITED_BY", { x: xs[1] + nw / 2 + 0.08, y: y1 + nh + 0.2, w: 1.3, h: 0.26, fontSize: 10, bold: true, color: SLATE, fontFace: MONO });
  arrow(s, xs[2] + nw / 2, y1 + nh + 0.03, 0, y2 - y1 - nh - 0.06, SLATE);
  T(s, "SOURCED_FROM", { x: xs[2] + nw / 2 + 0.08, y: y1 + nh + 0.2, w: 1.4, h: 0.26, fontSize: 10, bold: true, color: SLATE, fontFace: MONO });
  arrow(s, xs[0] + nw, y1 + nh, xs[1] - xs[0] - nw, y2 - y1 - nh, VIO, { flipV: true });
  T(s, "CLAIMS", { x: xs[0] + nw + 0.45, y: y2 - 0.42, w: 0.9, h: 0.26, fontSize: 10, bold: true, color: VIO, fontFace: MONO });
  T(s, "APPLIES_TO ← Benefit", { x: xs[3], y: y2 + nh + 0.05, w: 2.68, h: 0.26, fontSize: 10, color: SLATE, fontFace: MONO, align: "center" });
  T(s, [
    { text: "모든 관계 속성: document_id · chunk_id · evidence(원문 문장). 근거 없는 관계는 만들지 않고, 카드 간 같은 정책만 하나의 노드로 공유합니다.", options: { bold: true, color: INK, breakLine: true } },
    { text: "판단 실행 기록 설계 메모: JudgmentRun {trace_id, 질문, 판정, 모델·데이터 버전} —USED→ 경로상의 Benefit·Condition·Clause (미구현)", options: { color: AMBER_D } },
  ], { x: L, y: 4.92, w: CW, h: 0.62, fontSize: 12, lineSpacingMultiple: 1.1 });
  boxT(s, "// 시연 ③ 영향 추적 (예시 Cypher, 미실행)\nMATCH (x:Condition {name:'상품권·기프트카드 구매'})<-[:EXCLUDES {scope:'실적'}]-(r:Condition)<-[:REQUIRES]-(b:Benefit)<-[:HAS_BENEFIT]-(c:Card)\nOPTIONAL MATCH (r)-[:SOURCED_FROM]->(cl:Clause)\nRETURN c.name AS card, b.name AS benefit, r.threshold AS spend, cl.id AS clause", { x: L, y: 5.62, w: CW, h: 1.28, fill: { color: INK }, line: { color: INK }, color: "E6ECF4", fontFace: MONO, fontSize: 10, align: "left", valign: "top", margin: 10 });
  footer(s, "노드·관계는 과제_매핑표_10.29.md M2 안 · Copy 노드는 V2 §6 제안 · JudgmentRun은 V4 설계 메모 · 쿼리는 설계 예시이며 실행 결과 아님");
  notes(s, "부록 B 그래프 설계안", { purpose: "8장 A(원문 근거)·B(실행 기록)가 그래프에서 어디에 저장되는지 보인다.", status: "설계안", rebuttal: "—" },
    "그래프 설계안입니다. 카드, 혜택, 조건, 제외 항목, 조항을 노드로 두고, 모든 관계에 문서 ID, 청크 ID, 원문 문장을 속성으로 붙입니다. 판단 실행 기록은 JudgmentRun 노드로 두고, 판단에 쓰인 경로상의 혜택·조건·조항을 USED 관계로 연결하는 안입니다. 아직 구현 전입니다.");
}

// C — experiment
{
  const s = content("부록 C   비교 실험 설계", "주장 대신 실험으로 — 결과 칸은 실행한 뒤에만 채웁니다", "부록");
  pills(s, ["미실행"]);
  T(s, "골든 질문 15~20개 · 정답 기준은 원문 조항", { x: L, y: 1.82, w: 6.0, h: 0.5, fontSize: 14, bold: true, color: INK });
  const qs = [
    ["근거 경로", "STYLE 대중교통 혜택의 전월실적 조건과 근거 조항은?"],
    ["변경 영향", "상품권을 실적에 포함하면 영향받는 카드·혜택·조항은?"],
    ["공유 구조", "체크·신용카드의 유사 혜택은 조건이 어떻게 다른가?"],
    ["적용 범위", "같은 항목이 할인·적립 제외로 쓰인 상품은?"],
    ["3상태 판정", "적용 / 미적용 / 판단 불가 사유가 맞는가?"],
  ];
  qs.forEach((q, i) => {
    const y = 2.4 + i * 0.66;
    chip(s, q[0], L, y, 1.45, 0.54, AMBER_T, AMBER_D);
    T(s, q[1], { x: L + 1.6, y, w: 4.5, h: 0.54, fontSize: 13, color: TXT, valign: "middle" });
  });
  T(s, "비교: ① 벡터 RAG ② PostgreSQL + 조건 + LLM ③ GraphRAG\n작성자·표본 수·계산법을 기록하고 불리한 항목도 공개합니다.\n선택 과제(S1) — 필수 M0~M9 완료 후 수행합니다.", { x: L, y: 5.8, w: 6.0, h: 1.05, fontSize: 12, color: SLATE, lineSpacingMultiple: 1.15 });
  const H = (t, bg) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: bg || SLATE }, align: "center" } });
  const e = { text: "—", options: { color: "A0AAB8", align: "center", fill: { color: MIST } } };
  const metrics = ["조건 누락률", "근거 조항 정확도", "잘못된 단정 비율", "영향 탐색 정밀도", "영향 탐색 재현율", "근거 경로 일치율", "판단 불가 적정성", "오류 원인 단계 식별률"];
  const rows = [[H("지표"), H("벡터 RAG"), H("SQL + LLM"), H("GraphRAG", INK)]].concat(metrics.map((m) => [{ text: m, options: { bold: true, color: INK } }, e, e, e]));
  s.addTable(rows, { x: 6.95, y: 1.85, w: 5.78, colW: [2.38, 1.13, 1.13, 1.14], rowH: 0.46, fontFace: F, fontSize: 12, color: TXT, border: tblBorder, valign: "middle", margin: [2, 6, 2, 6] });
  T(s, "— : 미실행. 수치는 실험 후 교체합니다.", { x: 6.95, y: 6.12, w: 5.78, h: 0.3, fontSize: 11, color: MUTED });
  footer(s, "설계 근거: 카드사_자체AI판단엔진_개발명분_공식근거조사_20261028.md §5 · V2 §3·§4 · 과제_매핑표_10.29.md (M8, S1)");
  notes(s, "부록 C 비교 실험 설계", { purpose: "6장의 예상 기호를 검증할 실험 설계. V4에서 시연 ① 질문과 '오류 원인 단계 식별률'을 추가했다.", status: "미실행", rebuttal: "—" },
    "6장의 비교는 예상이므로 실험으로 확인합니다. 골든 질문 15~20개를 원문 조항 기준으로 만들고 세 방식에 같은 질문을 던집니다. V4에서는 시연 ①의 근거 경로 질문과, 오답이 났을 때 원인 단계를 맞게 짚었는지 보는 오류 원인 단계 식별률을 지표에 추가했습니다. 결과 칸은 실험 후에만 채웁니다.");
}

// D — error verification (V3 S10)
{
  const s = content("부록 D   오류 검증 기준", "틀린 관계는 검증하고, 근거가 부족하면 판단을 보류합니다", "부록");
  pills(s, ["원문 확인", "검증 예정"]);
  const st = ["원문 청크", "트리플 JSON", "정규화 개체", "Neo4j 그래프"];
  const sw = 2.72, sg = (CW - sw * 4) / 3;
  st.forEach((t, i) => {
    const x = L + i * (sw + sg);
    boxT(s, t, { x, y: 1.85, w: sw, h: 0.58, fill: { color: SLATE_T }, line: { color: SLATE_T }, color: INK, fontSize: 14, bold: true });
    if (i < 3) arrow(s, x + sw + 0.03, 2.14, sg - 0.06, 0);
  });
  T(s, "단계 사이를 원문과 대조 (M8)", { x: L, y: 2.5, w: CW, h: 0.28, fontSize: 11, color: MUTED, align: "center" });
  T(s, "오류 6분류 — M8 검증 기준", { x: L, y: 2.95, w: 5.9, h: 0.32, fontSize: 14, bold: true, color: INK });
  ["원문에 없는 관계", "방향 오류", "중복", "오병합", "스키마 위반", "적재 누락"].forEach((t, i) => chip(s, t, L + (i % 3) * 1.98, 3.35 + Math.floor(i / 3) * 0.48, 1.88, 0.4, RED_T, RED_D, { fontSize: 13 }));
  T(s, "개선 루프", { x: L, y: 4.42, w: 5.9, h: 0.32, fontSize: 14, bold: true, color: INK });
  ["오류 분류", "프롬프트·정규화 수정", "재추출", "같은 질문 재검증"].forEach((t, i) => {
    const x = L + i * 1.5;
    boxT(s, t, { x, y: 4.8, w: 1.3, h: 0.62, fill: { color: AMBER_T }, line: { color: AMBER_T }, color: AMBER_D, fontSize: 12, bold: true, margin: 3 });
    if (i < 3) arrow(s, x + 1.31, 5.11, 0.18, 0);
  });
  T(s, "A(파일)·B(PostgreSQL) 두 파이프라인의 추출이 어긋나는 항목은 사람 검토 대상으로 분류합니다.", { x: L, y: 5.55, w: 5.95, h: 0.55, fontSize: 12, color: SLATE });
  T(s, "원문 조사에서 이미 확인한 함정 — 시연 후보", { x: 6.85, y: 2.95, w: 5.88, h: 0.32, fontSize: 14, bold: true, color: INK });
  const cases = [
    ["실적 제외 ↔ 혜택 제외 혼동", "상품권이 BT 실적 제외와 BIG TICKET 할인 제외에 모두 등장. scope를 잘못 붙이면 시연 ②·③ 결과가 틀어집니다."],
    ["표 구조 손실 → 잘못된 관계", "BT 할인율 4개가 한 셀로 추출. 구간별 할인율·한도 연결은 사람 검토 대상입니다."],
    ["원문 문구의 임의 정규화", "신한 건담 X 원문의 ‘상품/선불전자지급수단’ → ‘상품권’으로 자동 변환하지 않고 판단 보류."],
  ];
  cases.forEach((c, i) => {
    const y = 3.35 + i * 0.95;
    rect(s, { x: 6.85, y, w: 5.88, h: 0.85 });
    T(s, [{ text: c[0], options: { bold: true, color: INK, fontSize: 13, breakLine: true } }, { text: c[1], options: { fontSize: 12, color: SLATE } }], { x: 7.02, y: y + 0.07, w: 5.55, h: 0.75 });
  });
  boxT(s, "목표는 ‘전부 고쳤다’가 아니라 ‘어디서 멈추는지 안다’입니다. 미해결 1건은 판단 보류로 그대로 공개합니다.", { x: L, y: 6.2, w: CW, h: 0.65, fill: { color: INK }, line: { color: INK }, color: "FFFFFF", fontSize: 15, bold: true, align: "left", margin: 14 });
  footer(s, "함정 사례는 원문 조사로 확인한 위험 · LLM 실행 로그로 재현한 ‘실제 오답’은 M4·M8 이후 교체 (V1·V2 오답 공개 원칙)");
  notes(s, "부록 D 오류 검증 기준", { purpose: "시연 ②의 오류 추적을 뒷받침하는 M8 검증 기준(V3 본문 10장을 부록으로 이동).", status: "원문 확인(함정 사례) · 검증 예정", rebuttal: "—" },
    "시연 ②의 오류 추적을 뒷받침하는 검증 기준입니다. 원문 청크, 트리플, 정규화 개체, 그래프 사이를 원문과 대조하고 오류를 6가지로 분류합니다. 오른쪽은 원문 조사에서 이미 확인한 함정이며, 실제 LLM 오답은 추출 후 교체합니다.");
}

// E — control (V3 S12 table)
{
  const s = content("부록 E   자사 AI vs 외부 AI", "자사 AI와 외부 AI의 차이는 엔진이 아니라 ‘통제권’에 있습니다", "부록");
  pills(s, ["팀 가설"]);
  const H = (t, bg) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: bg || SLATE } } });
  const lab = (t) => ({ text: t, options: { bold: true, color: INK, fill: { color: MIST } } });
  const rows = [
    [H("구분"), H("카드사 자사 AI", INK), H("외부 AI (연동 허용 시)")],
    [lab("조건·근거·판단 기록"), { text: "같은 엔진 → 같은 구조화 결과·근거·trace", options: { colspan: 2, bold: true, color: TEAL_D, fill: { color: TEAL_T }, align: "center" } }],
    [lab("고객 접점"), "카드사", "외부 플랫폼"],
    [lab("답변·화면 구성"), "카드사가 설계", "외부 AI가 결정"],
    [lab("최종 답변–근거 일치 점검"), "카드사가 사후 점검 가능", "외부 AI의 최종 문장은 카드사가 받지 못할 수 있음"],
    [lab("브랜드·캠페인 표시"), "승인 정책대로 관리", "필드를 줘도 표시 보장 불가"],
    [lab("최신 조건 사용"), "운영 절차로 통제", "호출·캐시·요약에 따라 다름"],
  ];
  s.addTable(rows, { x: L, y: 1.85, w: CW, colW: [3.2, 4.2, 4.73], rowH: 0.52, fontFace: F, fontSize: 13, color: TXT, border: tblBorder, valign: "middle", margin: [3, 8, 3, 8] });
  boxT(s, [
    { text: "시사점  ", options: { bold: true, color: AMBER } },
    { text: "엔진은 공유하되, 최종 답변까지 근거와 대조할 수 있는 곳은 카드사가 통제하는 채널입니다. 외부 AI에는 근거·trace id를 함께 공급해 사후 추적의 단서를 남기되, 최종 답변 대조는 플랫폼의 응답 기록 제공 여부에 달려 있습니다.", options: { color: "FFFFFF" } },
  ], { x: L, y: 5.75, w: CW, h: 0.95, fill: { color: INK }, line: { color: INK }, fontSize: 14, align: "left", margin: 14 });
  footer(s, "역할 비교: V2 §6-1 · '최종 답변–근거 일치 점검' 행은 V4 추가(팀 가설) · 외부 플랫폼 정책은 미확인");
  notes(s, "부록 E 자사 AI vs 외부 AI", { purpose: "V3 본문 12장의 통제권 표를 부록으로 옮기고, 최종 답변–근거 일치 점검 행을 추가했다.", status: "팀 가설", rebuttal: "—" },
    "자사 AI와 외부 AI는 같은 엔진을 쓰면 같은 근거를 받습니다. 차이는 통제권입니다. 특히 최종 답변이 근거와 일치하는지 사후 점검할 수 있는 곳은 카드사가 통제하는 채널이고, 외부 AI에는 근거와 trace id를 함께 공급해 추적 단서를 남기는 안입니다.");
}

// F — Q&A
{
  const s = content("부록 F   예상 질문", "받을 질문을 먼저 정리했습니다", "부록");
  const H = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: INK } } });
  const q = (t) => ({ text: t, options: { bold: true, color: INK, fill: { color: MIST } } });
  const rows = [
    [H("질문"), H("답변 요지")],
    [q("AI(LLM)의 사고 과정까지 설명하나요?"), "아니요. 설명 대상은 실행 시 기록 가능한 검색 경로·적용 규칙·근거 조항과 최종 답변의 일치 여부입니다. LLM 내부 추론은 대상이 아닙니다."],
    [q("PDF 원문 검색으로 충분하지 않나요?"), "원문 위치는 찾지만, 어떤 조건이 어느 혜택에 어떤 범위로 적용됐는지는 남지 않습니다. 혜택별 조건–판단 연결이 필요한 이유입니다."],
    [q("카드사의 정본은 PDF가 아니라 내부 상품 DB 아닌가요?"), "PDF는 고객에게 고지된 계약 문구입니다. 내부 DB와 고지 문서의 불일치를 점검하는 보완 용도로 제안합니다 (내부 시스템 구조는 미확인)."],
    [q("카드를 약 10종으로 늘려도 SQL로 되지 않나요?"), "됩니다. GraphRAG만 가능한 기능은 아닙니다. 유사 혜택·제외 범위를 SQL과 Cypher로 비교해 모델링과 경로 추적의 차이를 검증하겠습니다."],
    [q("신한이 이미 비슷한 걸 만들지 않나요?"), "차별점이 아니라 업계가 인정한 문제라는 근거로 인용했습니다. 신한 엔진의 방식(GraphRAG 여부)은 공개되지 않았습니다."],
    [q("표 추출이 자동인가요?"), "기본 표 추출은 대부분 실패했습니다. 수작업 보정과 사람 검토가 들어간다는 점을 공개합니다."],
    [q("MCP가 있으면 외부 AI의 답을 통제하나요?"), "아닙니다. 조건·근거·trace id를 공급하고 그 내역을 기록할 뿐, 호출 여부·요약·문구는 외부 AI가 결정합니다. 최종 답변 추적은 플랫폼이 응답 기록을 줄 때만 가능합니다."],
    [q("고객에게 추천하면 규제 문제는요?"), "이번 범위는 내부 검토 도구입니다. 고객 대면 추천·광고는 금융소비자보호법상 권유·광고 규율 검토가 필요합니다 (준법 확인 필요)."],
    [q("문서가 최신인가요?"), "시행일·현재 유효 여부·재배포 조건은 미확인입니다. 문서 버전과 SHA-256 해시를 함께 기록합니다."],
  ];
  s.addTable(rows, { x: L, y: 1.75, w: CW, colW: [4.0, 8.13], rowH: [0.38, 0.52, 0.52, 0.52, 0.52, 0.52, 0.45, 0.45, 0.52, 0.45], fontFace: F, fontSize: 11, color: TXT, border: tblBorder, valign: "middle", margin: [2, 6, 2, 6] });
  footer(s, "출처: ppt_story_key_points_v2_draft.md §8 (예상 반론과 답변) · V4 추가: 앞의 두 질문");
  notes(s, "부록 F 예상 질문", { purpose: "예상 질문과 답변 요지. V4에서 'LLM 사고 과정'과 'PDF 원문 검색으로 충분한가'를 추가했다.", status: "—", rebuttal: "—" },
    "예상 질문입니다. V4에서 추가한 두 질문이 가장 중요합니다. 저희는 LLM 내부 사고 과정을 설명한다고 주장하지 않고, 기록 가능한 경로·규칙·근거와 최종 답변의 일치를 검증합니다. 그리고 원문 검색만으로는 조건이 어느 혜택에 어떤 범위로 적용됐는지가 남지 않습니다.");
}

// G — sources
{
  const s = content("부록 G   출처와 검증 상태", "무엇을 확인했고, 무엇을 정정했는가", "부록");
  const H = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: INK } } });
  const ok = (t) => ({ text: t, options: { color: TEAL_D, bold: true } });
  const rows = [
    [H("자료"), H("사용한 내용"), H("상태")],
    ["신한금융그룹 보도자료 (2026-09-09) shinhangroup.com/kr/archive/press/detail/966", "조건 판단 AI 엔진 공동 개발, 기존 AI 문제 4가지", ok("공식 확인 2026-10-30")],
    ["신한카드 보도자료 (2026-09-13) press1.newswire.co.kr/newsRead.php?no=1042468", "ChatGPT for Kakao, PlayMCP 기반 카카오 툴즈 연동", ok("공식 확인 2026-10-30")],
    ["하나카드 상품설명서 STYLE·PLAY·BT·에너지 더블 (m.hanacard.co.kr/leaflet/…)", "상품권 제외 범위, 혜택별 실적 조건, STYLE 대중교통 조건·예외", ok("원문 확인 2026-10-30")],
    ["card_pdf_structuring_validation.md", "표 추출 실패 사례 (STYLE·PLAY 0개, BT 셀 병합)", ok("팀 검증 기록")],
    ["card_scope_comparison_claude.md · _gpt_review.md · card_scope_comparison.md", "공통 문구·scope 차이, PG 재분류 문장, PDF 확보 범위", ok("팀 조사 기록")],
    ["src/common/query_logger.py", "SQL·Cypher 원문·파라미터·결과 로그 포매터 (판단 실행 기록의 기반 부품)", ok("구현 확인")],
  ];
  s.addTable(rows, { x: L, y: 1.8, w: CW, colW: [5.2, 4.83, 2.1], rowH: 0.44, fontFace: F, fontSize: 11, color: TXT, border: tblBorder, valign: "middle", margin: [2, 6, 2, 6] });
  rect(s, { x: L, y: 5.12, w: CW, h: 1.7, fill: { color: AMBER_T }, line: { color: AMBER_T } });
  T(s, [
    { text: "원문 대조로 정정한 사항", options: { bold: true, color: AMBER_D, fontSize: 13, breakLine: true } },
    { text: "V3 표지의 ‘대중교통 5% 할인’ → 원문은 ‘5% 캐시백, 서비스 한도 월 1천원’. V4에서 정정했습니다 (V3 파일은 보존).", options: { bullet: true, breakLine: true } },
    { text: "BT BIG TICKET의 지난달 실적은 원문 표에 ‘없음’, 50만원 조건은 인천공항 라운지입니다 (card_scope_comparison_claude.md 기재와 다름).", options: { bullet: true, breakLine: true } },
    { text: "에너지 더블은 에너지 공과금 청구할인(40/80만원)도 지난달 실적 조건이 있어 영향 목록에 포함했습니다.", options: { bullet: true, breakLine: true } },
    { text: "STYLE 문서는 15650_20260429판 기준. 일부 조사 문서는 15650_20260316 링크를 인용하며, 두 판의 차이는 대조하지 않았습니다.", options: { bullet: true } },
  ], { x: L + 0.2, y: 5.2, w: CW - 0.4, h: 1.55, fontSize: 12, color: TXT, paraSpaceAfter: 3 });
  footer(s, "원문 PDF는 저장소에 추가하지 않았습니다 (재배포 조건 미확인).");
  notes(s, "부록 G 출처와 검증 상태", { purpose: "출처·검증 상태·정정 이력을 공개한다.", status: "—", rebuttal: "—" },
    "출처와 검증 상태입니다. 이번 V4에서 V3 표지의 대중교통 5% 할인을 원문대로 5% 캐시백, 월 1천원 한도로 정정했습니다. STYLE 문서는 2026년 4월 29일 판을 기준으로 했고, 일부 조사 문서가 인용한 다른 판과의 차이는 대조하지 않았습니다.");
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  if (process.env.PPTX_SKILL) {
    const { applyTheme } = require(process.env.PPTX_SKILL + "/scripts/apply_theme.js");
    await applyTheme(OUT, THEME);
  }
  if (NOTES_OUT) {
    const md = NOTES.map((n, i) => [
      `## ${i + 1}. ${n.label}`,
      "",
      `- **목적:** ${n.purpose}`,
      `- **상태:** ${n.status}`,
      `- **예상 반박:** ${n.rebuttal}`,
      "",
      "**발표 대본**",
      "",
      `> ${n.script}`,
      "",
    ].join("\n")).join("\n");
    fs.writeFileSync(NOTES_OUT, md, "utf8");
  }
  console.log("written", OUT, NOTES.length, "slides");
})();
