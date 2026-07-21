// verify_report.js (v3.6.33 - v3.49 3.1 재배열: 새 번호 3.1.1금리 3.1.2물가 3.1.3고용 3.1.4CLI 3.1.5순환변동치 3.1.6FactSet 3.1.7M7 3.1.8CAPEX 3.1.9HBM 3.1.10관세청 3.1.11반도체사이클 3.1.12심리 3.1.13파생) -- pre-send quality gate.
// Goal (2026-06-19 user feedback): never silently ship a section that is broken
// (missing chart / "-" / stale). If any problem is found, BLOCK sending and ask the user.
// ASCII-only on purpose: the sandbox mount intermittently corrupts multibyte (Korean) chars
// when node reads the file, which broke parsing. Messages reference section numbers (req1..req8).
// Usage: node verify_report.js <report_data.json> [WORK_dir(charts + nmr_*.json)]
// Output: JSON {ok, problems:[], warnings:[]} to stdout. exit 1 if problems (=do NOT send).
const fs=require('fs'), path=require('path');
const J=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const rp=process.argv[2];
const WORK=process.argv[3]||path.dirname(rp);
const problems=[], warnings=[];
let d={}; try{ d=J(rp); }catch(e){ console.log(JSON.stringify({ok:false,problems:["report_data read failed: "+e.message],warnings:[]})); process.exit(1); }
const m=d.markets||{};
const chartsDir=fs.existsSync(path.join(WORK,'charts'))?path.join(WORK,'charts'):WORK;
const cExists=(rel)=>{ if(!rel)return false; try{ return fs.statSync(path.join(chartsDir,path.basename(rel))).size>800; }catch(e){ return false; } };
const fileN=(rel)=>{ try{ const x=J(path.join(WORK,rel)); return Array.isArray(x)?x.length:((x.series||[]).length||0); }catch(e){ return 0; } };

// req1: 3.1.1 KOSPI/KOSDAQ must be daily candle (kospi_tech/kosdaq_tech), not the flows fallback
const ki=m.korea_investors||{};
['kospi','kosdaq'].forEach(k=>{
  const ch=ki[k+'_chart']||'';
  if(!cExists(ch)) problems.push(`[req1] 3.2.1 ${k} chart missing/broken: ${ch||'(none)'}`);
  else if(/flows/i.test(ch)) problems.push(`[req1] 3.2.1 ${k} chart is NOT a daily candle (flows fallback): ${ch}; use gen_kr_candle (candle+volume+cumulative net-buy)`);
  else { try{ if(fs.existsSync(path.join(chartsDir,k+'_tech.weekly'))) problems.push(`[req1] 3.2.1 ${k} chart is WEEKLY line fallback (mplfinance missing) - must be daily candle; gen_kr_candle now auto-installs mplfinance`); }catch(e){} }
});
// req2: 3.1.5 leading-index long series + chart
if(!cExists(m.korea_leading_chart||'charts/leading_cycle.png')) problems.push('[req2] 3.1.5 leading-index chart missing/broken');
{ const n=fileN('nmr_leading_series.json'); if(n<12) problems.push(`[req2] 3.1.5 leading-index long series too short (${n}<12); collect INDEXerGO monthly long series`); }
// req3: 3.2.3 8 theme trend charts
const THEMES=["a","b","c","d","e","f","g","h"]; // placeholder count; resolve by report data order
const tRows=Array.isArray(m.korea_theme_rows)?m.korea_theme_rows:[];
if(tRows.length<16) problems.push(`[req3] 3.2.3 theme rows ${tRows.length}<16 (v3.65: +2차전지/엔터)`);
let tMiss=tRows.filter(t=>!cExists(t.chart)).map(t=>t.theme||'?');
if(tMiss.length) problems.push(`[req3] 3.2.3 theme trend charts missing ${tMiss.length}/${tRows.length}: ${tMiss.join(', ')}`);
// req3b (v3.64): 3.1.14 국내 유동성·레버리지 — kr_liquidity + 판정 + 차트 4종
{ const kl=m.kr_liquidity;
  if(!kl||!kl.as_of) problems.push('[req3b] 3.1.14 markets.kr_liquidity missing (fetch_krliq.py -> gen_krliq_charts.py)');
  else { if(!kl.verdict||!kl.verdict.label) problems.push('[req3b] 3.1.14 verdict missing (deposit/turnover 5d)');
    for(let i=1;i<=4;i++) if(!cExists('charts/krliq_'+i+'.png')) problems.push('[req3b] 3.1.14 chart krliq_'+i+'.png missing/broken'); } }
