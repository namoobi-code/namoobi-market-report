#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# nmr_apply_321.py — "3.1.21 파생시장 포지셔닝 기반 현물 선행신호 분석" 섹션 신설 (자동 생성 훅)
# 멱등(idempotent): 이미 반영된 항목은 건너뛴다. 여러 번 실행해도 안전. 다른 세션 변경은 건드리지 않음.
#   python nmr_apply_321.py           # 적용
#   python nmr_apply_321.py --check   # dry-run(리포트만)
import os, sys, io, re, json, subprocess

ROOT  = os.path.dirname(os.path.abspath(__file__))
SK    = os.path.join(ROOT, "plugins", "namoobi-market-report", "skills", "namoobi-market-report")
SCR   = os.path.join(SK, "scripts")
REF   = os.path.join(SK, "references")
BUILD = os.path.join(SCR, "build_report.js")
MERGE = os.path.join(SCR, "merge.py")
SKILL = os.path.join(SK, "SKILL.md")
CL    = os.path.join(SK, "CHANGELOG.md")
PJ    = os.path.normpath(os.path.join(SK, os.pardir, os.pardir, ".claude-plugin", "plugin.json"))
MP    = os.path.join(ROOT, ".claude-plugin", "marketplace.json")
DRY   = "--check" in sys.argv
TARGET_PLUGIN = "1.16.0"

rows = []
def log(n, s, d=""): rows.append((n, s, d))
def rd(p):
    with io.open(p, encoding="utf-8") as f: return f.read()
def wr(p, s):
    if DRY: return
    with io.open(p, "w", encoding="utf-8", newline="\n") as f: f.write(s)
def replace_once(path, old, new, marker, name):
    if not os.path.exists(path): return log(name, "MISSING", path)
    t = rd(path)
    if marker in t: return log(name, "OK", "이미 반영")
    if old in t: wr(path, t.replace(old, new, 1)); return log(name, "APPLIED", "치환")
    log(name, "FAIL", "앵커 못찾음: " + old[:46].replace(chr(10), " "))
def insert_before(path, anchor, insert, marker, name):
    if not os.path.exists(path): return log(name, "MISSING", path)
    t = rd(path)
    if marker in t: return log(name, "OK", "이미 반영")
    i = t.find(anchor)
    if i < 0: return log(name, "FAIL", "앵커 못찾음: " + anchor[:46])
    wr(path, t[:i] + insert + t[i:]); log(name, "APPLIED", "삽입")
def append_text(path, appendix, marker, name):
    if not os.path.exists(path): return log(name, "MISSING", path)
    t = rd(path)
    if marker in t: return log(name, "OK", "이미 반영")
    wr(path, t + appendix); log(name, "APPLIED", "추가")
def bump_version(path, target, name):
    if not os.path.exists(path): return log(name, "MISSING", path)
    t = rd(path); m = re.search(r'"version"\s*:\s*"([\d.]+)"', t)
    if not m: return log(name, "FAIL", "version 필드 없음")
    cur = m.group(1)
    if cur == target: return log(name, "OK", "이미 " + target)
    wr(path, re.sub(r'("version"\s*:\s*")' + re.escape(cur) + r'(")', r'\g<1>' + target + r'\g<2>', t))
    log(name, "APPLIED", cur + "→" + target)

