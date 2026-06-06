#!/usr/bin/env node
/**
 * build_report.js v3 - 글로벌 시황 보고서 DOCX 생성기 (namoobi-market-report)
 *
 * v3 변경점 (v2 대비):
 *  - `--validate` 모드: docx 생성 없이 입력 JSON 의 섹션 완결성만 검사 (Phase 3 검증용)
 *  - Executive Summary 섹션 추가 (analysis.summary)
 *  - null 안전 처리 강화: fear_greed 델타, market_overview 거래량, kimchi premium
 *  - JSON 파싱 실패 시 명확한 오류 메시지 + exit code
 *  - 빌드 후 표 개수 출력 (무결성 점검 보조)
 *
 * 사용법:
 *   node build_report.js <input_data.json> [output_path.docx]
 *   node build_report.js --validate <input_data.json>
 */

const fs = require('fs');
const path = require('path');

// ---------- CLI ----------
const argv = process.argv.slice(2);
const validateOnly = argv[0] === '--validate';
const args = validateOnly ? argv.slice(1) : argv;
if (args.length < 1) {
  console.error("Usage: node build_report.js [--validate] <input_data.json> [output_path.docx]");
  process.exit(1);
}
const inputPath = args[0];

let data;
try {
  data = JSON.parse(fs.readFileSync(inputPath, 'utf-8'));
} catch (e) {
  console.error(`❌ 입력 JSON 읽기/파싱 실패: ${inputPath}`);
  console.error(`   ${e.message}`);
  process.exit(1);
}

// ---------- Validation (보고서 품질 기준 8개 항목) ----------
function validate(d) {
  const issues = [];
  const warn = [];
  const has = (obj, k) => obj && obj[k] !== undefined && obj[k] !== null;

  if (!has(d, 'metadata') || !d.metadata.report_date) issues.push("metadata.report_date 누락");
  if (!has(d, 'news') || !Array.isArray(d.news.top_news) || d.news.top_news.length === 0)
    issues.push("news.top_news 누락 (품질기준 1: Top News 10)");
  else if (d.news.top_news.length < 10) warn.push(`top_news ${d.news.top_news.length}개 (<10)`);
  if (!has(d, 'news') || !Array.isArray(d.news.events_calendar) || d.news.events_calendar.length === 0)
    warn.push("news.events_calendar 누락 (품질기준 2: 1개월 캘린더)");
  if (!has(d, 'news') || !Array.isArray(d.news.events_calendar_longterm) || d.news.events_calendar_longterm.length === 0)
    warn.push("news.events_calendar_longterm 누락 (품질기준 2: 중장기 ★★★ 캘린더)");
  if (!has(d, 'markets')) issues.push("markets 누락 (품질기준 3,4: 증시 추세)");
  else {
    if (!d.markets.korea) warn.push("markets.korea 누락 (코스피·코스닥)");
    if (!d.markets.us_markets) issues.push("markets.us_markets 누락");
    else { if (!d.markets.us_markets.vix) warn.push("VIX 누락 (품질기준 5)"); if (!d.markets.us_markets.dxy) warn.push("DXY 누락 (품질기준 5)"); }
    if (!d.markets.asia_markets) warn.push("markets.asia_markets 누락");
    if (!d.markets.europe_markets) warn.push("markets.europe_markets 누락");
    if (!d.markets.fx_markets) warn.push("markets.fx_markets 누락 (품질기준 7: 환율 추세) — fx_snapshot 폴백 사용");
  }
  if (!has(d, 'commodities')) issues.push("commodities 누락 (품질기준 6)");
  else {
    if (!d.commodities.agriculture) warn.push("commodities.agriculture 누락 (옥수수·대두·밀)");
    if (!d.commodities.metals || !d.commodities.metals.rare_earth) warn.push("commodities.metals.rare_earth 누락 (희토류 REMX)");
  }
  if (!has(d, 'crypto')) issues.push("crypto 누락 (품질기준 8)");
  else { if (!d.crypto.fear_greed) warn.push("crypto.fear_greed 누락"); if (!d.crypto.kimchi_premium) warn.push("crypto.kimchi_premium 누락"); }
  if (!has(d, 'securities')) warn.push("securities 누락 (한국 5대 증권사)");
  if (!has(d, 'global_securities')) warn.push("global_securities 누락 (글로벌 IB 5사: UBS/GS/JPM/MS/BlackRock)");
  if (!has(d, 'analysis')) issues.push("analysis 누락 (품질기준 8)");
  else {
    if (!d.analysis.portfolios) issues.push("analysis.portfolios 누락 (공격/중립/안정형)");
    if (!d.analysis.summary) warn.push("analysis.summary 누락 (Executive Summary)");
  }
  return { issues, warn };
}

const { issues, warn } = validate(data);
if (validateOnly) {
  if (warn.length) { console.log("⚠️ 경고:"); warn.forEach(w => console.log("  - " + w)); }
  if (issues.length) {
    console.error("❌ 필수 누락:"); issues.forEach(i => console.error("  - " + i));
    process.exit(1);
  }
  console.log("✅ 데이터 검증 통과" + (warn.length ? ` (경고 ${warn.length}건)` : ""));
  process.exit(0);
}
if (issues.length) { console.error("⚠️ 필수 섹션 누락 상태로 빌드합니다:"); issues.forEach(i => console.error("  - " + i)); }
if (warn.length) { warn.forEach(w => console.error("  (경고) " + w)); }