// req4: semi stocks (>=10) + charts
const ss=Array.isArray(m.semi_ai_stocks)?m.semi_ai_stocks:[];
if(ss.length<10) problems.push(`[req4] 3.2.3 semi stocks ${ss.length}<10`);
{ const miss=ss.filter((x,i)=>!cExists(x.chart||('charts/semi_s_'+i+'.png'))).length; if(miss) problems.push(`[req4] 3.2.3 semi-stock trend charts missing ${miss}/${ss.length}`); }
// req5: semi ETFs (==20) + charts
const se=Array.isArray(m.semi_ai_etfs)?m.semi_ai_etfs:[];
if(se.length<20) problems.push(`[req5] 3.2.3 semi ETFs ${se.length}<20 (always show AUM top 20)`);
{ const miss=se.filter((x,i)=>!cExists(x.chart||('charts/semi_e_'+i+'.png'))).length; if(miss) problems.push(`[req5] 3.2.3 semi-ETF trend charts missing ${miss}/${se.length}`); }
// req6: CAPEX present (empty-year column drop handled in builder)
if(!(m.bigtech_capex&&Array.isArray(m.bigtech_capex.rows)&&m.bigtech_capex.rows.length>=4)) warnings.push('[req6] 3.1.8 CAPEX rows<4');
// req7: FOMC dot plot completeness (no empty jun/mar)
const f=m.fomc_dotplot;
if(!f||!Array.isArray(f.rows)||!f.rows.length) problems.push('[req7] 3.1.1 FOMC dot plot data missing');
else { const miss=[]; f.rows.forEach(r=>['jun','mar'].forEach(c=>{ const v=r[c]; if(v==null||String(v).trim()===''||String(v).trim()==='-')miss.push((r.item||'?')+'.'+c); })); if(miss.length) problems.push('[req7] 3.1.1 dot plot empty values: '+miss.join(', ')); }
// req8: broker/IB freshness. KR brokers: daily<=1/weekly<=3 (Mon/weekend allow Friday). Global IB: weekly cadence <=7.
function fresh(dateStr,kind){ if(!dateStr)return true; const ref=new Date((d.metadata&&d.metadata.report_date)||Date.now()); const dt=new Date(String(dateStr).slice(0,10)); if(isNaN(dt))return true; let max=(kind==='daily')?1:(kind==='weekly7'?7:3); const dow=ref.getDay(); if(dow===1)max+=2; if(dow===6)max+=1; if(dow===0)max+=2; const diff=Math.floor((ref-dt)/86400000); return diff<=max; }
function houses(obj,label,kind){ if(!obj||typeof obj!=='object')return; Object.keys(obj).forEach(k=>{ const v=obj[k]; if(!v||typeof v!=='object'||Array.isArray(v))return; const krs=v.key_reports; if(Array.isArray(krs)) krs.forEach(r=>{ const dt=(r&&r.date)||''; if(dt&&!fresh(dt,kind)) problems.push(`[req8] ${label}.${k} report stale: ${dt} (exceeds freshness)`); }); }); }
houses(d.securities,'KR-brokers','weekly');
houses(d.global_securities,'GlobalIB','weekly7');

// req9 (absorbed from build_report --validate): major sections present (advisory)
['news','markets','commodities','crypto','analysis'].forEach(s=>{ if(!d[s]) warnings.push('[req9] section missing: '+s); });
// req10: top_news grounding -- source_url present
{ const tn=(d.news&&d.news.top_news)||[]; const n=tn.filter(x=>!(x&&x.source_url)).length; if(tn.length&&n) warnings.push('[req10] top_news without source_url: '+n+'/'+tn.length); }
// req11: portfolio basis present (no false precision)
{ const pf=(d.analysis&&d.analysis.portfolios)||{}; Object.keys(pf).forEach(k=>{ const p=pf[k]; if(p&&typeof p==='object'&&!Array.isArray(p)&&!p.basis) warnings.push('[req11] portfolio '+k+' missing basis'); }); }
// req12: events_calendar date sanity -- not past-dated vs report_date
{ const ev=(d.news&&d.news.events_calendar)||[]; const ref=new Date((d.metadata&&d.metadata.report_date)||Date.now()); const r0=new Date(ref.toDateString()); let pst=0; ev.forEach(e=>{ const x=new Date(String((e&&e.date)||'').slice(0,10)); if(!isNaN(x)&&x<r0) pst++; }); if(pst) warnings.push('[req12] events_calendar past-dated entries: '+pst); }