# ── 1) build_report.js — DERIV_POS_DEFAULT + renderDerivPositioning() 삽입 (M7 기본값 앞) ──
DP_JS = r'''// (v3.47.0) 3.1.21 파생시장 포지셔닝 → 현물 선행신호 — 파생·수급 지표 z-score 스냅샷.
// 라이브(merge markets.deriv_positioning = nmr_deriv_positioning.json) 있으면 대체, 없으면 아래 내장 스냅샷으로 비차단 렌더.
const DERIV_POS_DEFAULT = {
  asof: "가격 2026-07-02 · 미국 COT 2026-06-23(주간) · KOSPI200 수급 2026-07-03 · 미국 옵션 2026-07-04",
  index: [
    {name:"S&P 500", close:"7,483.24", ret1:"+0.00%", ret5:"+1.71%"},
    {name:"Nasdaq 100", close:"29,329.21", ret1:"-1.61%", ret5:"-0.38%"},
    {name:"KOSPI200", close:"1,219.62", ret1:"-8.67%", ret5:"-16.13%"}
  ],
  rows: [
    {label:"선물 베이시스 (bp)", cells:[{v:"+60",z:0.88},{v:"+77",z:1.14},{v:"+174",z:2.84}]},
    {label:"레버리지(美)/외국인(韓) 순", cells:[{v:"-373,468 계약",z:0.72},{v:"-51,062 계약",z:-0.90},{v:"-43,706 억원",z:-1.06}]},
    {label:"자산운용(美)/기관(韓) 순", cells:[{v:"992,729 계약",z:-0.23},{v:"62,908 계약",z:-1.50},{v:"-20,825 억원",z:-1.44}]},
    {label:"선물 OI 변화", cells:[{v:"-599,666 (주)",z:-2.34},{v:"-79,358 (주)",z:-2.40},{v:"+4,676 (5일)",z:0.64}]},
    {label:"풋콜비율 (OI)", cells:[{v:"4.63",z:null},{v:"1.72",z:null},{v:"2.86",z:null}]},
    {label:"IV 스큐", cells:[{v:"+0.028",z:null},{v:"+0.048",z:null},{v:"+7.0",z:-0.36}]},
    {label:"딜러 감마 (GEX)", cells:[{v:"-0.45bn",z:null},{v:"-0.29bn",z:null},{v:"—",z:-0.20}]}
  ],
  signals: [
    "S&P500 선물 OI 변화 z=-2.34 → 디레버리징(청산)",
    "나스닥 자산운용/기관 순 z=-1.50 → 리얼머니 축소(하방 경계)",
    "나스닥 선물 OI 변화 z=-2.40 → 디레버리징(청산)",
    "KOSPI200 선물 베이시스 z=+2.84 → 선물 프리미엄 확대(과매도 반등/위험선호)"
  ],
  market_us: "선물은 위험선호(베이시스 프리미엄)이나 포지셔닝은 방어적 — 양 지수 OI 급감(z≈-2.3~-2.4·디레버리징), 나스닥 자산운용 순매수 z=-1.50(리얼머니 축소·검증 5일 -1.16%·적중 82%), 딜러 GEX 음수(숏감마·변동성 확대).",
  market_kr: "실제 지수 -8.7%(5일 -16.1%) 급락·외국인/기관 동반 순매도인데 선물 베이시스 극단 프리미엄(z=+2.84). 검증상 베이시스 z≥+1.5는 5일 +3.77%·적중 78% 반등 신호 → 가격·수급 약세 vs 베이시스 반등의 상충. 확정은 외국인 순매수 전환(5일 +5.83%·적중 87%) 확인.",
  synthesis: "미국=가격 프리미엄 vs 포지셔닝 방어의 괴리, 한국=현물·수급 급락 vs 선물 극단 프리미엄의 상충. 전반적으로 신중, 한국 베이시스는 과매도 되돌림 가능성. 옵션 지표(PCR·IV스큐·미국 GEX)는 표본 부족으로 참고. 리서치용·투자권유 아님."
};
function renderDerivPositioning(){ const m=data.markets||{};
  const dp=(m.deriv_positioning&&typeof m.deriv_positioning==="object"&&Array.isArray(m.deriv_positioning.rows)&&m.deriv_positioning.rows.length)?m.deriv_positioning:DERIV_POS_DEFAULT;
  if(!dp||!Array.isArray(dp.rows)||!dp.rows.length)return;
  children.push(h("3.1.21 파생시장 포지셔닝 기반 현물 선행신호 분석",3));
  children.push(p("선물 베이시스·순포지션/수급·풋콜비율·IV 스큐·딜러 감마(GEX)를 롤링 z-score(60거래일)로 표준화한 현재 스냅샷. |z|≥1.5는 통계적으로 이례적인 신호.",{size:15,italics:true,color:"94A3B8"}));
  if(dp.asof)children.push(p("기준일 — "+dp.asof,{size:14,color:"64748B"}));
  if(Array.isArray(dp.index)&&dp.index.length){
    children.push(p("① 지수 현황 (종가·수익률)",{bold:true,size:18,color:"1E40AF",before:100}));
    const iw=[3000,2360,2000,2000]; const ir=[hdrRow(["지수","종가","1일","5일"],iw)];
    dp.index.forEach((r,i)=>{const a=i%2===1; ir.push(new TableRow({children:[
      cell(r.name||"-",{width:iw[0],alt:a,bold:true,size:15}),
      cell(r.close||"-",{width:iw[1],alt:a,size:15,align:AlignmentType.CENTER}),
      cell(r.ret1||"-",{width:iw[2],alt:a,size:15,align:AlignmentType.CENTER}),
      cell(r.ret5||"-",{width:iw[3],alt:a,size:15,align:AlignmentType.CENTER})]}));});
    children.push(makeTable(iw,ir)); }
  children.push(p("② 지표별 현재값 · z-스코어  (굵은 셀=|z|≥1.5 신호; 파랑=양수·빨강=음수)",{bold:true,size:18,color:"1E40AF",before:120}));
  const zw=[2760,2200,2200,2200]; const zr=[hdrRow(["지표","S&P 500","Nasdaq 100","KOSPI200"],zw)];
  const fz=(c)=>{ const z=(c&&c.z!=null&&!isNaN(c.z))?Number(c.z):null; const sig=(z!=null&&Math.abs(z)>=1.5);
    return {t:String((c&&c.v)||"-")+"  (z "+(z==null?"—":((z>=0?"+":"")+z.toFixed(2)))+")", s:sig, c:sig?(z>=0?"1D4ED8":"B91C1C"):"0F172A"}; };
  dp.rows.forEach((r,i)=>{const a=i%2===1; const cs=(r.cells||[]).map(fz);
    zr.push(new TableRow({children:[cell(r.label||"-",{width:zw[0],alt:a,bold:true,size:14})].concat(
      cs.map((x,j)=>cell(x.t,{width:zw[j+1],alt:a,align:AlignmentType.CENTER,size:13,bold:x.s,color:x.c})))}));});
  children.push(makeTable(zw,zr));
  const sg=Array.isArray(dp.signals)?dp.signals:[];
  children.push(p("③ 활성 신호 (|z|≥1.5)",{bold:true,size:18,color:(sg.length?"B91C1C":"1E40AF"),before:100}));
  if(sg.length)sg.forEach(s=>children.push(p("• "+s,{size:16,bold:true,color:"B45309"})));
  else children.push(p("현재 |z|≥1.5 신호 없음",{size:16,color:"334155"}));
  if(dp.market_us){ children.push(p("④ 시장해석",{bold:true,size:18,color:"1E40AF",before:100}));
    children.push(p("· 미국: "+dp.market_us,{size:16,color:"334155"})); }
  if(dp.market_kr)children.push(p("· KOSPI200: "+dp.market_kr,{size:16,color:"334155"}));
  if(dp.synthesis){ children.push(p("⑤ 종합",{bold:true,size:18,color:"1E40AF",before:80}));
    children.push(p(dp.synthesis,{size:16})); }
  children.push(p("데이터: yfinance · CFTC COT · 네이버 투자자별 매매동향 · data.go.kr(파생상품·지수 시세) · 파이프라인 deriv_signals/. 리서치용·투자권유 아님.",{size:13,italics:true,color:"94A3B8"}));
  children.push(p("")); }

'''
insert_before(BUILD, "const M7_OUTLOOK_DEFAULT = {", DP_JS,
              "function renderDerivPositioning(", "build: renderDerivPositioning 함수+기본값")