let docx;
try { docx = require('docx'); }
catch (e) {
  console.error("❌ docx 라이브러리가 없습니다. cd " + __dirname + " && npm install docx");
  process.exit(1);
}

const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, HeadingLevel,
  BorderStyle, WidthType, ShadingType, PageNumber, PageBreak
} = docx;

const reportDate = (data.metadata && data.metadata.report_date) || new Date().toISOString().slice(0, 10);
const dateCompact = reportDate.replace(/-/g, '');
const defaultOutPath = path.join(__dirname, '..', '..', `글로벌금융시장_종합시황보고서_${dateCompact}.docx`);
const outPath = args[1] || defaultOutPath;

// ---------- Style helpers ----------
const border = { style: BorderStyle.SINGLE, size: 4, color: "9CA3AF" };
const borders = { top: border, bottom: border, left: border, right: border };
const headerShading = { fill: "1E40AF", type: ShadingType.CLEAR, color: "auto" };
const altShading   = { fill: "EFF6FF", type: ShadingType.CLEAR, color: "auto" };
const negativeColor = "DC2626";
const positiveColor = "059669";

function fmtPct(v) {
  if (v === null || v === undefined || v === "") return "-";
  const n = Number(v);
  if (isNaN(n)) return String(v);
  return (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
}
function pctColor(v) {
  if (v === null || v === undefined || v === "") return undefined;
  const n = Number(v);
  if (isNaN(n)) return undefined;
  return n >= 0 ? positiveColor : negativeColor;
}
function fmtNum(v) {
  if (v === null || v === undefined || v === "") return "-";
  const n = Number(v);
  if (isNaN(n)) return String(v);
  if (Math.abs(n) >= 1000) return n.toLocaleString(undefined, {maximumFractionDigits: 2});
  return n.toFixed(2);
}
function fgDelta(cur, prev) {
  const c = Number(cur), p = Number(prev);
  if (isNaN(c) || isNaN(p)) return "-";
  const d = c - p;
  return (d >= 0 ? "+" : "") + d;
}

function p(text, opts={}) {
  return new Paragraph({
    spacing: { after: opts.after ?? 80, before: opts.before ?? 0 },
    alignment: opts.align ?? AlignmentType.LEFT,
    children: [new TextRun({ text: String(text), bold: opts.bold, size: opts.size ?? 22,
                             color: opts.color, italics: opts.italics })]
  });
}
function h(text, level) {
  const map = { 1: HeadingLevel.HEADING_1, 2: HeadingLevel.HEADING_2, 3: HeadingLevel.HEADING_3 };
  return new Paragraph({
    heading: map[level], spacing: { before: 240, after: 120 },
    children: [new TextRun({ text, bold: true })]
  });
}
function bullet(text, opts={}) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 60 },
    children: [new TextRun({ text: String(text), size: opts.size ?? 22, bold: opts.bold, color: opts.color })]
  });
}
function cellRun(text, opts={}) {
  return new TextRun({ text: String(text), bold: opts.bold || opts.header,
                       size: opts.size ?? 20,
                       color: opts.header ? "FFFFFF" : opts.color });
}
function cell(text, opts={}) {
  return new TableCell({
    borders, width: { size: opts.width, type: WidthType.DXA },
    shading: opts.header ? headerShading : (opts.alt ? altShading : undefined),
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      alignment: opts.align ?? AlignmentType.LEFT,
      children: opts.runs || [cellRun(text, opts)]
    })]
  });
}
let tableCount = 0;
function makeTable(colWidths, rows) {
  tableCount++;
  const total = colWidths.reduce((a,b)=>a+b, 0);
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: colWidths, rows });
}

// ---------- Build content ----------
const children = [];

// Cover
children.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 2400, after: 240 },
  children: [new TextRun({ text: "글로벌 금융시장 종합 시황 보고서", bold: true, size: 48, color: "1E3A8A" })]
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after: 240 },
  children: [new TextRun({ text: "Global Financial Markets Comprehensive Report", italics: true, size: 28, color: "475569" })]
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after: 1200 },
  children: [new TextRun({ text: "Top News · 이벤트 캘린더 · 단·중·장기 추세 · 매크로 · 원자재·희토류 · 환율 · 코인 · 5대 증권사 · 포트폴리오", size: 20, color: "64748B" })]
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after: 120 },
  children: [new TextRun({ text: `기준일: ${reportDate}`, size: 26, bold: true })]
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after: 120 },
  children: [new TextRun({ text: "작성: Claude AI Research (Cowork) — namoobi-market-report v3.2", size: 22, color: "64748B" })]
}));

// Executive Summary
if (data.analysis && data.analysis.summary) {
  children.push(new Paragraph({ children: [new PageBreak()] }));
  children.push(h("Executive Summary", 1));
  children.push(p(data.analysis.summary, { size: 24 }));
  if (data.news && Array.isArray(data.news.top_news) && data.news.top_news.length > 0) {
    children.push(p(""));
    children.push(p("오늘의 핵심 헤드라인:", { bold: true }));
    data.news.top_news.slice(0, 3).forEach(n => children.push(bullet(`${n.headline} — ${n.impact || ''}`)));
  }
}