{ const u=(m.macro&&m.macro._db_unverified)||null; if(u){ const n=((u.rows_backfilled||[]).length)+((u.series_unverified||[]).length); if(n) warnings.push("[req13] 변경 미확인(당일 미수집·DB 백필): "+n+"건 — 조용히 통과 아님, 다음 실행 재조사 권고"); } }
// req14: macro daily cells present (US10Y/US2Y/fed_funds current) -- catches stale/"-" macro (req1/req4)
{ const r=(m.macro&&m.macro.rates)||{}; const u10=r.us10y||{},u2=r.us2y||{},ff=r.fed_funds||{};
  if(u10.current==null) problems.push('[req14] 3.1.1 US10Y current missing');
  if(u2.current==null) problems.push('[req14] 3.1.1 US2Y current missing');
  if(ff.current==null) problems.push('[req14] 3.1.1 FOMC fed_funds current missing');
  if(ff.asof){ const ref=new Date((d.metadata&&d.metadata.report_date)||Date.now()); const a=new Date(String(ff.asof).slice(0,10)); if(!isNaN(a)&&Math.floor((ref-a)/86400000)>70) problems.push('[req14] FOMC fed_funds asof stale: '+ff.asof); } }
// req15 (2026-07-12 개정): HY 표 폐지 — current(코멘트용)+차트만 검사(d1~y1 앵커 요구 제거)
{ const hy=m.hy_spread||{}; if(hy.current==null&&hy.hy_oas==null) problems.push('[req15] 3.1.1 HY spread current missing');
  if(!cExists((hy.chart)||'charts/hy_oas.png')) problems.push('[req15] 3.1.1 HY chart missing/broken: charts/hy_oas.png'); }
// req16: FOMC past meetings must be actual (no estimate marker) -- catches req5
{ const fm=((m.macro&&m.macro.rates)||{}).fomc_meetings||[]; const ref=new Date((d.metadata&&d.metadata.report_date)||Date.now()); let est=0;
  const EST=/\uCD94\uC815|estimate|\(E\)/;
  fm.forEach(x=>{ const dt=new Date(String((x&&x.date)||'').slice(0,10)); const nt=String((x&&(x.note||x.stance))||''); if(!isNaN(dt)&&dt<ref&&EST.test(nt)) est++; });
  if(est) problems.push('[req16] FOMC past meetings marked estimate (need actual decisions): '+est); }
// req16b (2026-07-12): FOMC 회의 구성 — 과거 1년 실제 결정 >=6건 + 예정 <=3건
{ const fm=((m.macro&&m.macro.rates)||{}).fomc_meetings||[];
  const today=String((d.metadata&&d.metadata.report_date)||'').slice(0,10);
  const past=fm.filter(x=>String(x&&x.date||'')<=today&&String(x&&x.stance||'')!=='\uC608\uC815');
  const fut=fm.filter(x=>String(x&&x.date||'')>today);
  if(fm.length&&past.length<6) problems.push('[req16b] FOMC past actual decisions '+past.length+'<6 (usmacro fomc_meetings union check)');
  if(fut.length>3) problems.push('[req16b] FOMC upcoming meetings '+fut.length+'>3 (limit to next 3)'); }
