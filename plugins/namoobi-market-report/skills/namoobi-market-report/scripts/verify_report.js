// verify_report.js (v3.6.32) -- pre-send quality gate.
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
  if(!cExists(ch)) problems.push(`[req1] 3.1.1 ${k} chart missing/broken: ${ch||'(none)'}`);
  else if(/flows/i.test(ch)) problems.push(`[req1] 3.1.1 ${k} chart is NOT a daily candle (flows fallback): ${ch}; use gen_kr_candle (candle+volume+cumulative net-buy)`);
});
// req2: 3.1.3 leading-index long series + chart
if(!cExists(m.korea_leading_chart||'charts/leading_cycle.png')) problems.push('[req2] 3.1.3 leading-index chart missing/broken');
{ const n=fileN('nmr_leading_series.json'); if(n<12) problems.push(`[req2] 3.1.3 leading-index long series too short (${n}<12); collect INDEXerGO monthly long series`); }
// req3: 3.1.4 8 theme trend charts
const THEMES=["a","b","c","d","e","f","g","h"]; // placeholder count; resolve by report data order
const tRows=Array.isArray(m.korea_theme_rows)?m.korea_theme_rows:[];
if(tRows.length<8) problems.push(`[req3] 3.1.4 theme rows ${tRows.length}<8`);
let tMiss=tRows.filter(t=>!cExists(t.chart)).map(t=>t.theme||'?');
if(tMiss.length) problems.push(`[req3] 3.1.4 theme trend charts missing ${tMiss.length}/${tRows.length}: ${tMiss.join(', ')}`);
// req4: semi stocks (>=10) + charts
const ss=Array.isArray(m.semi_ai_stocks)?m.semi_ai_stocks:[];
if(ss.length<10) problems.push(`[req4] 3.1.4 semi stocks ${ss.length}<10`);
{ const miss=ss.filter((x,i)=>!cExists(x.chart||('charts/semi_s_'+i+'.png'))).length; if(miss) problems.push(`[req4] 3.1.4 semi-stock trend charts missing ${miss}/${ss.length}`); }
// req5: semi ETFs (==20) + charts
const se=Array.isArray(m.semi_ai_etfs)?m.semi_ai_etfs:[];
if(se.length<20) problems.push(`[req5] 3.1.4 semi ETFs ${se.length}<20 (always show AUM top 20)`);
{ const miss=se.filter((x,i)=>!cExists(x.chart||('charts/semi_e_'+i+'.png'))).length; if(miss) problems.push(`[req5] 3.1.4 semi-ETF trend charts missing ${miss}/${se.length}`); }
// req6: CAPEX present (empty-year column drop handled in builder)
if(!(m.bigtech_capex&&Array.isArray(m.bigtech_capex.rows)&&m.bigtech_capex.rows.length>=4)) warnings.push('[req6] 3.2.1 CAPEX rows<4');
// req7: FOMC dot plot completeness (no empty jun/mar)
const f=m.fomc_dotplot;
if(!f||!Array.isArray(f.rows)||!f.rows.length) problems.push('[req7] 3.2.2 FOMC dot plot data missing');
else { const miss=[]; f.rows.forEach(r=>['jun','mar'].forEach(c=>{ const v=r[c]; if(v==null||String(v).trim()===''||String(v).trim()==='-')miss.push((r.item||'?')+'.'+c); })); if(miss.length) problems.push('[req7] 3.2.2 dot plot empty values: '+miss.join(', ')); }
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

const ok=problems.length===0;
console.log(JSON.stringify({ok,problems,warnings},null,1));
process.exit(ok?0:1);
// EOF -- namoobi-market-report verify_report.js