// 목차
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h("목   차", 1));
const toc = [
  "1. 글로벌 Top News 10",
  "2. 글로벌 주요 이벤트 캘린더 (향후 1개월 + 중장기 ★★★)",
  "3. 글로벌 증시 단·중·장기 추세 (한국·미국·일본·중국·홍콩·인도·베트남·유럽)",
  "4. 매크로 지표 (달러지수·VIX·미국채 10년)",
  "5. 원자재 - 에너지·금속(희토류 포함)·농산물",
  "6. 주요 환율 단·중·장기 추세 (+달러인덱스)",
  "7. 암호화폐 - 시장·공포탐욕·김치프리미엄",
  "8. 한국 5대 증권사 리서치 (강점·채널·시각)",
  "9. 글로벌 주요 IB 리서치 (UBS·GS·JPM·MS·BlackRock)",
  "10. 종합 분석 - 매크로 톤·핵심 테마·리스크",
  "11. 자산별 단·중·장기 견해",
  "12. 추천 포트폴리오 (공격형 / 중립형 / 안정형)",
  "13. 액션 아이템 - 단기·중기·장기 체크리스트",
  "14. 주의 사항 및 출처"
];
toc.forEach(t => children.push(p(t, { size: 22, after: 40 })));

// ============================================================
// 1. Top News
// ============================================================
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h("1. 글로벌 Top News 10", 1));
if (data.news && Array.isArray(data.news.top_news)) {
  const newsHeader = ["#", "헤드라인", "내용 요약", "임팩트"];
  const rows = [newsHeader, ...data.news.top_news.map(n => [
    String(n.rank ?? "-"), n.headline ?? "-", n.summary ?? "-", n.impact ?? "-"
  ])].map((r, i) => new TableRow({
    children: r.map((c, j) => cell(c, {
      width: [600, 2200, 4660, 1900][j], header: i === 0,
      alt: i > 0 && i % 2 === 0,
      align: j === 0 ? AlignmentType.CENTER : AlignmentType.LEFT,
      bold: j === 1 && i > 0
    }))
  }));
  children.push(makeTable([600, 2200, 4660, 1900], rows));
} else {
  children.push(p("(뉴스 데이터 없음)"));
}

// ============================================================
// 2. 글로벌 주요 이벤트 캘린더
// ============================================================
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h("2. 글로벌 주요 이벤트 캘린더", 1));
children.push(h("2.1 향후 1개월 (전체 중요도)", 2));
if (data.news && Array.isArray(data.news.events_calendar) && data.news.events_calendar.length > 0) {
  const evHeader = ["날짜", "지역", "이벤트", "중요도", "예상 영향"];
  const evWidths = [1300, 1100, 2800, 1100, 3060];
  const evRows = [evHeader, ...data.news.events_calendar.map(e => [
    e.date ?? "-", e.region ?? "-", e.event ?? "-", e.importance ?? "-", e.expected_impact ?? "-"
  ])].map((r, i) => new TableRow({
    children: r.map((c, j) => cell(c, {
      width: evWidths[j], header: i === 0,
      alt: i > 0 && i % 2 === 0,
      align: (j === 0 || j === 1 || j === 3) ? AlignmentType.CENTER : AlignmentType.LEFT,
      bold: j === 2 && i > 0,
      color: (j === 3 && i > 0 && String(c).includes("★★★")) ? "DC2626" : undefined
    }))
  }));
  children.push(makeTable(evWidths, evRows));
} else {
  children.push(p("(1개월 이벤트 캘린더 데이터 없음)"));
}
children.push(p(""));
children.push(h("2.2 중장기 — 1개월 이후 ~ 1년 (★★★ 핵심 이벤트만)", 2));
if (data.news && Array.isArray(data.news.events_calendar_longterm) && data.news.events_calendar_longterm.length > 0) {
  const lvHeader = ["날짜", "지역", "이벤트", "예상 영향"];
  const lvWidths = [1500, 1200, 3000, 3660];
  const lvRows = [lvHeader, ...data.news.events_calendar_longterm.map(e => [
    e.date ?? "-", e.region ?? "-", e.event ?? "-", e.expected_impact ?? "-"
  ])].map((r, i) => new TableRow({
    children: r.map((c, j) => cell(c, {
      width: lvWidths[j], header: i === 0,
      alt: i > 0 && i % 2 === 0,
      align: (j === 0 || j === 1) ? AlignmentType.CENTER : AlignmentType.LEFT,
      bold: j === 2 && i > 0
    }))
  }));
  children.push(makeTable(lvWidths, lvRows));
  children.push(p("※ 중장기 캘린더는 중요도 ★★★ 이벤트만 수록. 미확정 일정은 (예정) 표기.", { italics: true, color: "94A3B8", size: 18 }));
} else {
  children.push(p("(중장기 이벤트 캘린더 데이터 없음)"));
}

// ============================================================
// 3. 증시 단·중·장기 추세
// ============================================================
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h("3. 글로벌 증시 단·중·장기 추세", 1));
children.push(p("각 시장의 단기(1주)·중기(1~3개월)·장기(6개월~1년) 변화율을 통해 추세 강도와 모멘텀을 동시에 평가한다.", { italics: true, color: "64748B" }));