// req17: yield curve data present -- catches req2 at data level
{ const yc=(((m.macro||{}).rates||{}).yield_curve)||{}; if(!yc||typeof yc!=='object'||yc.spread==null) problems.push('[req17] 3.1.1 yield_curve(10Y-2Y) data empty'); }
// req18: macro charts must exist (curve/employment/inflation) -- catches req6/req7 regressions
['macro_curve.png','macro_employment.png','macro_inflation.png'].forEach(c=>{ if(!cExists('charts/'+c)) problems.push('[req18] macro chart missing/broken: '+c); });
// req19: 3.1.4 OECD CLI - DB-seeded unified chart (all countries, monthly). Data present => chart must exist.
if(m.oecd_cli&&Array.isArray(m.oecd_cli.months)&&m.oecd_cli.months.length){ if(!cExists((m.oecd_cli.chart)||'charts/oecd_cli.png')) problems.push('[req19] 3.1.4 OECD CLI chart missing/broken: charts/oecd_cli.png (run gen_cli_chart.py)'); }
else warnings.push('[req19] 3.1.4 oecd_cli data missing (db/oecd_cli.json seed) - section omitted');
if(m.customs&&m.customs.series&&Array.isArray(m.customs.months)&&m.customs.months.length){ if(!cExists((m.customs.chart_total)||'charts/수출_전체_24개월.png')||!cExists((m.customs.chart_semi)||'charts/수출_반도체_24개월.png')) problems.push('[req] 3.1.10 관세청 수출 잠정치 차트 missing: charts/수출_전체_24개월.png|charts/수출_반도체_24개월.png (run gen_customs_chart.py)'); }
else warnings.push('[req] 3.1.10 customs data missing (db/customs.json seed) - section omitted');
// (fix v3.48) 한국상장 ETF 추세 스파크라인 coverage — Yahoo .KS 이력 미제공시 Daum 폴백이 채워야 함.
//   자율(예약) 실행이 조용히 누락 통과하지 않도록 warning 으로 표면화(발송 차단 아님).
try{
  const grp=['asia','china','japan','taiwan','india','vietnam','sea'];  // (v3.50) sea=SE-Asia(US-listed)
  const ae=m.asia_etfs||{}; let aTot=0,aMiss=0;
  grp.forEach(g=>{(Array.isArray(ae[g])?ae[g]:[]).forEach(x=>{aTot++; if(!cExists('charts/spark_aetf_'+(x.code||x.symbol||'')+'.png')) aMiss++;});});
  if(aTot && aMiss>Math.max(1,Math.floor(aTot*0.2))) warnings.push('[3.4.1] asia ETF trend charts missing '+aMiss+'/'+aTot+' (Yahoo .KS no-history -> check Daum fallback in fetch_asia_etf.py)');
  if(aTot && aTot<29) warnings.push('[3.4.1] asia ETF rows '+aTot+'<29 (v3.50: KR14+US15; check fetch_asia_etf.py US tickers)');
}catch(e){}
try{
  const eu=(m.europe_etfs&&m.europe_etfs.items)||[]; let eMiss=0;
  eu.forEach(x=>{ if(!cExists('charts/spark_etf_'+(x.symbol||x.dispSym||'')+'.png')) eMiss++; });
  if(eu.length && eMiss>Math.max(1,Math.floor(eu.length*0.4))) warnings.push('[3.5.1] europe ETF trend charts missing '+eMiss+'/'+eu.length+' (check Daum fallback in fetch_us.py euetf)');
}catch(e){}
// (v3.50) 3.6/3.7 US-listed country ETF — data present => spark coverage check; data absent => section omitted (warning)
try{
  [['americas_etfs','3.6',3],['aume_etfs','3.7',4]].forEach(([k,sec,exp])=>{
    const it=(m[k]&&m[k].items)||[];
    if(!it.length){ warnings.push('['+sec+'] '+k+' data missing (fetch_us.py) - section omitted'); return; }
    if(it.length<exp) warnings.push('['+sec+'] '+k+' items '+it.length+'<'+exp);
    let miss=0; it.forEach(x=>{ if(!cExists('charts/spark_etf_'+(x.symbol||'')+'.png')) miss++; });
    if(miss) warnings.push('['+sec+'] country ETF trend charts missing '+miss+'/'+it.length);
  });
}catch(e){}
// (v3.51) [AppC] AI value-chain stocks -- data present => count + spark coverage; absent => warning (section omitted). (v3.52.1) 43->46 (ORCL/007660/AMKR)
try{
  const ac=m.appendix_c||{}; const rows=(ac&&ac.rows)||{}; let n=0,miss=0;
  Object.keys(rows).forEach(g=>{(Array.isArray(rows[g])?rows[g]:[]).forEach(x=>{ n++; const sym=String((x&&(x.code||x.symbol))||'').replace(/\./g,'_'); if(!cExists('charts/spark_c_'+sym+'.png')) miss++; });});
  if(!n) warnings.push('[AppC] appendix_c data missing (fetch_appc.py) - section omitted');
  else { if(n<46) warnings.push('[AppC] AI value-chain rows '+n+'<46 (v3.52.1: check fetch_appc.py)');
         if(miss>Math.max(1,Math.floor(n*0.2))) warnings.push('[AppC] value-chain spark charts missing '+miss+'/'+n+' (gen_rest_charts spark_c_*)'); }
}catch(e){}
// req20 (2026-07-05): 3.1.6 FactSet — "매 실행 변동 체크·미변동 유지" 동작 보장.
//   next_date 가 비면 다음 회차 갱신 트리거가 영구 불능 → warning. next_date 경과했는데 report.date 미갱신 → problem(이전 자료 잔존 금지).
{ const fsx=m.factset||{}; const rp=fsx.report||{};
  const today=String((d.metadata&&d.metadata.report_date)||'').slice(0,10)||new Date().toISOString().slice(0,10);
  if(rp.date){
    if(!rp.next_date) warnings.push('[req20] 3.1.6 FactSet report.next_date 비어있음 — 다음 회차 갱신 트리거 불능(주간 발행일 기입 필요)');
    else if(String(rp.next_date)<=today && String(rp.date)<String(rp.next_date))
      problems.push('[req20] 3.1.6 FactSet Earnings Insight 신규 회차 미갱신(next_date '+rp.next_date+' 경과, report.date '+rp.date+') — 새 PDF 정독·full_summary 교체 필요'); }
}
// req21 (2026-07-05): 3.1.7 M7 — "업데이트:매일" 동작 보장. as_of 가 실행일과 다르면 오늘 실측이 아님(내장 스냅샷/전일 잔존).
{ const m7=m.m7_outlook||{};
  const today=String((d.metadata&&d.metadata.report_date)||'').slice(0,10);
  if(m7.rows&&m7.rows.length&&today&&String(m7.as_of||'').slice(0,10)!==today)
    problems.push('[req21] 3.1.7 M7 실적 전망 as_of('+(m7.as_of||'없음')+') != 실행일('+today+') — 매일 실측 규칙 위반(M7OutlookAgent 재실행 필요)');
  if(!m7.rows||!m7.rows.length) warnings.push('[req21] 3.1.7 m7_outlook 데이터 없음 — 빌더 내장 스냅샷으로 렌더됨'); }