# ── 2) build_report.js — 호출부 (renderM7Outlook 직후) ──
replace_once(BUILD,
    "renderM7Outlook();   // 3.1.20 미국 빅테크(M7) 실적 전망 — 가이던스·추정치 변화 시장 신호 (매일)",
    "renderM7Outlook();   // 3.1.20 미국 빅테크(M7) 실적 전망 — 가이던스·추정치 변화 시장 신호 (매일)\n  renderDerivPositioning();   // 3.1.21 파생시장 포지셔닝→현물 선행신호 (스냅샷·z매트릭스·활성신호·해석)",
    "renderDerivPositioning();", "build: renderDerivPositioning 호출")

# ── 3) merge.py — nmr_deriv_positioning.json 로드 + 라이브 오버라이드 ──
replace_once(MERGE,
    "m7o = L('nmr_m7.json')  # (v3.46) 3.1.20 미국 빅테크(M7) 실적전망 라이브 데이터(있으면 내장 스냅샷 대체)",
    "m7o = L('nmr_m7.json')  # (v3.46) 3.1.20 미국 빅테크(M7) 실적전망 라이브 데이터(있으면 내장 스냅샷 대체)\ndpv = L('nmr_deriv_positioning.json')  # (v3.47) 3.1.21 파생 포지셔닝 라이브(있으면 내장 스냅샷 대체)",
    "nmr_deriv_positioning.json", "merge: deriv_positioning 로드")