function trendRow(name, m, i) {
  const cells = [
    cell(name, { width: 1700, alt: i % 2 === 1, bold: true }),
    cell(fmtNum(m && m.current), { width: 1300, alt: i % 2 === 1, align: AlignmentType.RIGHT }),
    cell(fmtPct(m && m['1w_pct']),  { width: 1100, alt: i % 2 === 1, align: AlignmentType.RIGHT, color: pctColor(m && m['1w_pct']) }),
    cell(fmtPct(m && m['1mo_pct']), { width: 1100, alt: i % 2 === 1, align: AlignmentType.RIGHT, color: pctColor(m && m['1mo_pct']) }),
    cell(fmtPct(m && m['3mo_pct']), { width: 1100, alt: i % 2 === 1, align: AlignmentType.RIGHT, color: pctColor(m && m['3mo_pct']) }),
    cell(fmtPct(m && m['6mo_pct']), { width: 1100, alt: i % 2 === 1, align: AlignmentType.RIGHT, color: pctColor(m && m['6mo_pct']) }),
    cell(fmtPct(m && m['1y_pct']),  { width: 1100, alt: i % 2 === 1, align: AlignmentType.RIGHT, color: pctColor(m && m['1y_pct']) }),
    cell((m && m.trend) || "-",    { width: 1700, alt: i % 2 === 1 })
  ];
  return new TableRow({ children: cells });
}
function trendHeaderRow() {
  const headers = ["지수", "현재치", "1주", "1개월", "3개월", "6개월", "1년", "추세 평가"];
  const widths  = [1700, 1300, 1100, 1100, 1100, 1100, 1100, 1700];
  return new TableRow({
    children: headers.map((h_, i) => cell(h_, { width: widths[i], header: true, align: AlignmentType.CENTER }))
  });
}
const tw = [1700, 1300, 1100, 1100, 1100, 1100, 1100, 1700];

function renderMarketBlock(title, marketObj, labels) {
  if (!marketObj) return;
  children.push(h(title, 2));
  const rows = [trendHeaderRow()];
  let i = 0;
  for (const [key, val] of Object.entries(marketObj)) {
    const displayName = (labels && labels[key]) || key.toUpperCase();
    rows.push(trendRow(displayName, val, i));
    i++;
  }
  children.push(makeTable(tw, rows));
  children.push(p(""));
}

if (data.markets) {
  renderMarketBlock("3.1 한국 증시", data.markets.korea, {
    kospi: "코스피", kosdaq: "코스닥"
  });
  renderMarketBlock("3.2 미국 증시", data.markets.us_markets, {
    sp500: "S&P 500", nasdaq: "나스닥", dow: "다우",
    vix: "VIX (공포지수)", dxy: "달러지수 DXY", us10y: "美 10년 국채"
  });
  renderMarketBlock("3.3 아시아 증시", data.markets.asia_markets, {
    nikkei: "닛케이 225", shanghai: "상하이종합",
    hsi: "홍콩 항셍", sensex: "인도 센섹스", vietnam: "베트남 (VNM)"
  });
  renderMarketBlock("3.4 유럽 증시", data.markets.europe_markets, {
    stoxx50: "유로 스톡스 50", dax: "독일 DAX", ftse: "영국 FTSE 100"
  });
}

// ============================================================
// 4. 매크로 지표
// ============================================================
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h("4. 매크로 지표 종합 코멘트", 1));
const usM = (data.markets && data.markets.us_markets) || {};
const macroRows = [
  ["지표", "현재치", "단기 시그널", "장기 추세"],
  ["VIX (공포지수)", fmtNum(usM.vix && usM.vix.current),
    fmtPct(usM.vix && usM.vix['1w_pct']),  (usM.vix && usM.vix.trend) || "-"],
  ["DXY (달러지수)", fmtNum(usM.dxy && usM.dxy.current),
    fmtPct(usM.dxy && usM.dxy['1w_pct']),  (usM.dxy && usM.dxy.trend) || "-"],
  ["美 10년 국채금리", fmtNum(usM.us10y && usM.us10y.current),
    fmtPct(usM.us10y && usM.us10y['1w_pct']),  (usM.us10y && usM.us10y.trend) || "-"]
].map((r, i) => new TableRow({
  children: r.map((c, j) => cell(c, {
    width: [2400, 2000, 2200, 2760][j], header: i === 0,
    alt: i > 0 && i % 2 === 0, bold: j === 0 && i > 0,
    align: (j === 1 || j === 2) ? AlignmentType.RIGHT : AlignmentType.LEFT,
    color: (j === 2 && i > 0) ? pctColor(String(r[j]).replace('%','').replace('+','')) : undefined
  }))
}));
children.push(makeTable([2400, 2000, 2200, 2760], macroRows));

// ============================================================
// 5. 원자재
// ============================================================
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h("5. 원자재 종합 - 에너지·금속·희토류·농산물", 1));

if (data.commodities) {
  renderMarketBlock("5.1 에너지", data.commodities.energy, {
    wti: "WTI 원유", brent: "Brent 원유", natgas: "천연가스"
  });
  renderMarketBlock("5.2 금속 (귀금속·산업금속·희토류)", data.commodities.metals, {
    gold: "금 (Gold)", silver: "은 (Silver)", copper: "구리 (Copper)", platinum: "백금 (Platinum)",
    rare_earth: "희토류 (REMX ETF)"
  });
  renderMarketBlock("5.3 농산물", data.commodities.agriculture, {
    corn: "옥수수 (Corn)", soybean: "대두 (Soybeans)", wheat: "밀 (Wheat)"
  });
  if (data.commodities.metals && data.commodities.metals.rare_earth) {
    children.push(p("※ 희토류는 거래소 선물 시세가 없어 VanEck 희토류·전략금속 ETF(REMX)를 프록시로 사용.", { italics: true, color: "94A3B8", size: 18 }));
  }
  if (data.commodities.commentary) {
    children.push(h("5.4 원자재 종합 코멘트", 2));
    children.push(p(data.commodities.commentary));
  }
}