// req22 (v3.54): 3.2.4/3.2.5 KRX 증시 Brief·공매도 데일리 브리프 — 데이터 있으면 페이지 캡쳐 PNG 필수, 데이터 자체가 없으면 warning(수집 실패).
{ const kb=m.krx_brief||{};
  [['krx','krx_brief','3.2.4 KRX 증시 Brief'],['short','short_brief','3.2.5 공매도 데일리 브리프']].forEach(([k,pfx,label])=>{
    const it=kb[k];
    if(!it||!it.pages){ warnings.push('[req22] '+label+' 데이터 없음 — fetch_krx_brief.py 수집 실패 여부 확인'); return; }
    for(let i=1;i<=it.pages;i++) if(!cExists('charts/'+pfx+'_p'+i+'.png')) problems.push('[req22] '+label+' 캡쳐 누락: '+pfx+'_p'+i+'.png (fetch_krx_brief.py 재실행 필요)');
    if(it.stale_note) warnings.push('[req22] '+label+' 직전 회차(DB) 폴백 사용: '+(it.date||'-')); }); }
// req23 (2026-07-12): 3.1.8 CAPEX — 대시보드형 4분할 차트 필수 + Meta 포함 5개사
{ if(m.bigtech_capex&&Array.isArray(m.bigtech_capex.rows)&&m.bigtech_capex.rows.length){
    ['capex_capex.png','capex_rev.png','capex_fcf.png','capex_ratio.png'].forEach(c=>{ if(!cExists('charts/'+c)) problems.push('[req23] 3.1.8 CAPEX chart missing: '+c+' (run gen_capex_chart.py)'); });
    const hasMeta=m.bigtech_capex.rows.some(r=>/meta/i.test(String(r&&r.company||'')));
    if(!hasMeta) warnings.push('[req23] 3.1.8 CAPEX rows without Meta'); } }
// req24 (2026-07-12): 3.1.9 HBM — 대시보드 차트 + EPS 3사 단일화(중복 Micron 금지) + 단일소스 노트
{ const hb=m.hbm||{};
  if(m.memory&&m.memory.tables&&!cExists((hb.chart)||'charts/hbm_dashboard.png')) problems.push('[req24] 3.1.9 hbm_dashboard.png missing (run gen_hbm_dashboard.py)');
  const ey=Array.isArray(hb.eps_yearly)?hb.eps_yearly:[];
  if(ey.length){ const mic=ey.filter(o=>/micron|\uB9C8\uC774\uD06C\uB860/i.test(String(o&&o.name||''))).length;
    if(mic>1) problems.push('[req24] 3.1.9 EPS table duplicate Micron rows: '+mic+' (merge alias normalization broken)');
    if(!hb.eps_note) warnings.push('[req24] 3.1.9 eps_note(single-source price note) missing'); } }
// req25 (2026-07-12): 3.1.12 KSVKOSPI — 1w~1y anchors 필수(공식 VKOSPI 일별 이력 기반, '-' 금지)
{ const rows=((m.macro||{}).sentiment||{}).rows||[];
  const vk=rows.find(r=>/KSVKOSPI/i.test(String(r&&r.name||'')));
  if(vk){ const miss=['1w_pct','1mo_pct','3mo_pct','6mo_pct','1y_pct'].filter(k=>vk[k]==null);
    if(miss.length) problems.push('[req25] 3.1.12 KSVKOSPI anchors missing: '+miss.join(',')+' (merge req8: deriv_signals.db VKOSPI history)'); } }