replace_once(MERGE,
    "if isinstance(m7o, dict) and m7o.get('rows'): m['m7_outlook'] = m7o  # 3.1.20 라이브 오버라이드",
    "if isinstance(m7o, dict) and m7o.get('rows'): m['m7_outlook'] = m7o  # 3.1.20 라이브 오버라이드\nif isinstance(dpv, dict) and (dpv.get('rows') or dpv.get('index')): m['deriv_positioning'] = dpv  # 3.1.21 라이브 오버라이드",
    "m['deriv_positioning']", "merge: deriv_positioning 오버라이드")

# ── 4) SKILL.md — 3.1.21 스펙 ──
SKILL_SPEC = "**3.1.21 파생시장 포지셔닝 기반 현물 선행신호 분석 (v3.47 신설 — 매일)** — KOSPI200·S&P500·Nasdaq100의 선물 베이시스·순포지션/수급(美 CFTC COT 레버리지·자산운용 / 韓 외국인·기관)·풋콜비율·IV 스큐·딜러 감마(GEX)를 **롤링 z-score(60거래일)** 로 표준화한 현재 스냅샷(3.1.20 뒤). **매일 갱신**: `deriv_signals/daily_update.py`(무료 소스 yfinance·CFTC COT·네이버 수급·data.go.kr 파생/지수, `secrets.env`의 DATA_GO_KR_KEY)로 DB 갱신 → `deriv_signals/export_snapshot.py` → `nmr_deriv_positioning.json` → merge `markets.deriv_positioning` → 빌더 `renderDerivPositioning`(① 지수 현황 ② 값·z 매트릭스 |z|≥1.5 강조 ③ 활성 신호 ④ 시장해석 ⑤ 종합). 미수집 시 빌더 내장 스냅샷(DERIV_POS_DEFAULT)으로 **비차단 렌더**. 신호=|z|≥1.5(굵게·파랑 양수/빨강 음수). 선행성 검증(신호일→1/3/5일 현물수익률)은 `deriv_signals/` 파이프라인이 산출. 상세=`references/agents.md`·`references/data-schema.md`. `DerivPositioningAgent`(Phase 1, model:sonnet).\n"
insert_before(SKILL, "**3.2.1 한국 지수 일봉 캔들** — 차트는 반드시",
              SKILL_SPEC, "3.1.21 파생시장 포지셔닝", "docs: SKILL.md 스펙")

# ── 5) references — data-schema.md / agents.md (안전 append) ──
DS = os.path.join(REF, "data-schema.md")
DS_APPEND = ("\n\n## nmr_deriv_positioning.json — 3.1.21 파생 포지셔닝 스냅샷 (v3.47)\n\n"
    "`deriv_signals/export_snapshot.py` 가 `deriv_signals.db` 에서 산출. 빌더 `renderDerivPositioning` 스키마.\n\n"
    "```json\n"
    '{\n  "asof": "가격 YYYY-MM-DD · 미국 COT YYYY-MM-DD(주간) · KOSPI200 수급 YYYY-MM-DD · 미국 옵션 YYYY-MM-DD",\n'
    '  "index": [{"name":"S&P 500","close":"7,483.24","ret1":"+0.00%","ret5":"+1.71%"}],\n'
    '  "rows":  [{"label":"선물 베이시스 (bp)","cells":[{"v":"+60","z":0.88},{"v":"+77","z":1.14},{"v":"+174","z":2.84}]}],\n'
    '  "signals": ["KOSPI200 선물 베이시스 z=+2.84 → 선물 프리미엄 확대(과매도 반등)"] ,\n'
    '  "market_us": "…", "market_kr": "…", "synthesis": "…"\n}\n'
    "```\n\n- `rows[].cells` 순서 = S&P500 / Nasdaq100 / KOSPI200. `z`=null 이면 렌더러가 `z —`(표본 축적 전, 미국 옵션 등).\n")
append_text(DS, DS_APPEND, "nmr_deriv_positioning.json", "docs: data-schema")

AG = os.path.join(REF, "agents.md")
AG_APPEND = ("\n\n## DerivPositioningAgent — 3.1.21 파생시장 포지셔닝 (v3.47, Phase 1, model:sonnet)\n\n"
    "역할: 파생·수급 포지셔닝 z-score 스냅샷을 매일 산출.\n\n"
    "1) `deriv_signals/` 에서 `python daily_update.py` 실행 — 무료 소스(yfinance 현물·선물·VIX·옵션, CFTC COT, 네이버 투자자별 매매동향, data.go.kr 파생상품·지수시세)로 `deriv_signals.db` 갱신. data.go.kr 키는 `deriv_signals/secrets.env` 의 `DATA_GO_KR_KEY`(gitignore).\n"
    "2) `python export_snapshot.py <실행폴더>/nmr_deriv_positioning.json` — DB에서 지수현황·z매트릭스·활성신호·해석 산출.\n"
    "3) merge 가 `markets.deriv_positioning` 로 로드 → 빌더 `renderDerivPositioning`. 미수집 시 내장 스냅샷(DERIV_POS_DEFAULT)으로 비차단.\n"
    "※ COT는 주간(화요일 기준·금요일 공표)이라 미국 순포지션만 주간, 나머지(현물·베이시스·수급·옵션)는 일별.\n")