// ============================================================
// 6. 환율 (단·중·장기 추세 + 달러인덱스)
// ============================================================
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h("6. 주요 환율 단·중·장기 추세", 1));
if (data.markets && data.markets.fx_markets) {
  children.push(p("환율 상승 = 원화 약세. 달러인덱스(DXY)는 6개 주요통화 대비 달러 가치.", { italics: true, color: "64748B" }));
  const fxLabels = {
    usd_krw: "USD/KRW", eur_krw: "EUR/KRW", jpy_krw: "JPY/KRW (100엔)",
    cny_krw: "CNY/KRW", hkd_krw: "HKD/KRW"
  };
  const fxRows = [trendHeaderRow()];
  let fi = 0;
  for (const [key, val] of Object.entries(data.markets.fx_markets)) {
    fxRows.push(trendRow(fxLabels[key] || key.toUpperCase(), val, fi)); fi++;
  }
  if (data.markets.us_markets && data.markets.us_markets.dxy) {
    fxRows.push(trendRow("달러인덱스 (DXY)", data.markets.us_markets.dxy, fi));
  }
  children.push(makeTable(tw, fxRows));
} else if (data.news && data.news.fx_snapshot) {
  // 구버전 폴백: 현재가 스냅샷만 렌더링
  const fx = data.news.fx_snapshot;
  const fxRows = [
    ["통화쌍", "현재 환율 (원화 기준)"],
    ["USD/KRW",          fx.USD_KRW || "-"],
    ["EUR/KRW",          fx.EUR_KRW || "-"],
    ["JPY/KRW (100엔)",  fx.JPY_KRW || "-"],
    ["CNY/KRW",          fx.CNY_KRW || "-"],
    ["HKD/KRW",          fx.HKD_KRW || "-"]
  ].map((r, i) => new TableRow({
    children: r.map((c, j) => cell(c, {
      width: [3000, 6360][j], header: i === 0,
      alt: i > 0 && i % 2 === 0, bold: j === 0 && i > 0,
      align: j === 1 ? AlignmentType.RIGHT : AlignmentType.LEFT
    }))
  }));
  children.push(makeTable([3000, 6360], fxRows));
}
if (data.news && data.news.fx_snapshot && (data.news.fx_snapshot.krw_trend || data.news.fx_snapshot.krw_comment)) {
  const fx = data.news.fx_snapshot;
  children.push(p(""));
  children.push(p(`원화 톤: ${fx.krw_trend || '-'}`, { bold: true }));
  if (fx.krw_comment) children.push(p(fx.krw_comment));
}

// ============================================================
// 7. 암호화폐
// ============================================================
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h("7. 암호화폐 시장", 1));
if (data.crypto) {
  const c = data.crypto;

  if (c.market_overview) {
    children.push(h("7.1 시장 개요", 2));
    const mo = c.market_overview;
    const vol = Number(mo.total_volume_24h_usd);
    children.push(bullet(`24시간 거래량: ${isNaN(vol) || !vol ? "-" : "$" + (vol/1e8).toFixed(1) + "억"}`));
    children.push(bullet(`평균 변동: ${mo.avg_change_pct ?? "-"}%`));
    children.push(bullet(`상승 ${mo.coins_up ?? "-"}개 / 하락 ${mo.coins_down ?? "-"}개`));
    if (mo.btc_dominance !== undefined && mo.btc_dominance !== null) children.push(bullet(`BTC Dominance: ${mo.btc_dominance}%`));
  }

  if (c.fear_greed) {
    children.push(h("7.2 공포 & 탐욕 지수", 2));
    const fg = c.fear_greed;
    const fgRows = [
      ["시점", "지수", "분류 / 변화"],
      ["현재",    String(fg.current ?? "-"),    fg.classification || "-"],
      ["1일 전",  String(fg.yesterday ?? "-"),  fgDelta(fg.current, fg.yesterday)],
      ["1주 전",  String(fg.last_week ?? "-"),  fgDelta(fg.current, fg.last_week)],
      ["1개월 전",String(fg.last_month ?? "-"), fgDelta(fg.current, fg.last_month)]
    ].map((r, i) => new TableRow({
      children: r.map((cc, j) => cell(cc, {
        width: [2400, 1800, 5160][j], header: i === 0,
        alt: i > 0 && i % 2 === 0, align: AlignmentType.CENTER,
        bold: j === 0 && i > 0
      }))
    }));
    children.push(makeTable([2400, 1800, 5160], fgRows));
  }

  if (c.kimchi_premium && Array.isArray(c.kimchi_premium.coins) && c.kimchi_premium.coins.length > 0) {
    children.push(h("7.3 김치 프리미엄", 2));
    children.push(p(`기준 환율: 1 USD = ${c.kimchi_premium.rate_usd_krw ?? "-"} KRW`));
    const kpRows = [
      ["코인", "업비트 (KRW)", "바이낸스 (USD)", "프리미엄", "상태"],
      ...c.kimchi_premium.coins.map(coin => [
        coin.symbol ?? "-",
        coin.upbit_krw ? `₩${Number(coin.upbit_krw).toLocaleString()}` : "-",
        coin.binance_usd ? `$${coin.binance_usd}` : "-",
        (coin.premium_pct !== undefined && coin.premium_pct !== null) ? `${coin.premium_pct}%` : "-",
        coin.status || "-"
      ])
    ].map((r, i) => new TableRow({
      children: r.map((cc, j) => cell(cc, {
        width: [1200, 2500, 2400, 1660, 1600][j], header: i === 0,
        alt: i > 0 && i % 2 === 0, align: AlignmentType.CENTER,
        bold: (j === 0 || j === 3) && i > 0,
        color: (j === 3 && i > 0) ? pctColor(c.kimchi_premium.coins[i-1].premium_pct) : undefined
      }))
    }));
    children.push(makeTable([1200, 2500, 2400, 1660, 1600], kpRows));
  }

  if (Array.isArray(c.top_gainers) && c.top_gainers.length > 0) {
    children.push(h("7.4 24h Top Gainers / Losers", 2));
    const gainers = (c.top_gainers || []).slice(0, 5);
    const losers  = (c.top_losers || []).slice(0, 5);
    const maxLen = Math.max(gainers.length, losers.length);
    const tgRows = [
      ["순위", "Top Gainer", "변동", "Top Loser", "변동"]
    ];
    for (let i = 0; i < maxLen; i++) {
      tgRows.push([
        String(i+1),
        gainers[i] ? gainers[i].symbol : "-",
        gainers[i] ? fmtPct(gainers[i].change_pct) : "-",
        losers[i] ? losers[i].symbol : "-",
        losers[i] ? fmtPct(losers[i].change_pct) : "-"
      ]);
    }
    const tgTable = tgRows.map((r, i) => new TableRow({
      children: r.map((cc, j) => cell(cc, {
        width: [1000, 2400, 1900, 2400, 1660][j], header: i === 0,
        alt: i > 0 && i % 2 === 0, align: AlignmentType.CENTER,
        color: (j === 2 && i > 0) ? positiveColor : (j === 4 && i > 0) ? negativeColor : undefined
      }))
    }));
    children.push(makeTable([1000, 2400, 1900, 2400, 1660], tgTable));
  }
}