// req26 (2026-07-12): 3.1.11 조기경보 — 신호차트 존재 + 판정상태 타임라인 DB 누적 확인
{ if(m.semi_cycle&&m.semi_cycle.signals&&m.semi_cycle.signals.length){
    if(!cExists('charts/semi_cycle_signals.png')) problems.push('[req26] 3.1.11 semi_cycle_signals.png missing (run gen_hbm_dashboard.py)');
    try{ const st=J(require('path').join(WORK,'..','..','claudeCowork','namoobi-market-report-server','db','series_semi_status.json')); }catch(e){
      try{ const g=require('fs').readdirSync('/sessions').map(x=>'/sessions/'+x+'/mnt/claudeCowork/namoobi-market-report-server/db/series_semi_status.json').find(p=>{try{return require('fs').existsSync(p)}catch(_){return false}});
        if(!g) warnings.push('[req26] series_semi_status.json (판정 타임라인 DB) not found'); }catch(_){} } } }
// req27 (2026-07-12): 3.1.6 FactSet — Key Metrics 차트용 report.metrics 존재(없으면 대시보드 미생성)
{ const rp2=(m.factset||{}).report||{}; if(rp2.date&&!rp2.metrics) warnings.push('[req27] 3.1.6 FactSet report.metrics missing — factset_keymetrics.png cannot regenerate'); }
// req28 (2026-07-12): 2장 캘린더 전 항목 출처 필수 — docx·대시보드 출처 공백 방지
{ const nw=(d.news||{}); [['events_calendar','2.1'],['events_calendar_longterm','2.2'],['bigtech_events','2.3']].forEach(pair=>{
    const k=pair[0], lb=pair[1]; const arr=Array.isArray(nw[k])?nw[k]:[];
    const none=arr.filter(e=>e&&!e.source&&!e.source_url).length;
    const nourl=arr.filter(e=>e&&e.source&&!e.source_url).length;
    if(none) problems.push('[req28] '+lb+' '+k+' 출처 전무 항목 '+none+'건 — 전 이벤트 source(·source_url) 필수');
    if(nourl) warnings.push('[req28] '+lb+' '+k+' source_url 없는 항목 '+nourl+'건'); }); }
// ---- v3.72 게이트 보강 (2026-07-21 검토: 게이트 밖으로 샐 수 있던 결함의 코드화) ----
// req29: 1장 Top News 최신성 — SKILL req1(D-0~D-1)의 게이트화. D-2 는 미국 저녁기사 시차 허용(warning), D-3+ 는 차단.
{ const tn=(d.news&&d.news.top_news)||[]; const ref=new Date(String((d.metadata&&d.metadata.report_date)||'').slice(0,10));
  if(tn.length&&!isNaN(ref)){ const old=[],near=[],nod=[];
    tn.forEach(x=>{ const pd=String((x&&x.published_date)||'').slice(0,10);
      if(!pd){ nod.push(x&&x.rank); return; }
      const p=new Date(pd); if(isNaN(p))return; const df=Math.floor((ref-p)/86400000);
      if(df>2) old.push((x&&x.rank)+':'+pd); else if(df===2) near.push((x&&x.rank)+':'+pd); });
    if(old.length) problems.push('[req29] 1장 Top News 신선도 위반(D-2 초과): '+old.join(', ')+' — 전일~당일 기사만 허용');
    if(near.length) warnings.push('[req29] top_news D-2 기사(시차 경계): '+near.join(', '));
    if(nod.length) warnings.push('[req29] top_news published_date 누락: rank '+nod.join(',')); } }
// req30: 수집 신선도 — 침묵 실패(carry-forward) 감지. 파일 mtime=오늘 이 아니면 fetch 미실행.
{ try{ const kp=path.join(WORK,'nmr_kr_ohlcv.json'); const st=fs.statSync(kp);
    const today=String((d.metadata&&d.metadata.report_date)||'').slice(0,10);
    const mt=new Date(st.mtimeMs+9*3600*1000).toISOString().slice(0,10);  // (v3.72.1) KST 환산 — UTC 그대로면 06시 실행분이 전일로 오탐
    if(today&&mt<today) problems.push('[req30] fetch_kr 미실행 의심: nmr_kr_ohlcv.json mtime '+mt+' != 실행일 '+today);
    const ko=J(kp); const last=String(((ko.kospi_ohlcv||[]).slice(-1)[0]||[])[0]||'');
    const ref=new Date(today), l=new Date(last);
    if(last&&!isNaN(l)&&!isNaN(ref)&&Math.floor((ref-l)/86400000)>7) warnings.push('[req30] kospi_ohlcv 마지막 '+last+' — 7일 초과(장기 휴장 아니면 소스 점검)');
  }catch(e){ warnings.push('[req30] nmr_kr_ohlcv.json 없음/손상 — 시세 신선도 미확인'); }
  { const ca=String((d.crypto&&(d.crypto.as_of||d.crypto.marker))||'').slice(0,10); const ref=new Date(String((d.metadata&&d.metadata.report_date)||'').slice(0,10)); const a=new Date(ca);
    if(ca&&!isNaN(a)&&!isNaN(ref)&&Math.floor((ref-a)/86400000)>1) warnings.push('[req30] 6장 crypto as_of 스테일('+ca+') — 서버 크론 확인'); } }