append_text(AG, AG_APPEND, "DerivPositioningAgent", "docs: agents")

# ── 6) CHANGELOG.md — v3.47.0 ──
CL_BLOCK = (
"## v3.47.0 (plugin 1.16.0) — 3.1.21 파생시장 포지셔닝 기반 현물 선행신호 분석 신설 (매일)\n"
"- **신설 3.1.21**: 3.1.20 뒤. KOSPI200·S&P500·Nasdaq100의 선물 베이시스·순포지션/수급(美 COT / 韓 외국인·기관)·풋콜비율·IV스큐·딜러감마(GEX)를 z-score(60거래일)로 표준화한 스냅샷(① 지수현황 ② 값·z 매트릭스 ③ 활성신호 ④ 시장해석 ⑤ 종합).\n"
"- **파이프라인**: `deriv_signals/`(daily_update.py→DB, export_snapshot.py→nmr_deriv_positioning.json) → merge `markets.deriv_positioning` → 빌더 `renderDerivPositioning`. 미수집 시 내장 DERIV_POS_DEFAULT 비차단. 데이터=yfinance·CFTC COT·네이버 수급·data.go.kr(파생·지수).\n"
"- **선행성 검증**: 신호일→1/3/5일 현물수익률 hit·IC (예: 외국인 순매수 z≥+1.5 → 5일 +5.83%·적중 87%, KOSPI200 베이시스 z≥+1.5 → +3.77%·78%).\n\n"
)
replace_once(CL, "# Namoobi Market Report — 변경이력 (CHANGELOG)\n\n",
             "# Namoobi Market Report — 변경이력 (CHANGELOG)\n\n" + CL_BLOCK,
             "v3.47.0", "docs: CHANGELOG")

# ── 7) 버전 범프 → 1.16.0 ──
bump_version(PJ, TARGET_PLUGIN, "ver: plugin.json")
bump_version(MP, TARGET_PLUGIN, "ver: marketplace.json")

# ── 리포트 ──
print("\n===== 3.1.21 적용/검증 리포트  (mode: %s) =====" % ("CHECK(dry-run)" if DRY else "APPLY"))
w = max(len(n) for n, _, _ in rows)
okc = apc = flc = 0
for n, s, d in rows:
    print("  %s  %-*s  %-8s %s" % ({"OK": "✓", "APPLIED": "✚", "FAIL": "✗", "MISSING": "✗"}.get(s, "?"), w, n, s, d))
    okc += s == "OK"; apc += s == "APPLIED"; flc += s in ("FAIL", "MISSING")
print("  ---- OK %d · APPLIED %d · FAIL %d ----" % (okc, apc, flc))

print("\n===== 자체검증 =====")
try:
    r = subprocess.run(["node", "--check", BUILD], capture_output=True, text=True)
    print("  %s build_report.js (node --check)" % ("✓" if r.returncode == 0 else "✗ " + (r.stderr.strip().splitlines()[-1] if r.stderr else "")))
except FileNotFoundError:
    print("  · node 미검출 — build_report.js 구문검사 스킵")
try:
    import ast; ast.parse(rd(MERGE)); print("  ✓ merge.py (ast.parse)")
except Exception as e:
    print("  ✗ merge.py:", e)
b = rd(BUILD) if os.path.exists(BUILD) else ""; mm = rd(MERGE) if os.path.exists(MERGE) else ""
for cond, label in [("function renderDerivPositioning(" in b, "renderDerivPositioning 함수"),
                    ("renderDerivPositioning();" in b, "renderDerivPositioning 호출"),
                    ("m['deriv_positioning']" in mm, "merge deriv_positioning")]:
    print("  %s %s" % ("✓" if cond else "✗", label))
print("\n다음: FAIL 0 확인 → git add (plugins/ + deriv_signals/export_snapshot.py) → 커밋 → push → 플러그인 v%s 재설치" % TARGET_PLUGIN)
if DRY: print("※ --check 모드. 실제 적용: python nmr_apply_321.py")
