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
const ki=m.korea_investors||{};
['kospi','kosdaq'].forEach(k=>{ const ch=ki[k+'_chart']||'';
  if(!cExists(ch)) problems.push("[req1] 3.1.1 "+k+" chart missing/broken: "+(ch||'(none)'));
  else if(/flows/i.test(ch)) problems.push("[req1] 3.1.1 "+k+" chart NOT a candle (flows fallback): "+ch); });
if(!cExists(m.korea_leading_chart||'charts/leading_cycle.png')) problems.push('[req2] 3.1.3 leading chart missing/broken');
{ const n=fileN('nmr_leading_series.json'); if(n<12) problems.push("[req2] 3.1.3 leading long series short ("+n+"<12)"); }
const tRows=Array.isArray(m.korea_theme_rows)?m.korea_theme_rows:[];
if(tRows.length<8) problems.push("[req3] 3.1.4 theme rows "+tRows.length+"<8");
{ const miss=tRows.filter(t=>!cExists(t.chart)).map(t=>t.theme||'?'); if(miss.length) problems.push("[req3] 3.1.4 theme trend charts missing "+miss.length+"/"+tRows.length+": "+miss.join(', ')); }
const ss=Array.isArray(m.semi_ai_stocks)?m.semi_ai_stocks:[];
if(ss.length<10) problems.push("[req4] 3.1.4 semi stocks "+ss.length+"<10");
{ const miss=ss.filter((x,i)=>!cExists(x.chart||('charts/semi_s_'+i+'.png'))).length; if(miss) problems.push("[req4] 3.1.4 semi-stock trend charts missing "+miss+"/"+ss.length); }
const se=Array.isArray(m.semi_ai_etfs)?m.semi_ai_etfs:[];
if(se.length<20) problems.push("[req5] 3.1.4 semi ETFs "+se.length+"<20 (need AUM top 20)");
{ const miss=se.filter((x,i)=>!cExists(x.chart||('charts/semi_e_'+i+'.png'))).length; if(miss) problems.push("[req5] 3.1.4 semi-ETF trend charts missing "+miss+"/"+se.length); }
if(!(m.bigtech_capex&&Array.isArray(m.bigtech_capex.rows)&&m.bigtech_capex.rows.length>=4)) warnings.push('[req6] CAPEX rows<4');
const f=m.fomc_dotplot;
if(!f||!Array.isArray(f.rows)||!f.rows.length) problems.push('[req7] 3.2.2 dot plot missing');
else { const miss=[]; f.rows.forEach(r=>['jun','mar'].forEach(c=>{ const v=r[c]; if(v==null||String(v).trim()===''||String(v).trim()==='-')miss.push((r.item||'?')+'.'+c); })); if(miss.length) problems.push('[req7] 3.2.2 dot plot empty: '+miss.join(', ')); }
function fresh(s,kind){ if(!s)return true; const ref=new Date((d.metadata&&d.metadata.report_date)||Date.now()); const dt=new Date(String(s).slice(0,10)); if(isNaN(dt))return true; let max=(kind==='daily')?1:(kind==='w7'?7:3); const dow=ref.getDay(); if(dow===1)max+=2; if(dow===6)max+=1; if(dow===0)max+=2; return Math.floor((ref-dt)/86400000)<=max; }
function houses(o,label,kind){ if(!o||typeof o!=='object')return; Object.keys(o).forEach(k=>{ const v=o[k]; if(!v||typeof v!=='object'||Array.isArray(v))return; const kr=v.key_reports; if(Array.isArray(kr)) kr.forEach(r=>{ const dt=(r&&r.date)||''; if(dt&&!fresh(dt,kind)) problems.push("[req8] "+label+"."+k+" report stale: "+dt); }); }); }
houses(d.securities,'KRbrokers','weekly');
houses(d.global_securities,'GlobalIB','w7');
const ok=problems.length===0;
console.log(JSON.stringify({ok,problems,warnings},null,1));
process.exit(ok?0:1);