// ============================================================
// 8. 한국 5대 증권사
// ============================================================
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h("8. 한국 5대 증권사 리서치 (강점·채널·시각)", 1));

const secLabels = {
  shinhan: "신한투자증권",
  miraeasset: "미래에셋증권",
  samsung: "삼성증권",
  korea_inv: "한국투자증권",
  kiwoom: "키움증권"
};
const secViewFields = {
  shinhan: { field: 'asset_allocation_view', label: '자산배분 시각' },
  miraeasset: { field: 'etf_emerging_view', label: 'ETF·신흥국 시각' },
  samsung: { field: 'derivatives_view', label: '파생·선물 시각' },
  korea_inv: { field: 'ib_china_view', label: 'IB·중국 시각' },
  kiwoom: { field: 'global_etf_view', label: '글로벌 ETF·신흥국 시각' }
};

if (data.securities) {
  let idx = 0;
  for (const key of Object.keys(secLabels)) {
    const sec = data.securities[key];
    if (!sec) continue;
    idx++;
    children.push(h(`8.${idx} ${secLabels[key]}`, 2));
    if (sec.strength) children.push(p(`핵심 강점: ${sec.strength}`, { bold: true, color: "1E40AF" }));
    if (Array.isArray(sec.channels) && sec.channels.length > 0) {
      children.push(p(`주요 채널: ${sec.channels.join(' / ')}`, { italics: true, color: "475569" }));
    }
    if (sec.key_message) children.push(p(`오늘의 메시지: ${sec.key_message}`));
    const viewMeta = secViewFields[key];
    if (viewMeta && sec[viewMeta.field]) {
      children.push(p(`${viewMeta.label}: ${sec[viewMeta.field]}`, { color: "0F766E" }));
    }
    if (Array.isArray(sec.key_reports) && sec.key_reports.length > 0) {
      children.push(p("대표 리포트:", { bold: true, after: 40 }));
      sec.key_reports.forEach(r => children.push(bullet(r)));
    } else {
      children.push(p("(리포트 수집 실패 - 사이트 접근 제한)", { italics: true, color: "94A3B8" }));
    }
  }
  if (Array.isArray(data.securities.common_themes) && data.securities.common_themes.length > 0) {
    children.push(h("8.6 5사 공통 핵심 주제", 2));
    data.securities.common_themes.forEach(t => children.push(bullet(t)));
  }
  if (data.securities.investor_type_recommendation) {
    children.push(h("8.7 투자자 유형별 추천 조합", 2));
    const rec = data.securities.investor_type_recommendation;
    const recMap = [
      ["장기 자산배분형", rec.long_term_allocator],
      ["해외주식 종목 픽킹", rec.overseas_stock_picker],
      ["단기 트레이더", rec.short_term_trader],
      ["ETF·패시브 투자자", rec.etf_passive],
      ["중국 집중 투자자", rec.china_focused]
    ];
    const recRows = [["유형", "추천 조합"], ...recMap].map((r, i) => new TableRow({
      children: r.map((cc, j) => cell(cc || "-", {
        width: [2800, 6560][j], header: i === 0,
        alt: i > 0 && i % 2 === 0, bold: j === 0 && i > 0
      }))
    }));
    children.push(makeTable([2800, 6560], recRows));
  }
}

// ============================================================
// 9. 글로벌 주요 IB 리서치
// ============================================================
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h("9. 글로벌 주요 IB 리서치 (UBS·GS·JPM·MS·BlackRock)", 1));