// req31: 6장 암호화폐 필수 요소(품질기준 8) — 공포탐욕·김프 4종(SOL 포함)·시장개요·코인/공포탐욕 차트.
{ const c=d.crypto||{};
  if(!(c.fear_greed&&c.fear_greed.current!=null)) problems.push('[req31] 6장 공포·탐욕 current 없음');
  const coins=((c.kimchi_premium||{}).coins)||[]; const syms=coins.map(x=>String((x&&x.symbol)||'').toUpperCase());
  if(coins.length<4||['BTC','ETH','XRP','SOL'].some(s=>syms.indexOf(s)<0)) problems.push('[req31] 6.3 김치프리미엄 4종(BTC/ETH/XRP/SOL) 미충족: '+syms.join(','));
  const mo=c.market_overview||{};
  if(mo.total_mcap_usd==null&&mo.total_market_cap==null) problems.push('[req31] 6.1 시장개요 시가총액 없음');
  if(!((c.top_gainers||[]).length&&(c.top_losers||[]).length)) warnings.push('[req31] 6.4 등락 상위(G/L) 비어있음 — CoinInfo 재시도 여부 확인');
  const ch=c.charts||{}; ['btc','eth','xrp','sol','fng'].forEach(k=>{ if(!cExists(ch[k]||('charts/coin_'+k+'.png'))) problems.push('[req31] 6장 차트 누락: '+(ch[k]||('coin_'+k+'.png'))); });
  if(!cExists('charts/kimp_30d.png')) warnings.push('[req31] 6.3 김프 차트(kimp_30d.png) 없음 — gen_kimp_chart.py'); }
// req32: 9~12장 분석 완결성 — 배분 합계 100·액션아이템·자산뷰 커버리지.
{ const a=d.analysis||{}; const pf=a.portfolios||{};
  ['aggressive','balanced','conservative'].forEach(k=>{ const p=pf[k];
    if(!p){ problems.push('[req32] 포트폴리오 '+k+' 없음'); return; }
    const s=(p.allocation||[]).reduce((t,x)=>t+(+((x||{}).weight_pct)||0),0);
    if(Math.abs(s-100)>0.5) problems.push('[req32] 포트폴리오 '+k+' 배분 합계 '+s+'% != 100%'); });
  const ai=a.action_items; let na=0;
  if(Array.isArray(ai)) na=ai.length; else if(ai&&typeof ai==='object') na=['short_term','mid_term','long_term'].reduce((t,k)=>t+(((ai||{})[k]||[]).length),0);
  if(!na) problems.push('[req32] 12장 action_items 비어있음');
  const av=a.asset_view||{}; if(Object.keys(av).length<11) warnings.push('[req32] asset_view '+Object.keys(av).length+'<11 자산'); }
// req33: v3.71 stale 필터 부작용 감시 — 핵심 증권사·IB 가 빈 key_reports 인데 '미확인' 정직 표기 없으면 침묵 마스킹 의심.
{ const chk=(obj,keys,label)=>{ keys.forEach(k=>{ const v=(obj||{})[k]; if(!v||typeof v!=='object')return;
    if(Array.isArray(v.key_reports)&&!v.key_reports.length&&String(v.key_message||'').indexOf('미확인')<0) warnings.push('[req33] '+label+'.'+k+' key_reports 비었는데 key_message 에 "미확인" 표기 없음(stale 필터 마스킹 의심 — key_message 갱신 필요)'); }); };
  chk(d.securities,['kb','nh','samsung','miraeasset','korea_inv','meritz'],'KR핵심');
  chk(d.global_securities,['ubs','goldman','jpmorgan','morgan_stanley','blackrock'],'IB'); }
