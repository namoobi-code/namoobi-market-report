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
if(tRows.length<14) problems.push(`[req3] 3.2.3 theme rows ${tRows.length}<14 (v3.63: +K-food/K-beauty)`);
let tMiss=tRows.filter(t=>!cExists(t.chart)).map(t=>t.theme||'?');
if(tMiss.length) problems.push(`[req3] 3.2.3 theme trend charts missing ${tMiss.length}/${tRows.length}: ${tMiss.join(', ')}`);
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
const ok=problems.length===0;
console.log(JSON.stringify({ok,problems,warnings},null,1));
process.exit(ok?0:1);
// EOF -- namoobi-market-report verify_report.js