const gsecLabels = {
  ubs: "UBS",
  goldman: "Goldman Sachs",
  jpmorgan: "J.P. Morgan",
  morgan_stanley: "Morgan Stanley",
  blackrock: "BlackRock"
};
const gsecViewFields = {
  ubs: { field: 'house_view', label: 'CIO 하우스 뷰' },
  goldman: { field: 'macro_commodity_view', label: '매크로·원자재 시각' },
  jpmorgan: { field: 'global_strategy_view', label: '글로벌 전략 시각' },
  morgan_stanley: { field: 'us_equity_view', label: '미국주식 전략 시각' },
  blackrock: { field: 'etf_allocation_view', label: 'ETF·자산배분 시각' }
};

if (data.global_securities) {
  let gidx = 0;
  for (const key of Object.keys(gsecLabels)) {
    const sec = data.global_securities[key];
    if (!sec) continue;
    gidx++;
    children.push(h(`9.${gidx} ${gsecLabels[key]}`, 2));
    if (sec.strength) children.push(p(`핵심 강점: ${sec.strength}`, { bold: true, color: "1E40AF" }));
    if (Array.isArray(sec.channels) && sec.channels.length > 0) {
      children.push(p(`공개 채널: ${sec.channels.join(' / ')}`, { italics: true, color: "475569" }));
    }
    if (sec.key_message) children.push(p(`오늘의 메시지: ${sec.key_message}`));
    const gvMeta = gsecViewFields[key];
    if (gvMeta && sec[gvMeta.field]) {
      children.push(p(`${gvMeta.label}: ${sec[gvMeta.field]}`, { color: "0F766E" }));
    }
    if (Array.isArray(sec.key_reports) && sec.key_reports.length > 0) {
      children.push(p("대표 발간물:", { bold: true, after: 40 }));
      sec.key_reports.forEach(r => children.push(bullet(r)));
    } else {
      children.push(p("(수집 실패 또는 비공개 - 공개 채널 한정 수집)", { italics: true, color: "94A3B8" }));
    }
  }
  if (Array.isArray(data.global_securities.common_themes) && data.global_securities.common_themes.length > 0) {
    children.push(h("9.6 글로벌 IB 공통 핵심 주제", 2));
    data.global_securities.common_themes.forEach(t => children.push(bullet(t)));
  }
  if (data.global_securities.wall_street_consensus) {
    children.push(h("9.7 월가 컨센서스", 2));
    children.push(p(data.global_securities.wall_street_consensus));
  }
  children.push(p("※ 해외 IB 원문 리포트는 고객 전용으로, 본 섹션은 각 사 공개 Insights 채널과 언론 보도 기반 하우스 뷰 요약입니다.", { italics: true, color: "94A3B8", size: 18 }));
} else {
  children.push(p("(글로벌 IB 리서치 데이터 없음)"));
}

// ============================================================
// 10. 종합 분석
// ============================================================
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h("10. 종합 분석 - 매크로·테마·리스크", 1));
if (data.analysis) {
  const a = data.analysis;
  if (a.macro_view) {
    children.push(h("10.1 매크로 톤", 2));
    children.push(p(a.macro_view));
  }
  if (Array.isArray(a.key_themes) && a.key_themes.length > 0) {
    children.push(h("10.2 핵심 테마", 2));
    const thRows = [["테마", "방향", "코멘트"]];
    a.key_themes.forEach(t => thRows.push([t.theme || "-", t.direction || "-", t.comment || "-"]));
    children.push(makeTable([2400, 1400, 5560], thRows.map((r, i) => new TableRow({
      children: r.map((cc, j) => cell(cc, {
        width: [2400, 1400, 5560][j], header: i === 0,
        alt: i > 0 && i % 2 === 0, bold: (j === 0 || j === 1) && i > 0,
        align: j === 1 ? AlignmentType.CENTER : AlignmentType.LEFT
      }))
    }))));
  }
  if (Array.isArray(a.key_risks) && a.key_risks.length > 0) {
    children.push(h("10.3 핵심 리스크", 2));
    a.key_risks.forEach(r => children.push(bullet(r, { color: negativeColor })));
  }
}

// ============================================================
// 11. 자산별 견해
// ============================================================
if (data.analysis && data.analysis.asset_view) {
  children.push(new Paragraph({ children: [new PageBreak()] }));
  children.push(h("11. 자산별 단·중·장기 견해", 1));
  const av = data.analysis.asset_view;
  const avMap = [
    ["미국 주식", av.us_equity],
    ["한국 주식", av.kr_equity],
    ["중국 주식", av.china_equity],
    ["일본 주식", av.japan_equity],
    ["신흥시장 주식", av.em_equity],
    ["유럽 주식", av.europe_equity],
    ["한국 채권", av.kr_treasury],
    ["美 국채", av.us_treasury],
    ["금 (Gold)", av.gold],
    ["원유 (Oil)", av.oil],
    ["비트코인 (BTC)", av.btc]
  ];
  const avRows = [["자산군", "단·중·장기 견해"], ...avMap].map((r, i) => new TableRow({
    children: r.map((cc, j) => cell(cc || "-", {
      width: [2400, 6960][j], header: i === 0,
      alt: i > 0 && i % 2 === 0, bold: j === 0 && i > 0
    }))
  }));
  children.push(makeTable([2400, 6960], avRows));
}