// req34: 부록 A/B + 5장 환율 골격 — 버크셔 보유·AI 트렌드 10건·환율 5쌍.
{ const bk=d.berkshire||{}; if(!((bk.top_holdings||[]).length)) warnings.push('[req34] 부록A 버크셔 top_holdings 비어있음');
  const it=((d.ai_trends||{}).items)||[]; if(it.length<10) warnings.push('[req34] 부록B ai_trends '+it.length+'<10');
  const nu=it.filter(x=>!(x&&x.url)).length; if(nu) warnings.push('[req34] 부록B ai_trends url 없는 항목 '+nu+'건');
  const fx=(m.fx_markets)||{}; const missk=['usd_krw','eur_krw','jpy_krw','cny_krw','hkd_krw'].filter(k=>!fx[k]);
  if(missk.length) warnings.push('[req34] 5장 fx_markets 누락 쌍: '+missk.join(',')); }
// req35: docx 산출물 자동 검사(선택 3번째 인자 = docx 경로) — 크기·미디어 수를 GOODREPORT 골든과 비교(수동 비교의 코드화).
{ const dx=process.argv[4]; if(dx){ try{
    const st=fs.statSync(dx); if(st.size<3*1024*1024) problems.push('[req35] docx 크기 '+(st.size/1048576).toFixed(1)+'MB<3MB — 빌드 불완전 의심');
    const cp=require('child_process');
    const cnt=p=>{ try{ return cp.execSync('unzip -l "'+p+'" 2>/dev/null',{maxBuffer:16e6}).toString().split('word/media/').length-1; }catch(e){ return -1; } };
    const nn=cnt(dx);
    let gold=null; try{ const gd=fs.readdirSync('/sessions').map(x=>'/sessions/'+x+'/mnt/claudeCowork/GOODREPORT').find(p=>fs.existsSync(p));
      if(gd){ const fl=fs.readdirSync(gd).filter(f=>f.endsWith('.docx')).map(f=>({f:path.join(gd,f),t:fs.statSync(path.join(gd,f)).mtimeMs})).sort((a,b)=>b.t-a.t); if(fl.length) gold=fl[0].f; } }catch(e){}
    if(nn<0) warnings.push('[req35] docx 미디어 검사 불가(unzip)');
    else if(gold){ const gn=cnt(gold); if(gn>0&&nn<Math.floor(gn*0.9)) problems.push('[req35] docx 미디어 '+nn+' < 골든('+path.basename(gold)+') '+gn+'의 90% — 차트 대량 누락 의심'); }
    else if(nn<200) warnings.push('[req35] docx 미디어 '+nn+'<200 (GOODREPORT 골든 부재 — 절대 하한만 검사)');
  }catch(e){ warnings.push('[req35] docx 검사 실패: '+String(e).slice(0,60)); } } }
// req36 (v3.74): 직렬화 사고 검출 — 객체를 문자열 셀에 넣어 "[object Object]" 로 새어나간 값(2026-07-21 10장 실측).
{ const hits=[]; const walk=(o,path)=>{ if(o==null)return;
    if(typeof o==='string'){ if(o.indexOf('[object Object]')>=0) hits.push(path); return; }
    if(Array.isArray(o)){ o.forEach((x,i)=>walk(x,path+'['+i+']')); return; }
    if(typeof o==='object'){ Object.keys(o).forEach(k=>walk(o[k],path+'.'+k)); } };
  walk(d,'');
  if(hits.length) problems.push('[req36] "[object Object]" 직렬화 사고 '+hits.length+'건: '+hits.slice(0,5).join(', '));
  // 10장 asset_view 는 값이 객체여도 빌더(v3.74)가 평탄화하지만, 문자열화가 불가능한 형태면 표가 빈다.
  const av=(d.analysis&&d.analysis.asset_view)||{};
  const bad=Object.keys(av).filter(k=>{ const v=av[k]; if(typeof v==='string') return !v.trim();
    if(v&&typeof v==='object') return !Object.values(v).some(x=>typeof x==='string'&&x.trim()); return true; });
  if(bad.length) problems.push('[req36] 10장 asset_view 렌더 불가 항목: '+bad.join(','));
}
// req37 (v3.74): 3.1.11 사이클 단계 바 — current 가 list 의 어느 단계와도 매칭되지 않으면 강조가 사라진다.
{ const st=(m.semi_cycle||{}).stages||{};
  if(Array.isArray(st.list)&&st.list.length&&st.current){
    const c=String(st.current);
    if(!st.list.some(s=>c===s||c.startsWith(s)||c.includes(s)))
      problems.push('[req37] 3.1.11 stages.current("'+c.slice(0,30)+'…") 가 list 와 불일치 — 단계 바 강조 불능'); } }
const ok=problems.length===0;
console.log(JSON.stringify({ok,problems,warnings},null,1));
process.exit(ok?0:1);
// EOF -- namoobi-market-report verify_report.js