// ============================================================
// 12. 추천 포트폴리오
// ============================================================
if (data.analysis && data.analysis.portfolios) {
  children.push(new Paragraph({ children: [new PageBreak()] }));
  children.push(h("12. 추천 포트폴리오 (공격형 · 중립형 · 안정형)", 1));
  children.push(p("아래 포트폴리오는 본 시황 분석을 바탕으로 한 모델 예시이며 개인의 위험감내도·투자목표·세금 상황에 따라 조정해야 한다.", { italics: true, color: "64748B" }));
  const pf = data.analysis.portfolios;
  const order = [
    { key: 'aggressive',   color: 'DC2626' },
    { key: 'balanced',     color: '1E40AF' },
    { key: 'conservative', color: '059669' }
  ];
  order.forEach((o, idx) => {
    const pfObj = pf[o.key];
    if (!pfObj) return;
    children.push(h(`12.${idx+1} ${pfObj.label || o.key}`, 2));
    const meta = [
      ['기대수익', pfObj.expected_return],
      ['최대 낙폭(MDD)', pfObj.max_drawdown],
      ['리밸런싱 주기', pfObj.rebalance]
    ];
    meta.forEach(([k,v]) => { if (v) children.push(bullet(`${k}: ${v}`)); });
    if (Array.isArray(pfObj.allocation)) {
      const wsum = pfObj.allocation.reduce((s,a)=>s+(Number(a.weight_pct)||0),0);
      if (wsum !== 100) console.error(`  (경고) ${o.key} 포트폴리오 비중 합계 ${wsum}% (≠100%)`);
      const allocRows = [["자산", "비중", "구체적 방안 (종목·ETF)"], ...pfObj.allocation.map(a => [
        a.asset || "-", `${a.weight_pct ?? "-"}%`, a.vehicle || "-"
      ])].map((r, i) => new TableRow({
        children: r.map((cc, j) => cell(cc, {
          width: [3400, 1200, 4760][j], header: i === 0,
          alt: i > 0 && i % 2 === 0,
          bold: (j === 0 || j === 1) && i > 0,
          align: j === 1 ? AlignmentType.CENTER : AlignmentType.LEFT
        }))
      }));
      children.push(makeTable([3400, 1200, 4760], allocRows));
      children.push(p(""));
    }
  });
}

// ============================================================
// 13. 액션 아이템
// ============================================================
if (data.analysis && Array.isArray(data.analysis.action_items) && data.analysis.action_items.length > 0) {
  children.push(new Paragraph({ children: [new PageBreak()] }));
  children.push(h("13. 액션 아이템 - 단기·중기·장기 체크리스트", 1));
  data.analysis.action_items.forEach(item => children.push(bullet(item)));
}

// ============================================================
// 14. 주의 사항 및 출처
// ============================================================
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h("14. 주의 사항 및 출처", 1));
children.push(p("본 보고서는 Claude AI Research(Cowork)가 다양한 공개 데이터(Yahoo Finance, CoinGecko, 한국경제, 5대 증권사 공개 리서치 등)를 자동 수집·종합해 생성한 참고용 자료입니다. 모든 수치는 보고서 기준일의 시장 데이터이며, 시점에 따라 변동될 수 있습니다.", { italics: true }));
children.push(p("본 보고서의 어떤 내용도 특정 종목 매수·매도 권유나 보장된 투자 수익을 약속하지 않으며, 포트폴리오 추천은 모델 예시일 뿐 개인의 위험감내도·투자목표·세금 상황에 맞춰 조정·검증이 필요합니다. 투자 판단의 최종 책임은 이용자에게 있습니다.", { italics: true, color: "64748B" }));
children.push(p(""));
children.push(p("주요 출처: Yahoo Finance / CoinGecko / 한국경제 / 신한투자증권 / 미래에셋증권 / 삼성증권 / 한국투자증권 / 키움증권", { size: 18, color: "94A3B8" }));

// ---------- Doc ----------
const doc = new Document({
  styles: {
    default: { document: { run: { font: "맑은 고딕", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "맑은 고딕", color: "1E3A8A" },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "맑은 고딕", color: "1E40AF" },
        paragraph: { spacing: { before: 240, after: 140 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "맑은 고딕", color: "334155" },
        paragraph: { spacing: { before: 180, after: 100 }, outlineLevel: 2 } },
    ]
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
                   alignment: AlignmentType.LEFT,
                   style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } } },
    headers: { default: new Header({ children: [new Paragraph({
      alignment: AlignmentType.RIGHT,
      children: [new TextRun({ text: `글로벌 금융시장 종합 시황 보고서 | ${reportDate}`, size: 18, color: "64748B" })]
    })]})},
    footers: { default: new Footer({ children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [
        new TextRun({ text: "Page ", size: 18, color: "64748B" }),
        new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "64748B" }),
        new TextRun({ text: " / ", size: 18, color: "64748B" }),
        new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 18, color: "64748B" }),
        new TextRun({ text: "  |  namoobi-market-report v3.2", size: 18, color: "64748B" })
      ]
    })]})},
    children
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, buffer);
  console.log(`✅ 보고서 생성 완료: ${outPath}`);
  console.log(`   크기: ${buffer.length.toLocaleString()} bytes / 표 ${tableCount}개`);
}).catch(e => {
  console.error("❌ DOCX 생성 실패: " + e.message);
  process.exit(1);
});
// EOF — namoobi-market-report v1.1.0
