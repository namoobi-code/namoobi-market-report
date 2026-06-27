#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
// namoobi-market-report builder — v3.6.14 (신규상장 ETF 차트: 다음 charts API·상장후 라벨)
const argv = process.argv.slice(2);
const validateOnly = argv[0] === '--validate';
const args = validateOnly ? argv.slice(1) : argv;
if (args.length < 1) { console.error("Usage: node genreport.js [--validate] <input.json> [out.docx]"); process.exit(1); }
const inputPath = args[0];
let data;
try { data = JSON.parse(fs.readFileSync(inputPath, 'utf-8')); }
catch (e) { console.error(`JSON parse fail: ${inputPath}\n${e.message}`); process.exit(1); }

// ── v3.6.24 스키마 정규화: 에이전트 출력 드리프트를 흡수해 '조용한 누락' 방지 ──
// ── 구조적 정규화 (v3.6.29): 수익률 변화율 키 별칭 흡수 ──
// 에이전트가 1m_pct/3m_pct/6m_pct·1mo/3mo/6mo 등으로 키를 내보내도 표준키(1w_pct/1mo_pct/3mo_pct/6mo_pct/1y_pct)로 통일.
// 표준키가 비었을 때만 복사(실데이터 보존), 데이터 전체 재귀. → 3.1.4 등 1·3·6개월 '-' 키드리프트 버그를 코드로 영구 차단.
function normalizePctKeys(root){
  const ALIAS={"1d":"1d_pct","1day_pct":"1d_pct","1w":"1w_pct","1week_pct":"1w_pct","1m":"1mo_pct","1m_pct":"1mo_pct","1mo":"1mo_pct","1month_pct":"1mo_pct","3m":"3mo_pct","3m_pct":"3mo_pct","3mo":"3mo_pct","3month_pct":"3mo_pct","6m":"6mo_pct","6m_pct":"6mo_pct","6mo":"6mo_pct","6month_pct":"6mo_pct","1y":"1y_pct","12m_pct":"1y_pct","1yr_pct":"1y_pct"};
  const seen=new WeakSet();
  (function walk(o){ if(!o||typeof o!=="object"||seen.has(o))return; seen.add(o);
    if(Array.isArray(o)){ for(const it of o) walk(it); return; }
    for(const k of Object.keys(o)){ const c=ALIAS[k]; if(c&&c!==k&&(o[c]===undefined||o[c]===null||o[c]==="")) o[c]=o[k]; }
    for(const k of Object.keys(o)){ const v=o[k]; if(v&&typeof v==="object") walk(v); } })(root);
  return root;
}

function normalizeData(d){
  for (const sec of ['securities','global_securities']){
    const o=d[sec];
    if (o && o.firms && typeof o.firms==='object'){
      for (const k of Object.keys(o.firms)) if (o[k]===undefined) o[k]=o.firms[k];
    }
  }
  if (d.markets && d.markets.us_credit && !d.markets.hy_spread){
    const u=d.markets.us_credit;
    const num=v=>{const n=parseFloat(String(v).replace(/[^0-9.\-]/g,''));return isNaN(n)?null:n;};
    d.markets.hy_spread={current:num(u.hy_oas),w1:null,m1:null,m3:null,m6:null,y1:null,
      trend:u.trend||"",comment:u.comment||"",asof:u.asof||(d.metadata&&d.metadata.report_date)||""};
  }
  if (d.crypto && !d.crypto.charts){
    const m={},map={btc:'coin_btc.png',eth:'coin_eth.png',xrp:'coin_xrp.png',sol:'coin_sol.png',fng:'fng_1y.png'};
    for (const [k,f] of Object.entries(map)){ try{ if(fs.existsSync('charts/'+f)) m[k]='charts/'+f; }catch(e){} }
    if (Object.keys(m).length) d.crypto.charts=m;
  }
  try { normalizePctKeys(d); } catch(e){ console.error('normalizePctKeys 경고:', e.message); }
  return d;
}
try { normalizeData(data); } catch(e){ console.error('normalizeData 경고:', e.message); }

function validate(d) {
  const issues = [], warn = [];
  const has = (o, k) => o && o[k] !== undefined && o[k] !== null;
  if (!has(d,'metadata') || !d.metadata.report_date) issues.push("metadata.report_date 누락");
  if (!has(d,'news') || !Array.isArray(d.news.top_news) || !d.news.top_news.length) issues.push("news.top_news 누락");
  else { if (d.news.top_news.length<10) warn.push(`top_news ${d.news.top_news.length}개(<10)`);
    const ns=d.news.top_news.filter(n=>!n.source_url&&!n.source).length; if(ns) warn.push(`출처없는 뉴스 ${ns}개`); }
  if (!has(d,'news')||!Array.isArray(d.news.events_calendar)||!d.news.events_calendar.length) warn.push("events_calendar 누락");
  if (!has(d,'news')||!Array.isArray(d.news.events_calendar_longterm)||!d.news.events_calendar_longterm.length) warn.push("events_calendar_longterm 누락");
  if (!has(d,'markets')) issues.push("markets 누락");
  else { if(!d.markets.korea) warn.push("korea 누락"); if(!d.markets.us_markets) issues.push("us_markets 누락");
    else { if(!d.markets.us_markets.vix) warn.push("VIX 누락"); if(!d.markets.us_markets.dxy) warn.push("DXY 누락"); }
    if(!d.markets.asia_markets) warn.push("asia 누락"); if(!d.markets.europe_markets) warn.push("europe 누락"); if(!d.markets.fx_markets) warn.push("fx 누락"); }
  if (!has(d,'commodities')) issues.push("commodities 누락");
  else { if(!d.commodities.agriculture) warn.push("agriculture 누락"); if(!d.commodities.metals||!d.commodities.metals.rare_earth) warn.push("rare_earth 누락"); }
  if (!has(d,'crypto')) issues.push("crypto 누락");
  else { if(!d.crypto.fear_greed) warn.push("fear_greed 누락"); if(!d.crypto.kimchi_premium) warn.push("kimchi 누락"); }
  if (!has(d,'securities')) warn.push("securities 누락");
  if (!has(d,'global_securities')) warn.push("global_securities 누락");
  if (!has(d,'analysis')) issues.push("analysis 누락");
  else { if(!d.analysis.portfolios) issues.push("portfolios 누락");
    else ['aggressive','balanced','conservative'].forEach(k=>{const pf=d.analysis.portfolios[k]; if(pf&&!pf.basis) warn.push(`portfolios.${k}.basis 누락`);});
    if(!d.analysis.summary) warn.push("summary 누락"); }
  // ── v3.6.24 깊은 검증: 조용히 비거나 깨진 섹션을 명시적으로 보고 ──
  const M=d.markets||{};
  const secK=['shinhan','miraeasset','samsung','korea_inv','kiwoom'];
  if (d.securities && !secK.some(k=>d.securities[k])) issues.push("securities 5사 평탄 키 없음(firms 정규화 실패?) → 7장 전체 누락");
  const gsK=['ubs','goldman','jpmorgan','morgan_stanley','blackrock'];
  if (d.global_securities && !gsK.some(k=>d.global_securities[k])) issues.push("global_securities 5사 평탄 키 없음 → 8장 전체 누락");
  if (d.crypto && !d.crypto.charts) warn.push("crypto.charts 없음 → 6.2 코인차트 섹션 생략됨 (coin_*.png 생성 확인)");
  if (M.us_credit || M.hy_spread){ if(!M.hy_spread || M.hy_spread.current==null) warn.push("hy_spread.current 없음 → 3.2.3 HY 표/그래프 비거나 누락"); }
  if (!Array.isArray(M.korea_leading) || !M.korea_leading.length) warn.push("korea_leading 비어있음 → 3.1.3 경기선행지수 누락(통계청 KOSIS 수집 필요)");
  if (M.fx_markets){ const need=['usd_krw','eur_krw','jpy_krw','cny_krw','hkd_krw'];
    const miss=need.filter(k=>{try{return !fs.existsSync('charts/spark_'+k+'.png');}catch(e){return true;}});
    if(miss.length===need.length) warn.push("환율 추세 스파크라인 전무 → 5장 추세열 빈칸(nmr_series2.fx 시계열 수집 필요)"); }
  // (v3.6.33) ask-don't-degrade 차단 게이트 — 데이터는 있는데 차트가 없으면 조용히 "-"로 넘기지 말고 blocking 처리.
  //   --validate 가 issues 가 있으면 exit 1 → 워크플로(SKILL Phase 3.6)가 멈추고 사용자에게 어찌할지 묻는다.
  const needChart=(cond,file,msg)=>{ if(cond){ try{ if(!fs.existsSync(file)) issues.push("[차트누락] "+msg+" → "+file+" 없음 (데이터는 있으나 차트 미생성 — 사용자 확인 필요)"); }catch(e){ issues.push("[차트누락] "+msg);} } };
  needChart(M.korea_investors&&M.korea_investors.kospi, "charts/kospi_tech.png","3.2.1 코스피 일봉 캔들");
  needChart(M.korea_investors&&M.korea_investors.kosdaq, "charts/kosdaq_tech.png","3.2.1 코스닥 일봉 캔들");
  needChart(Array.isArray(M.korea_leading)&&M.korea_leading.length, "charts/leading_cycle.png","3.2.3 경기선행지수 차트");
  needChart(M.hy_spread, "charts/hy_oas.png","3.3.3 HY 스프레드 차트");
  (M.semi_ai_stocks||[]).forEach((x,i)=>needChart(true,"charts/semi_s_"+i+".png","3.2.4 반도체 종목 추세("+((x&&x.name)||i)+")"));
  (M.semi_ai_etfs||[]).forEach((x,i)=>needChart(true,"charts/semi_e_"+i+".png","3.2.4 반도체 ETF 추세("+((x&&x.name)||i)+")"));
  const etfN=(M.semi_ai_etfs||[]).length; if(M.semi_ai_etfs && etfN<20) issues.push("[부족] 반도체/AI ETF "+etfN+"종(<20) → 항상 상위 20 필요(수집 보강 후 재생성)");
  return { issues, warn };
}
const { issues, warn } = validate(data);
if (validateOnly) {
  if (warn.length) { console.log("⚠️ 경고:"); warn.forEach(w=>console.log("  - "+w)); }
  if (issues.length) { console.error("❌ 필수 누락:"); issues.forEach(i=>console.error("  - "+i)); process.exit(1); }
  console.log("✅ 데이터 검증 통과"+(warn.length?` (경고 ${warn.length}건)`:"")); process.exit(0);
}
if (issues.length) { console.error("⚠️ 필수 섹션 누락 상태로 빌드:"); issues.forEach(i=>console.error("  - "+i)); }
if (warn.length) warn.forEach(w=>console.error("  (경고) "+w));

let docx; try { docx = require('docx'); } catch(e){ console.error("docx 없음"); process.exit(1); }
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, Header, Footer,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType, ShadingType, PageNumber, PageBreak, ExternalHyperlink, ImageRun } = docx;
const HAS_IMG = typeof ImageRun !== 'undefined' && !!ImageRun;
function imagePara(relOrAbs, w, hgt){ try{
  const cands=[relOrAbs, path.join(__dirname,relOrAbs), path.join(process.cwd(),relOrAbs)];
  for(const fp of cands){ if(fp && relOrAbs && fs.existsSync(fp) && fs.statSync(fp).isFile() && HAS_IMG){
    return new Paragraph({alignment:AlignmentType.CENTER, spacing:{before:60,after:120},
      children:[new ImageRun({type:"png",data:fs.readFileSync(fp), transformation:{width:w,height:hgt}})]}); } }
}catch(e){} return null; }
const HAS_LINK = typeof ExternalHyperlink !== 'undefined' && !!ExternalHyperlink;
// (v3.4.2) 한글 폰트 임베드 — 미리보기 뷰어에 한글 폰트가 없어 깨지는 문제 방지. scripts/fonts/nmr_kr.ttf (나눔바른고딕 서브셋, OFL) 있으면 docx 에 임베드.
const fontCandidates=[path.join(__dirname,'fonts','nmr_kr.ttf'),path.join(process.cwd(),'fonts','nmr_kr.ttf'),process.env.NMR_FONT||''].filter(Boolean);
let embedFontData=null; for(const fp of fontCandidates){ try{ if(fs.existsSync(fp)){ embedFontData=fs.readFileSync(fp); break; } }catch(e){} }
const FONT=embedFontData?"NanumBarunGothic":"맑은 고딕"; // 임베드 TTF 내부 패밀리명과 동일해야 뷰어가 매칭한다
if(!embedFontData) console.error("  (경고) fonts/nmr_kr.ttf 없음 — 맑은 고딕 사용 (미리보기에서 한글이 깨질 수 있음)");
const reportDate = (data.metadata && data.metadata.report_date) || new Date().toISOString().slice(0,10);
const dateCompact = reportDate.replace(/-/g,'');
const outPath = args[1] || path.join(__dirname, `글로벌금융시장_종합시황보고서_${dateCompact}.docx`);

const border = { style: BorderStyle.SINGLE, size: 4, color: "9CA3AF" };
const borders = { top: border, bottom: border, left: border, right: border };
const headerShading = { fill: "1E40AF", type: ShadingType.CLEAR, color: "auto" };
const altShading = { fill: "EFF6FF", type: ShadingType.CLEAR, color: "auto" };
const negativeColor = "DC2626", positiveColor = "059669";
function fmtPct(v){ if(v===null||v===undefined||v==="")return "-"; const n=Number(v); if(isNaN(n))return String(v); return (n>=0?"+":"")+n.toFixed(2)+"%"; }
function viewText(v){ if(v==null)return ""; if(typeof v==="string")return v; if(Array.isArray(v))return v.map(viewText).filter(Boolean).join(", "); if(typeof v==="object")return Object.keys(v).map(function(k){var x=viewText(v[k]); return x?(/^[A-Za-z0-9_]+$/.test(k)&&v[k]&&typeof v[k]==="object"?x:x):"";}).filter(Boolean).join(" / "); return String(v); }
function pctColor(v){ if(v===null||v===undefined||v==="")return undefined; const n=Number(v); if(isNaN(n))return undefined; return n>=0?positiveColor:negativeColor; }
// (req5) '1일' 칸 = 직전장(2일전) 등락률 prev_pct (현재가의 한 세션 전). prev_pct 없으면 1d_pct 폴백.
function day1pct(m){ if(!m)return null; return (m.prev_pct!==undefined&&m.prev_pct!==null)?m.prev_pct:m['1d_pct']; }
function fmtNum(v){ if(v===null||v===undefined||v==="")return "-"; const n=Number(v); if(isNaN(n))return String(v); if(Math.abs(n)>=1000)return n.toLocaleString(undefined,{maximumFractionDigits:2}); return n.toFixed(2); }
// (v3.21) 전일 대비 절대변동 절댓값 포맷 (부호는 ▲/▼ 화살표로 표기)
function fmtChgAbs(v){ if(v===null||v===undefined||v==="")return null; const n=Number(v); if(isNaN(n))return null; const a=Math.abs(n);
  return a>=1000?a.toLocaleString(undefined,{maximumFractionDigits:2}):(a>=1?a.toFixed(2):a.toFixed(3)); }
// (v3.21b) '1일전' 셀: 전일(하루 전) 종가 표기 — 현재가(오늘)와 다른 하루 전 값. 접두 $/접미 % 가능.
function prevCloseText(v, opts){ opts=opts||{}; if(v===null||v===undefined||v==="")return "-"; return (opts.prefix||"")+fmtNum(v)+(opts.suffix||""); }
// (v3.21) 현재가 셀 runs: 1행=현재가(접두 $/접미 % 가능), 2행=전일대비 ▲/▼ 절대변동 (±%). 상승=초록·하락=빨강.
//   m.chg=전일대비 절대변동, m['1d_pct']=전일대비 %. 둘 다 없으면 현재가만 표기(기존과 동일).
function curCellRuns(cur, m, opts){ opts=opts||{}; m=m||{};
  const curStr=(opts.curText!=null&&opts.curText!=="")?String(opts.curText)
    :((cur===null||cur===undefined||cur==="")?"-":((opts.prefix||"")+fmtNum(cur)+(opts.suffix||"")));
  const runs=[new TextRun({text:curStr,bold:true,size:opts.size??20,color:opts.curColor})];
  let pct=m['1d_pct']; pct=(pct===null||pct===undefined||pct==="")?null:Number(pct);
  let chg=m.chg; chg=(chg===null||chg===undefined||chg==="")?null:Number(chg);
  if((pct!==null&&!isNaN(pct))||(chg!==null&&!isNaN(chg))){
    const ref=(pct!==null&&!isNaN(pct))?pct:chg; const col=ref>=0?positiveColor:negativeColor; const arrow=ref>=0?"▲":"▼";
    let t=arrow; const a=(chg!==null&&!isNaN(chg))?fmtChgAbs(chg):null; if(a!==null)t+=" "+a;
    if(pct!==null&&!isNaN(pct))t+=" ("+(pct>=0?"+":"")+pct.toFixed(2)+"%)";
    runs.push(new TextRun({text:t,break:1,size:(opts.size?Math.max(14,opts.size-4):16),color:col,bold:true})); }
  return runs; }
const mixedColor = "D97706"; // 양면(■) — 앰버
// (v3.4.3) 임팩트·방향 마커 색상: ▲ 강세=초록 / ▼ 부정=빨강 / ■ 양면=앰버. 구버전 ★(강세)·중립도 매핑.
function markColor(s){ const t=String(s||""); if(t.includes("▲")||t.includes("★"))return positiveColor; if(t.includes("▼"))return negativeColor; if(t.includes("■"))return mixedColor; return undefined; }
function fgDelta(cur,prev){ const c=Number(cur),pp=Number(prev); if(isNaN(c)||isNaN(pp))return "-"; const d=c-pp; return (d>=0?"+":"")+d; }
function p(text,opts={}){ return new Paragraph({ spacing:{after:opts.after??80,before:opts.before??0}, alignment:opts.align??AlignmentType.LEFT,
  children:[new TextRun({text:String(text),bold:opts.bold,size:opts.size??22,color:opts.color,italics:opts.italics})] }); }
function h(text,level){ const map={1:HeadingLevel.HEADING_1,2:HeadingLevel.HEADING_2,3:HeadingLevel.HEADING_3};
  return new Paragraph({ heading:map[level], spacing:{before:240,after:120}, children:[new TextRun({text,bold:true})] }); }
function bullet(text,opts={}){ return new Paragraph({ numbering:{reference:"bullets",level:0}, spacing:{after:60},
  children:[new TextRun({text:String(text),size:opts.size??22,bold:opts.bold,color:opts.color})] }); }
function cellRun(text,opts={}){ return new TextRun({text:String(text),bold:opts.bold||opts.header,size:opts.size??20,color:opts.header?"FFFFFF":opts.color}); }
function linkRun(text,url,opts={}){ const t=String(text); if(url&&HAS_LINK){ return new ExternalHyperlink({link:String(url),
  children:[new TextRun({text:t,size:opts.size??20,color:"1D4ED8",underline:{}})]}); } return new TextRun({text:t,size:opts.size??20,color:opts.color}); }
function reportBullet(r){ if(r&&typeof r==='object'){ const title=r.title||r.url||'-'; const dp=r.date?`  (${r.date})`:'';
  if(r.url&&HAS_LINK){ return new Paragraph({numbering:{reference:"bullets",level:0},spacing:{after:60},
    children:[new ExternalHyperlink({link:String(r.url),children:[new TextRun({text:String(title),size:22,color:"1D4ED8",underline:{}})]}),
    new TextRun({text:dp,size:20,color:"64748B"})]}); } return bullet(String(title)+dp); } return bullet(String(r)); }
function cell(text,opts={}){ return new TableCell({ borders, width:{size:opts.width,type:WidthType.DXA},
  shading:opts.header?headerShading:(opts.fill?{fill:opts.fill,type:ShadingType.CLEAR,color:"auto"}:(opts.alt?altShading:undefined)), margins:{top:80,bottom:80,left:120,right:120},
  children:[new Paragraph({alignment:opts.align??AlignmentType.LEFT, children:opts.runs||[cellRun(text,opts)]})] }); }
let tableCount=0;
function makeTable(cw,rows){ tableCount++; const total=cw.reduce((a,b)=>a+b,0); return new Table({width:{size:total,type:WidthType.DXA},columnWidths:cw,rows}); }
// ===== (v3.6.0) 추가 섹션 렌더러 — 데이터 없으면 자동 생략 =====
function simpleTable(w,header,body,opts){ opts=opts||{}; const leftCols=opts.left||[header.length-1];
  const rows=[header,...body].map((r,i)=>new TableRow({children:r.map((c,j)=>cell(c,{width:w[j],header:i===0,alt:i>0&&i%2===0,
    bold:(j===0||(opts.boldCols&&opts.boldCols.includes(j)))&&i>0, align:leftCols.includes(j)?AlignmentType.LEFT:AlignmentType.CENTER,
    color:(i>0&&opts.markCols&&opts.markCols.includes(j))?markColor(c):undefined}))}));
  children.push(makeTable(w,rows)); }
function renderBigtechEvents(){ const ev=data.news&&data.news.bigtech_events; if(!Array.isArray(ev)||!ev.length)return;
  children.push(h("2.3 빅테크 주요 이벤트 (신제품·신기술)",2));
  simpleTable([1500,3600,1100,3280],["시기","이벤트","중요도","예상 영향"],
    ev.map(e=>[e.date??"-",e.event??"-",e.importance??"-",e.expected_impact??e.impact??"-"]),{left:[1,3],boldCols:[1]});
  if(data.news.bigtech_events_comment) children.push(p(data.news.bigtech_events_comment)); }
function markSign(x){ const t=String(x||""); if(/^[\s]*[+]/.test(t)) return positiveColor; if(/^[\s]*[-−]/.test(t)) return negativeColor; return undefined; }
function renderKoreaExtras(){ const m=data.markets||{};
  if(m.korea_investors){ const ki=m.korea_investors; children.push(h("3.2.1 외국인 순매수 동향 (일봉·투자자별 수급)",3));
    children.push(p("외국인 순매수 동향: 시장 조정 국면에서 외국인이 매수세를 늘리면 하방 지지선이 구축된다는 강력한 신호입니다.",{italics:true,color:"64748B"}));
    const blk=(label,d,chart)=>{ if(!d)return; children.push(p(label+"   "+(d.level||""),{bold:true,color:"1E40AF",before:80}));
      const img=imagePara(chart, 648, 486); if(img)children.push(img); else children.push(p("(차트 생성 실패 — OHLCV/수급 데이터 확인 필요)",{italics:true,color:"B45309",size:16}));
      children.push(p("일봉 캔들(시·고·저·종)+이동평균(5·20·60·120) / 거래량 / 투자자별 누적순매수(빨강=외국인·파랑=기관·초록=개인, 조원)",{size:15,color:"94A3B8"}));
      children.push(p("투자자별 순매수 (기준: 최근 장 마감일 "+(ki.asof||"-")+" · 1일 기준)",{size:17,bold:true,color:"475569"}));
      const iw=[3300,3300,3300];
      const ih=new TableRow({children:["외국인 순매수","기관 순매수","개인 순매수"].map((x,i)=>cell(x,{width:iw[i],header:true,align:AlignmentType.CENTER}))});
      const ir=new TableRow({children:[
        cell(d.foreign||"-",{width:iw[0],align:AlignmentType.CENTER,bold:true,color:markSign(d.foreign)}),
        cell(d.institution||"-",{width:iw[1],align:AlignmentType.CENTER,bold:true,color:markSign(d.institution)}),
        cell(d.individual||"-",{width:iw[2],align:AlignmentType.CENTER,bold:true,color:markSign(d.individual)})]});
      children.push(makeTable(iw,[ih,ir]));
      if(d.comment)children.push(p(d.comment,{size:18,color:"64748B"})); };
    blk("코스피",ki.kospi,ki.kospi_chart);
    blk("코스닥",ki.kosdaq,ki.kosdaq_chart);
    children.push(p("기준일: "+(ki.asof||"-")+(ki.source?("   출처: "+ki.source):""),{size:16,color:"94A3B8"}));
    children.push(p("")); }
  { const ks=m.korea_investor_stocks||{}; children.push(h("3.2.2 투자자별 순매수·순매도 상위 종목 (최근 장 마감)",3));
    children.push(p("기준: "+(ks.asof||"-")+(ks.note?("   "+ks.note):""),{size:17,color:"94A3B8"}));
    const mw=[620,2950,1750,2950,1750];
    const nmOf=(x)=>(typeof x==="string")?x:((x&&(x.name||x.ticker))||"-");
    const dtOf=(x)=>(typeof x==="string")?"":((x&&(x.detail||x.amount||x.value))||"");
    const spanHdr=(t)=>new TableCell({borders,columnSpan:2,shading:headerShading,margins:{top:60,bottom:60,left:80,right:80},children:[new Paragraph({alignment:AlignmentType.CENTER,children:[cellRun(t,{header:true})]})]});
    // (요청) 외국인(좌)·기관(우) 한 표로 병합
    const invMerged=(title,fArr,iArr,n)=>{ children.push(p(title,{bold:true,color:"1E40AF",before:120,size:20}));
      const fa=Array.isArray(fArr)?fArr.slice(0,n):[], ia=Array.isArray(iArr)?iArr.slice(0,n):[];
      const grp=new TableRow({children:[cell("순위",{width:mw[0],header:true,align:AlignmentType.CENTER}),spanHdr("외국인"),spanHdr("기관")]});
      const sub=new TableRow({children:["순위","종목","순매매 규모","종목","순매매 규모"].map((x,i)=>cell(x,{width:mw[i],header:true,align:i===0?AlignmentType.CENTER:AlignmentType.LEFT}))});
      const rows=[grp,sub]; const rn=Math.max(fa.length,ia.length,1);
      for(let i=0;i<rn;i++){ const f=fa[i],iv=ia[i],alt=i%2===1;
        rows.push(new TableRow({children:[
          cell(String(i+1),{width:mw[0],alt,align:AlignmentType.CENTER}),
          cell(f?nmOf(f):"-",{width:mw[1],alt,bold:true}),
          cell(f?String(dtOf(f)||"-"):"-",{width:mw[2],alt,size:18}),
          cell(iv?nmOf(iv):"-",{width:mw[3],alt,bold:true}),
          cell(iv?String(dtOf(iv)||"-"):"-",{width:mw[4],alt,size:18})]})); }
      children.push(makeTable(mw,rows)); };
    children.push(p("◆ 코스피",{bold:true,size:22,color:"0F172A",before:120}));
    invMerged("순매수 상위 10 (좌 외국인 · 우 기관)",ks.kospi_foreign_buy||ks.kospi_buy,ks.kospi_inst_buy,10);
    invMerged("순매도 상위 10 (좌 외국인 · 우 기관)",ks.kospi_foreign_sell||ks.kospi_sell,ks.kospi_inst_sell,10);
    children.push(p("◆ 코스닥",{bold:true,size:22,color:"0F172A",before:160}));
    invMerged("순매수 상위 10 (좌 외국인 · 우 기관)",ks.kosdaq_foreign_buy||ks.kosdaq_buy,ks.kosdaq_inst_buy,10);
    invMerged("순매도 상위 10 (좌 외국인 · 우 기관)",ks.kosdaq_foreign_sell||ks.kosdaq_sell,ks.kosdaq_inst_sell,10);
    children.push(p("")); }
  if(Array.isArray(m.korea_leading)&&m.korea_leading.length){ children.push(h("3.2.3 경기선행지수 순환변동치 (주가 동행 선행지표)",3));
    children.push(p("경기선행지수 순환변동치와 주식(특히 KOSPI)은 상당한 정비례 상관관계를 가지며, 선행지수 순환변동치가 주가를 약 2개월 정도 선행하여 움직이는 특징이 있습니다.",{italics:true,color:"64748B"}));
    children.push(p("• 100 이상 = 경기 확장 전망    • 100 이하 = 경기 침체 전망",{bold:true,size:18,color:"475569"}));
    simpleTable([2200,2200,1800,3180],["시점","순환변동치","전월차","비고"],m.korea_leading.map(x=>[x.period??"-",(x.value!=null?String(x.value):"-"),x.mom??"-",x.note??"-"]),{left:[3]});
    { const lc=imagePara(m.korea_leading_chart||"charts/leading_cycle.png",648,243); if(lc){ children.push(lc); children.push(p("선행종합지수 순환변동치 장기 추이 (월별, 기준선 100 · 100 상회=확장 국면) · 출처: 국가데이터처 / INDEXerGO",{size:15,color:"94A3B8"})); } }
    if(m.korea_leading_comment)children.push(p(m.korea_leading_comment)); children.push(p("")); }
  { children.push(h("3.2.4 순환매 대비 테마별 현황 (대표 ETF·추세·수익률)",3));
    if(m.korea_themes_intro)children.push(p(m.korea_themes_intro,{italics:true,color:"64748B"}));
    children.push(p("각 항목은 2줄로 표기: 1행=설명(테마/종목·방향·대표ETF/시총·현황), 2행=현재가·1주·1개월·3개월·6개월·1년 수익률·추세(1Y) 그래프·추세 평가.",{size:16,color:"94A3B8"}));
    // (요청) 2줄 수익률 블록: 1행=설명(span), 2행=현재가·1주~1년·추세그래프·추세평가
    const RW=[1500,950,950,950,950,950,950,1500,1600]; const RTOT=RW.reduce((a,b)=>a+b,0);
    const retHeader=()=>new TableRow({children:["현재가","1일","1주","1개월","3개월","6개월","1년","추세(1Y)","추세 평가"].map((x,i)=>cell(x,{width:RW[i],header:true,align:AlignmentType.CENTER}))});
    const retRows=(items,prefix,descFn)=>{ const rows=[retHeader()];
      items.forEach((x,i)=>{ const alt=i%2===1; const chart=x.chart||(prefix?("charts/"+prefix+"_"+i+".png"):"");
        rows.push(new TableRow({children:[ new TableCell({borders,columnSpan:9,width:{size:RTOT,type:WidthType.DXA},shading:alt?altShading:undefined,margins:{top:70,bottom:30,left:120,right:120},children:[new Paragraph({children:descFn(x)})]}) ]}));
        rows.push(new TableRow({children:[
          cell("",{width:RW[0],alt,align:AlignmentType.RIGHT,runs:curCellRuns(x.current,x,{})}),
          cell(fmtPct(day1pct(x)),{width:RW[1],alt,align:AlignmentType.RIGHT,color:pctColor(day1pct(x))}),
          cell(fmtPct(x['1w_pct']),{width:RW[2],alt,align:AlignmentType.RIGHT,color:pctColor(x['1w_pct'])}),
          cell(fmtPct(x['1mo_pct']),{width:RW[3],alt,align:AlignmentType.RIGHT,color:pctColor(x['1mo_pct'])}),
          cell(fmtPct(x['3mo_pct']),{width:RW[4],alt,align:AlignmentType.RIGHT,color:pctColor(x['3mo_pct'])}),
          cell(fmtPct(x['6mo_pct']),{width:RW[5],alt,align:AlignmentType.RIGHT,color:pctColor(x['6mo_pct'])}),
          cell(fmtPct(x['1y_pct']),{width:RW[6],alt,align:AlignmentType.RIGHT,color:pctColor(x['1y_pct'])}),
          imgCellSpark(chart,RW[7],alt,150,48),
          cell(x.trend||x.trend_eval||"-",{width:RW[8],alt,size:16})]}));
      });
      return rows; };
    // 테마 (8개 고정 순서)
    const THEME_ORDER=["반도체/AI","전력기기","조선","방산","원자력","증권","로봇","우주"];
    const themeArr=Array.isArray(m.korea_theme_rows)?m.korea_theme_rows:[];
    const tByName={}; themeArr.forEach(t=>{ if(t&&t.theme)tByName[t.theme]=t; });
    const themeEtfs=m.korea_theme_etfs||{};
    const sani=(s)=>String(s).replace(/\//g,"_").replace(/\s+/g,"_");
    const themeItems=THEME_ORDER.map(nm=>{ const t=Object.assign({theme:nm},tByName[nm]||{}); if(!t.etf&&themeEtfs[nm])t.etf=themeEtfs[nm]; if(!t.chart)t.chart="charts/theme_"+sani(nm)+".png"; return t; });
    const themeDesc=(x)=>[ new TextRun({text:(x.theme||"-")+"  ",bold:true,size:20}),
      new TextRun({text:(x.direction||""),bold:true,size:18,color:markColor(x.direction)}),
      new TextRun({text:(x.etf?("   대표ETF: "+x.etf):""),size:16,color:"475569"}),
      new TextRun({text:(x.comment?("   — "+x.comment):""),size:16,color:"64748B"}) ];
    children.push(makeTable(RW,retRows(themeItems,null,themeDesc)));
    if(m.korea_themes_comment)children.push(p(m.korea_themes_comment)); children.push(p(""));
    // 반도체/AI 종목·ETF (시총/AUM순)
    const semiDesc=(x)=>[ new TextRun({text:(x.name||"-")+"  ",bold:true,size:20}),
      new TextRun({text:("시총/AUM: "+(x.aum||"미확인")),size:16,color:"475569"}),
      new TextRun({text:(x.note?("   — "+x.note):""),size:16,color:"64748B"}) ];
    if(Array.isArray(m.semi_ai_stocks)&&m.semi_ai_stocks.length){
      children.push(p("■ 반도체/AI 대표 국내 종목 (시총순)",{bold:true,color:"1E40AF",before:120}));
      children.push(makeTable(RW,retRows(m.semi_ai_stocks,"semi_s",semiDesc)));
      if(m.semi_ai_stocks_comment)children.push(p(m.semi_ai_stocks_comment,{size:18,color:"64748B"})); children.push(p("")); }
    if(Array.isArray(m.semi_ai_etfs)&&m.semi_ai_etfs.length){
      children.push(p("■ 반도체/AI 대표 ETF (AUM순, 상위 20)",{bold:true,color:"1E40AF",before:120}));
      children.push(makeTable(RW,retRows(m.semi_ai_etfs,"semi_e",semiDesc)));
      if(m.semi_ai_etfs_comment)children.push(p(m.semi_ai_etfs_comment,{size:18,color:"64748B"})); children.push(p("")); }
    else if(Array.isArray(m.semi_ai_breakdown)&&m.semi_ai_breakdown.length){
      children.push(p("■ 반도체/AI 대표 ETF·종목",{bold:true,color:"1E40AF",before:120}));
      children.push(makeTable(RW,retRows(m.semi_ai_breakdown,"semi",semiDesc))); }
  }
 }
// (v3.12.0) 3.1.6 메모리+HBM 대시보드 — 3.1(매크로 대시보드)로 이동. renderMacroIndicators 에서 호출.
function renderHBM(){ const m=data.markets||{}; const hbm=(m.hbm)||{};
  const ep=Array.isArray(hbm.eps_per)?hbm.eps_per:null;
  if(ep&&ep.length){ children.push(h("3.1.7 반도체 주가 체크용 메모리+HBM 지표",3));
    children.push(p("HBM 핵심 3사(SK하이닉스·삼성전자·Micron)의 EPS·PER 실측치. HBM 스팟가격·ASP·출하량·점유율은 무료 실측 데이터가 없어 이번 회차 미수록(추정 미사용).",{italics:true,color:"64748B"}));
    const w=[2600,1900,1500,1500,2240]; const rows=[hdrRow(["종목","EPS (TTM / E)","PER (TTM / E)","Fwd PER","비고"],w)];
    ep.forEach((o,i)=>{ const a=i%2===1;
      const eps=(o.eps_ttm!=null?String(o.eps_ttm):(o.eps_current_year!=null?(o.eps_current_year+" (E)"):"-"));
      const per=(o.per_ttm!=null?String(o.per_ttm):(o.per_current_year!=null?(o.per_current_year+" (E)"):"-"));
      rows.push(new TableRow({children:[cell(o.name||"-",{width:w[0],alt:a,bold:true}),
        cell(eps,{width:w[1],alt:a,align:AlignmentType.CENTER}),cell(per,{width:w[2],alt:a,align:AlignmentType.CENTER}),
        cell(o.forward_per!=null?String(o.forward_per):"-",{width:w[3],alt:a,align:AlignmentType.CENTER}),
        cell(o.note||(o.currency||""),{width:w[4],alt:a,size:14})]})); });
    children.push(makeTable(w,rows));
    children.push(p("기준: "+(hbm.asof||"")+" · 자료: "+(hbm.source||"FMP/UsStockInfo 실측")+(hbm.note?(" · "+hbm.note):""),{size:15,color:"94A3B8"}));
    children.push(p("")); } }

// (v3.6.30) 3.2.2 FOMC 점도표(dot plot) — 데이터(markets.fomc_dotplot) 없으면 자동 생략.
function renderFomcDotplot(){ const f=data.markets&&data.markets.fomc_dotplot; if(!f||typeof f!=="object")return;
  if(!(Array.isArray(f.rows)&&f.rows.length)&&!f.summary)return;
  children.push(p("■ FOMC 점도표 (dot plot)",{bold:true,color:"1E40AF",before:140,size:22}));
  children.push(p("점도표(dot plot): FOMC 위원들이 향후 적정 정책금리 수준을 점으로 표시한 전망. 중간값이 상향되면 매파적(긴축)·하향되면 비둘기파(완화) 신호다.",{italics:true,color:"64748B"}));
  children.push(p("업데이트: 분기 SEP(3·6·9·12월 FOMC) 발표 시 변동 체크 → 변동 시에만 갱신, 없으면 기존 자료 유지.",{size:15,italics:true,color:"94A3B8"}));
  if(f.summary)children.push(p(f.summary,{bold:true}));
  if(Array.isArray(f.rows)&&f.rows.length) simpleTable([3300,2300,2300,2300],["항목","6월 전망 (최신)","3월 전망 (이전)","변화"],f.rows.map(r=>[r.item!=null?r.item:"-",r.jun!=null?r.jun:"-",r.mar!=null?r.mar:"-",r.change!=null?r.change:"-"]),{left:[0]});
  if(Array.isArray(f.distribution)&&f.distribution.length){ children.push(p("연내 금리 전망 분포 (점 분포)",{bold:true,color:"1E40AF",before:100,size:20}));
    f.distribution.forEach(x=>children.push(p("• "+(x.label||"")+": "+(x.count||""),{size:19}))); }
  if(f.policy_rate)children.push(p("현 정책금리: "+f.policy_rate,{bold:true,before:60}));
  if(f.next_meeting)children.push(p("다음 점도표 발표: "+f.next_meeting,{size:18,color:"475569"}));
  if(Array.isArray(f.background)&&f.background.length){ children.push(p("배경 및 시장 영향",{bold:true,color:"1E40AF",before:100,size:20}));
    f.background.forEach(b=>children.push(p("• "+b,{size:19}))); }
  if(f.market_impact)children.push(p("시장 영향: "+f.market_impact,{color:"0F766E"}));
  if(Array.isArray(f.sources)&&f.sources.length)children.push(p("출처: "+f.sources.join(" · "),{size:14,color:"94A3B8"}));
  children.push(p("")); }

// (v3.12.0) 3.1.5 AI 빅테크 CAPEX — 3.1(매크로 대시보드)로 이동, 차트 풀폭(좌우 여백 제거).
function renderCapex(){ const m=data.markets||{};
  if(m.bigtech_capex&&Array.isArray(m.bigtech_capex.rows)&&m.bigtech_capex.rows.length){ const cx=m.bigtech_capex; children.push(h("3.1.6 AI 빅테크 자본지출(CAPEX)",3));
    const capV=(v)=>(v!==null&&v!==undefined&&String(v).trim()!=="")?v:"미공개";
    const yrHas=(k)=>cx.rows.some(r=>r[k]!==null&&r[k]!==undefined&&String(r[k]).trim()!=="");
    const years=[["y2025","2025(실적)"],["y2026","2026(E)"]];
    if(yrHas("y2027"))years.push(["y2027","2027(E)"]);
    if(yrHas("y2028"))years.push(["y2028","2028(E)"]);
    const Wt=9740, comp=1600, yw=1300, cmt=Math.max(2200, Wt-comp-yw*years.length);
    const ccols=[["company","기업",comp,1]].concat(years.map(y=>[y[0],y[1],yw,0])).concat([["comment","코멘트",cmt,1]]);
    const cwid=ccols.map(c=>c[2]),chead=ccols.map(c=>c[1]),cleft=ccols.map((c,i)=>c[3]?i:-1).filter(i=>i>=0);
    simpleTable(cwid,chead,cx.rows.map(r=>ccols.map(c=>(c[0]==="company")?(r.company??"-"):(c[0]==="comment")?(r.comment??"-"):capV(r[c[0]]))),{left:cleft});
    if(cx.comment)children.push(p(cx.comment));
    // 차트 풀폭(660): 좌우 여백 없이 최대 크기로 표시.
    { const c1=imagePara((cx.chart_capex)||"charts/capex_stack_ratio.png",660,289);
      if(c1){ children.push(c1); children.push(p("빅테크 CAPEX 합계(스택)와 매출 대비 비율 추이 — 2023~2025 실적 · 2026 가이던스 · 2027~2029 전망(E)",{size:15,color:"94A3B8"})); }
      const c2=imagePara((cx.chart_fcf)||"charts/capex_fcf.png",660,266);
      if(c2){ children.push(c2); children.push(p("주요 빅테크 잉여현금흐름(FCF) 추이 — 일부 기업 마이너스 전환 · 자료: 각사 SEC 보고서/FMP, AI Research",{size:15,color:"94A3B8"})); } }
    children.push(p("")); } }
// (v3.12.0) HY 스프레드 — 3.1.1 금리·통화정책에 통합(하위 블록).
function renderHY(){ const m=data.markets||{};
  if(m.hy_spread){ const c=m.hy_spread; children.push(p("■ 하이일드(HY) 스프레드",{bold:true,color:"1E40AF",before:140,size:22}));
    children.push(p("하이일드 스프레드(HY Spread): 하이일드 채권 수익률에서 미국 국채 수익률을 뺀 스프레드가 확대되면 신용시장 위험이 높아지지만, 반대로 안정되거나 좁혀지면 신용시장이 정상화되며 주식시장이 회복되는 경향을 보입니다.",{italics:true,color:"64748B"}));
    children.push(p("업데이트: 매일 (FRED BAMLH0A0HYM2 · ICE BofA US HY OAS 실측).",{size:15,italics:true,color:"94A3B8"}));
    const cols=[2200,1300,1200,1200,1200,1200,1700];
    const hdr=new TableRow({children:["지표 (OAS %)","현재","1주","1개월","3개월","6개월","1년"].map((x,i)=>cell(x,{width:cols[i],header:true,align:AlignmentType.CENTER}))});
    const lv=(v)=> (v===null||v===undefined)?"-":Number(v).toFixed(2)+"%";
    const col=(v)=>{ if(v===null||v===undefined)return undefined; return Number(v)>Number(c.current)? negativeColor : (Number(v)<Number(c.current)? positiveColor: undefined); };
    const row=new TableRow({children:[
      cell("美 HY OAS",{width:cols[0],bold:true}),
      cell(lv(c.current),{width:cols[1],align:AlignmentType.RIGHT,bold:true}),
      cell(lv(c.w1),{width:cols[2],align:AlignmentType.RIGHT,color:col(c.w1)}),
      cell(lv(c.m1),{width:cols[3],align:AlignmentType.RIGHT,color:col(c.m1)}),
      cell(lv(c.m3),{width:cols[4],align:AlignmentType.RIGHT,color:col(c.m3)}),
      cell(lv(c.m6),{width:cols[5],align:AlignmentType.RIGHT,color:col(c.m6)}),
      cell(lv(c.y1),{width:cols[6],align:AlignmentType.RIGHT,color:col(c.y1)})]});
    children.push(makeTable(cols,[hdr,row]));
    children.push(p("표는 각 시점의 OAS 레벨(%). 과거치가 현재보다 높으면(초록) 그동안 스프레드가 축소(신용 개선)된 것.",{size:18,color:"64748B"}));
    const img=imagePara(c.chart||"charts/hy_oas.png",480,173); if(img)children.push(img);
    if(c.trend)children.push(p("추세 평가: "+c.trend,{bold:true}));
    if(c.comment)children.push(p(c.comment));
    if(c.asof)children.push(p("기준: "+c.asof,{size:16,color:"94A3B8"}));
    children.push(p("")); } }
function renderUSExtras(){ renderUSEtfs(); renderIndexRebalance(); }
// (v3.6.8) 3.2.2 주요 미국 ETF — 지수추종·11개 섹터·테마/특화·방어형. 데이터(markets.us_etfs) 없으면 자동 생략.
function renderUSEtfs(){ const e=data.markets&&data.markets.us_etfs; if(!e||typeof e!=="object")return;
  const groups=[["index","① 미국 대표 지수 추종 ETF (시장 전체 흐름)"],["sector","② 섹터별 ETF (11개 S&P 500 섹터)"],["theme","③ 테마·특화 ETF (AI·반도체·배당·우주)"],["defensive","④ 방어형 ETF (변동성 완화)"]];
  if(!groups.some(([k])=>Array.isArray(e[k])&&e[k].length))return;
  children.push(h("3.3.1 주요 미국 ETF (지수·섹터·테마·방어형)",3));
  children.push(p("미국 대표 지수 추종·11개 S&P 500 섹터·테마/특화·방어형 ETF 의 현재가와 1주~1년 수익률, 1년 추세를 정리한다. 수익률은 주봉 종가 기준 가격수익률로, 분배금이 큰 ETF(SCHD·JEPI·채권형 등)는 실제 총수익률이 더 높을 수 있다. 섹터 ETF 옆 [%]는 S&P 500 내 비중.",{italics:true,color:"64748B"}));
  groups.forEach(([k,label])=>{ const arr=e[k]; if(!Array.isArray(arr)||!arr.length)return;
    children.push(p(label,{bold:true,color:"1E40AF",before:120,size:21}));
    const items=arr.map(x=>{ const sym=String(x.symbol||x.ticker||"-"); const nameLine=sym+" · "+(x.name||sym)+(x.weight?("  ["+x.weight+"]"):"");
      return {desc:[new TextRun({text:nameLine,bold:true,size:18,color:"1D4ED8"}),new TextRun({text:(x.desc?("  — "+x.desc):""),size:15,color:"64748B"})],
        m:x,current:x.current,curPrefix:"$",trend:String(x.trend||"-"),chart:"charts/spark_etf_"+sym+".png"}; });
    children.push(makeTable(TR2,trend2Rows(items))); });
  if(e.comment)children.push(p("추세 평가: "+e.comment,{bold:true,color:"0F766E"}));
  if(e.asof)children.push(p("기준: "+e.asof,{size:16,color:"94A3B8"}));
  children.push(p("")); }
// (v3.6.9) 3.2.3 미국 지수 정기 리밸런싱 — S&P 500·나스닥 100 편입/편출(사업내용·사유)·일정·기준·룰변경. 데이터(markets.index_rebalance) 없으면 자동 생략.
function renderIndexRebalance(){ const r=data.markets&&data.markets.index_rebalance; if(!r||typeof r!=="object")return;
  if(!r.sp500&&!r.nasdaq100)return;
  children.push(h("3.3.2 미국 지수 정기 리밸런싱 (S&P 500·나스닥 100)",3));
  children.push(p("S&P 500·나스닥 100 정기 리밸런싱의 편입·편출 종목(사업 내용·사유)·적용 시점, 편입 기준, 나스닥 패스트엔트리 룰 변경을 정리한다. 편입=초록, 편출=빨강.",{italics:true,color:"64748B"}));
  const cw=[820,780,1820,3300,3480]; // 구분/티커/회사명/사업내용/사유
  const chHdr=()=>new TableRow({children:["구분","티커","회사명","사업 내용","사유"].map((x,i)=>cell(x,{width:cw[i],header:true,align:i<2?AlignmentType.CENTER:AlignmentType.LEFT}))});
  const chRow=(it,i,action)=>{ const isAdd=String(action).indexOf("편입")>=0;
    return new TableRow({children:[
      cell(action,{width:cw[0],alt:i%2===1,bold:true,align:AlignmentType.CENTER,color:isAdd?positiveColor:negativeColor}),
      cell(String(it.ticker||"-"),{width:cw[1],alt:i%2===1,bold:true,align:AlignmentType.CENTER,color:"1D4ED8"}),
      cell(String(it.name||"-"),{width:cw[2],alt:i%2===1,bold:true}),
      cell(String(it.biz||"-"),{width:cw[3],alt:i%2===1,size:18}),
      cell(String(it.reason||"-"),{width:cw[4],alt:i%2===1,size:18})]}); };
  const renderEvent=(ev)=>{ if(!ev||typeof ev!=="object")return;
    const title=String(ev.title||"")+(ev.effective?("  ["+ev.effective+"]"):"");
    children.push(p(title,{bold:true,color:"1E40AF",before:100,size:20}));
    if(ev.note_top)children.push(p(String(ev.note_top),{size:17,color:"64748B"}));
    const rows=[chHdr()]; let i=0;
    (Array.isArray(ev.add)?ev.add:[]).forEach(it=>{rows.push(chRow(it,i,"편입"));i++;});
    (Array.isArray(ev.remove)?ev.remove:[]).forEach(it=>{rows.push(chRow(it,i,"편출"));i++;});
    children.push(makeTable(cw,rows));
    if(ev.note)children.push(p(String(ev.note),{size:17,color:"64748B"})); };
  // (v3.6.10) 견고화: events 가 {title,add,remove} 가 아니라 {ticker,name,biz,reason} 평면 배열로 와도 렌더되도록 정규화
  const renderEvents=(arr)=>{ if(!Array.isArray(arr)||!arr.length)return;
    const flat=arr.some(e=>e&&typeof e==="object"&&e.ticker&&!Array.isArray(e.add)&&!Array.isArray(e.remove));
    if(flat){ const add=[],remove=[];
      arr.forEach(it=>{ if(!it||typeof it!=="object")return; const rs=String(it.reason||"");
        (rs.indexOf("편출")>=0||/remove|delete/i.test(rs)?remove:add).push(it); });
      renderEvent({title:"편입·편출 종목",add,remove}); }
    else arr.forEach(renderEvent); };
  // S&P 500
  const sp=r.sp500;
  if(sp){ children.push(p("■ S&P 500 정기 리밸런싱",{bold:true,color:"0F172A",size:21,before:120}));
    if(Array.isArray(sp.schedule)&&sp.schedule.length){ children.push(p("1. 결정 시점 (분기별)",{bold:true,size:18}));
      if(sp.schedule.every(s=>typeof s==="string")) sp.schedule.forEach(s=>children.push(bullet(String(s))));
      else simpleTable([1500,2800,3200,2700],["분기","발표일","적용일(장 마감 후)","비고"],
        sp.schedule.map(s=>(typeof s==="string"?[s,"","",""]:[s.q??s.cycle??s.quarter??"-",s.announce??"-",s.effective??"-",s.note??"-"])),{left:[3]}); }
    renderEvents(sp.events);
    if(Array.isArray(sp.criteria)&&sp.criteria.length){ children.push(p("편입 기준",{bold:true,size:18,before:80}));
      if(sp.criteria.every(c=>typeof c==="string")) sp.criteria.forEach(c=>children.push(bullet(String(c))));
      else simpleTable([2400,7800],["항목","요건"],sp.criteria.map(c=>(typeof c==="string"?[c,""]:[c.item??"-",c.detail??"-"])),{left:[1]}); }
    if(sp.criteria_note)children.push(p(String(sp.criteria_note),{size:17,color:"9A3412"})); }
  // Nasdaq 100
  const nq=r.nasdaq100;
  if(nq){ children.push(p("■ 나스닥 100 (NDX) 정기 리밸런싱",{bold:true,color:"0F172A",size:21,before:160}));
    if(Array.isArray(nq.schedule)&&nq.schedule.length){ children.push(p("1. 결정 시점",{bold:true,size:18}));
      if(nq.schedule.every(s=>typeof s==="string")) nq.schedule.forEach(s=>children.push(bullet(String(s))));
      else simpleTable([3000,2700,4500],["주기","발표일","적용일(장 마감 후)"],
        nq.schedule.map(s=>(typeof s==="string"?[s,"",""]:[s.cycle??"-",s.announce??"-",s.effective??"-"])),{left:[2]}); }
    renderEvents(nq.events);
    if(nq.rule_change&&Array.isArray(nq.rule_change.rows)&&nq.rule_change.rows.length){ const rc=nq.rule_change;
      children.push(p("룰 변경"+(rc.effective?(" ("+rc.effective+" 발효)"):"")+" — 패스트 엔트리",{bold:true,color:"1E40AF",before:100,size:20}));
      if(rc.rows.some(x=>x&&(x.before!=null||x.after!=null))) simpleTable([2600,3800,3800],["규칙","변경 전","변경 후"],
        rc.rows.map(x=>[x.rule??x.item??"-",x.before??"-",x.after??"-"]),{left:[0,1,2]});
      else simpleTable([2800,7400],["항목","내용"], rc.rows.map(x=>[x.rule??x.item??"-",x.detail??x.change??"-"]),{left:[1]});
      if(rc.note)children.push(p(String(rc.note),{size:17,color:"64748B"})); }
    if(Array.isArray(nq.candidates)&&nq.candidates.length){ children.push(p("패스트 엔트리 유력 후보 (대형 IPO)",{bold:true,color:"1E40AF",before:100,size:20}));
      if(nq.candidates.some(c=>c&&(c.biz!=null||c.valuation!=null||c.status!=null))) simpleTable([1800,3300,2000,3100],["기업","사업 내용","추정 시총","IPO 상태/사유"],
        nq.candidates.map(c=>[c.name??"-",c.biz??"-",c.valuation??"-",c.status??"-"]),{left:[1,3]});
      else simpleTable([2400,7800],["기업","내용"], nq.candidates.map(c=>[c.name??"-",c.note??c.detail??"-"]),{left:[1]}); } }
  if(r.comment)children.push(p("종합: "+String(r.comment),{bold:true,color:"0F766E"}));
  if(r.asof)children.push(p("기준: "+String(r.asof),{size:16,color:"94A3B8"}));
  children.push(p("")); }
function renderStrategicMetals(){ const sm=data.commodities&&data.commodities.strategic_metals; if(!sm)return;
  children.push(h("4.5 전략광물·배터리 금속 (리튬·니켈·코발트·우라늄·희토류·흑연)",2));
  if(Array.isArray(sm.etf)&&sm.etf.length){ children.push(p("① ETF 프록시 가격 추세",{bold:true,color:"1E40AF"}));
    const etfKeys=["lit","remx","ura","urnm"]; const its=sm.etf.map((e,i)=>({desc:[new TextRun({text:(e.name||e.symbol||"-"),bold:true,size:20})],m:e,current:e.current,chart:"charts/spark_"+(etfKeys[i]||"")+".png"})); children.push(makeTable(TR2,trend2Rows(its)));
    if(sm.etf_comment)children.push(p(sm.etf_comment)); }
  if(Array.isArray(sm.spot)&&sm.spot.length){ children.push(p("② 주요 현물·실물 가격 현황",{bold:true,color:"1E40AF"}));
    simpleTable([1800,2400,5880],["품목","최근 가격","추세·코멘트"],sm.spot.map(s=>[s.item??"-",s.price??"-",s.comment??"-"]),{left:[2]}); }
  if(sm.comment)children.push(p(sm.comment)); children.push(p("")); }

const children = [];
children.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{before:2400,after:240},children:[new TextRun({text:"글로벌 금융시장 종합 시황 보고서",bold:true,size:48,color:"1E3A8A"})]}));
children.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:1200},children:[new TextRun({text:"Global Financial Markets Comprehensive Report",italics:true,size:28,color:"475569"})]}));
children.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:120},children:[new TextRun({text:`기준일: ${reportDate}`,size:26,bold:true})]}));
children.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:120},children:[new TextRun({text:"작성: AI Research — v3.6.14",size:22,color:"64748B"})]}));
children.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{before:360,after:0},
  border:{top:{style:BorderStyle.SINGLE,size:4,color:"F59E0B"},bottom:{style:BorderStyle.SINGLE,size:4,color:"F59E0B"}},
  children:[new TextRun({text:"⚠ 본 보고서는 AI가 공개 데이터를 자동 수집·생성한 참고 자료입니다. 투자 자문이 아니며, 자동 생성 특성상 오류·환각이 포함될 수 있으니 중요한 의사결정 전 반드시 원문 출처를 확인하십시오.",size:18,italics:true,color:"B45309"})]}));

if (data.analysis && data.analysis.summary) {
  children.push(new Paragraph({children:[new PageBreak()]}));
  children.push(h("Executive Summary",1));
  children.push(p(data.analysis.summary,{size:24}));
  if (data.news && Array.isArray(data.news.top_news) && data.news.top_news.length) {
    children.push(p("")); children.push(p("오늘의 핵심 헤드라인:",{bold:true}));
    data.news.top_news.slice(0,3).forEach(n=>children.push(bullet(`${n.headline} — ${n.impact||''}`)));
  }
}
children.push(new Paragraph({children:[new PageBreak()]}));
children.push(h("목   차",1));
["1. 글로벌 Top News 10","2. 글로벌 주요 이벤트 캘린더","3. 글로벌 증시 단·중·장기 추세 (매크로 지표 포함)","4. 원자재 (에너지·금속·희토류·농산물)","5. 주요 환율 (+달러인덱스)","6. 암호화폐","7. 한국 주요 증권사","8. 글로벌 IB (UBS·GS·JPM·MS·BlackRock)","9. 종합 분석","10. 자산별 견해","11. 추천 포트폴리오","12. 액션 아이템","13. 주의 사항 및 출처","[부록A] 워런 버핏 · 버크셔 13F","[부록B] 최신 AI Trends"].forEach(t=>children.push(p(t,{size:22,after:40})));

children.push(new Paragraph({children:[new PageBreak()]}));
children.push(h("1. 글로벌 Top News 10",1));
if (data.news && Array.isArray(data.news.top_news)) {
  const nw=[500,1900,3800,1300,1860];
  const rows=[new TableRow({children:["#","헤드라인","내용 요약","임팩트","출처"].map((c,j)=>cell(c,{width:nw[j],header:true,align:AlignmentType.CENTER}))})];
  data.news.top_news.forEach((n,k)=>{ const alt=(k+1)%2===0;
    const srcLabel=n.source||(n.source_url?"링크":"-");
    const srcRuns=(n.source||n.source_url)?[linkRun(srcLabel,n.source_url,{size:18})]:[cellRun("-",{size:18})];
    const ds=n.published_date?` (${n.published_date})`:"";
    if(ds&&(n.source||n.source_url)) srcRuns.push(new TextRun({text:ds,size:16,color:"94A3B8"}));
    rows.push(new TableRow({children:[cell(String(n.rank??"-"),{width:nw[0],alt,align:AlignmentType.CENTER}),
      cell(n.headline??"-",{width:nw[1],alt,bold:true}),cell(n.summary??"-",{width:nw[2],alt}),
      cell(n.impact??"-",{width:nw[3],alt,bold:true,align:AlignmentType.CENTER,color:markColor(n.impact)}),cell("",{width:nw[4],alt,runs:srcRuns})]})); });
  children.push(makeTable(nw,rows));
  children.push(new Paragraph({spacing:{before:80,after:80},children:[
    new TextRun({text:"임팩트 범례: ",size:18,color:"64748B"}),
    new TextRun({text:"▲ 강세",size:18,bold:true,color:positiveColor}),
    new TextRun({text:" · ",size:18,color:"64748B"}),
    new TextRun({text:"▼ 부정",size:18,bold:true,color:negativeColor}),
    new TextRun({text:" · ",size:18,color:"64748B"}),
    new TextRun({text:"■ 양면",size:18,bold:true,color:mixedColor})]}));
} else children.push(p("(뉴스 데이터 없음)"));

children.push(new Paragraph({children:[new PageBreak()]}));
children.push(h("2. 글로벌 주요 이벤트 캘린더",1));
// (v3.6.6) 2.1/2.2 에서 빅테크 신제품·신기술 이벤트 제외 — 2.3 빅테크 표에만 표시
const BIGTECH_EVENT_RE=/언팩|갤럭시|아이폰|WWDC|GTC|CES\b|MWC|메타 커넥트|구글 I\/O|Ignite|re:Invent|AWS re|키노트|언베일|Advancing AI|MI4\d0|애플[^,\n]*(가을|이벤트|행사|신제품)|OpenAI[^,\n]*(신모델|GPT|공개|플래그십)|엔비디아[^,\n]*(GTC|키노트|언팩)|삼성[^,\n]*언팩|구글[^,\n]*(I\/O|픽셀)|테슬라[^,\n]*(이벤트|데이|로보)/;
function notBigtechEvent(e){ return !BIGTECH_EVENT_RE.test(String((e&&e.event)||"")); }
children.push(h("2.1 향후 1개월 (전체 중요도)",2));
if (data.news && Array.isArray(data.news.events_calendar) && data.news.events_calendar.length) {
  const ew=[1300,1100,2800,1100,3060];
  const er=[["날짜","지역","이벤트","중요도","예상 영향"],...data.news.events_calendar.filter(notBigtechEvent).map(e=>[e.date??"-",e.region??"-",e.event??"-",e.importance??"-",e.expected_impact??"-"])].map((r,i)=>new TableRow({children:r.map((c,j)=>cell(c,{width:ew[j],header:i===0,alt:i>0&&i%2===0,align:(j===0||j===1||j===3)?AlignmentType.CENTER:AlignmentType.LEFT,bold:j===2&&i>0,color:(j===3&&i>0&&String(c).includes("★★★"))?"DC2626":undefined}))}));
  children.push(makeTable(ew,er));
} else children.push(p("(1개월 이벤트 없음)"));
children.push(p(""));
children.push(h("2.2 중장기 1개월~1년 (★★★만)",2));
if (data.news && Array.isArray(data.news.events_calendar_longterm) && data.news.events_calendar_longterm.length) {
  const lw=[1500,1200,3000,3660];
  const lr=[["날짜","지역","이벤트","예상 영향"],...data.news.events_calendar_longterm.filter(function(e){return e&&e.event;}).filter(notBigtechEvent).map(e=>[e.date??"-",e.region??"-",e.event??"-",e.expected_impact??"-"])].map((r,i)=>new TableRow({children:r.map((c,j)=>cell(c,{width:lw[j],header:i===0,alt:i>0&&i%2===0,align:(j===0||j===1)?AlignmentType.CENTER:AlignmentType.LEFT,bold:j===2&&i>0}))}));
  children.push(makeTable(lw,lr));
  children.push(p("※ 중장기는 ★★★만 수록. 미확정은 (예정) 표기.",{italics:true,color:"94A3B8",size:18}));
} else children.push(p("(중장기 이벤트 없음)"));
renderBigtechEvents();

children.push(new Paragraph({children:[new PageBreak()]}));
children.push(h("3. 글로벌 증시 단·중·장기 추세",1));
children.push(p("각 시장의 1주/1개월/3개월/6개월/1년 변화율로 추세·모멘텀을 평가한다.",{italics:true,color:"64748B"}));
const tw=[1500,1400,800,800,800,800,800,800,1500];
function trendRow(name,m,i){ const alt=i%2===1; return new TableRow({children:[
  cell(name,{width:tw[0],alt,bold:true}),
  cell("",{width:tw[1],alt,align:AlignmentType.RIGHT,runs:curCellRuns(m&&m.current,m,{})}),
  cell(fmtPct(day1pct(m)),{width:tw[2],alt,align:AlignmentType.RIGHT,color:pctColor(day1pct(m))}),
  cell(fmtPct(m&&m['1w_pct']),{width:tw[3],alt,align:AlignmentType.RIGHT,color:pctColor(m&&m['1w_pct'])}),
  cell(fmtPct(m&&m['1mo_pct']),{width:tw[4],alt,align:AlignmentType.RIGHT,color:pctColor(m&&m['1mo_pct'])}),
  cell(fmtPct(m&&m['3mo_pct']),{width:tw[5],alt,align:AlignmentType.RIGHT,color:pctColor(m&&m['3mo_pct'])}),
  cell(fmtPct(m&&m['6mo_pct']),{width:tw[6],alt,align:AlignmentType.RIGHT,color:pctColor(m&&m['6mo_pct'])}),
  cell(fmtPct(m&&m['1y_pct']),{width:tw[7],alt,align:AlignmentType.RIGHT,color:pctColor(m&&m['1y_pct'])}),
  cell((m&&m.trend)||"-",{width:tw[8],alt})]}); }
function trendHeaderRow(){ return new TableRow({children:["지수","현재치","1일","1주","1개월","3개월","6개월","1년","추세 평가"].map((x,i)=>cell(x,{width:tw[i],header:true,align:AlignmentType.CENTER}))}); }
function renderMarketBlock(title,obj,labels,exclude){ if(!obj)return; children.push(h(title,2)); const rows=[trendHeaderRow()]; let i=0;
  for(const [k,v] of Object.entries(obj)){ if(exclude&&exclude.includes(k))continue; rows.push(trendRow((labels&&labels[k])||k.toUpperCase(),v,i)); i++; } children.push(makeTable(tw,rows)); children.push(p("")); }
function imgCellSpark(relPath,width,alt,iw,ih){ iw=iw||84; ih=ih||28; let fp=null; if(!relPath)return cell("-",{width:width,alt:alt,align:AlignmentType.CENTER});
  const cands=[relPath, path.join(__dirname,relPath), path.join(process.cwd(),relPath)];
  for(const c of cands){ try{ if(c&&relPath&&fs.existsSync(c)&&fs.statSync(c).isFile()){fp=c;break;} }catch(e){} }
  if(fp&&HAS_IMG){ return new TableCell({borders,width:{size:width,type:WidthType.DXA},
    shading:alt?altShading:undefined, margins:{top:40,bottom:40,left:60,right:60},
    children:[new Paragraph({alignment:AlignmentType.CENTER,children:[new ImageRun({type:"png",data:fs.readFileSync(fp),transformation:{width:iw,height:ih}})]})]}); }
  return cell("-",{width:width,alt:alt,align:AlignmentType.CENTER}); }
const tw2=[1450,1150,930,930,930,930,930,1400,1550];
function trendHeaderRowC(){ return new TableRow({children:["지수","현재치","1주","1개월","3개월","6개월","1년","추세(1년)","추세 평가"].map((x,i)=>cell(x,{width:tw2[i],header:true,align:AlignmentType.CENTER}))}); }
function koTrend(m){ if(!m)return "-"; const t=String(m.trend||"").trim(); if(t&&/[가-힣]/.test(t))return t; // v3.6.11 영문/빈 trend → 수익률 기반 한글 자동 생성
  const y=m['1y_pct'],m3=m['3mo_pct'],m1=m['1mo_pct'],parts=[];
  if(y!==undefined&&y!==null)parts.push("1년 "+(y>=0?"+":"")+Math.round(y)+"% "+(y>=0?"강세":"약세"));
  if(m3!==undefined&&m3!==null)parts.push("3개월 "+(m3>=0?"+":"")+Math.round(m3)+"% "+(m3>=0?"상승":"조정"));
  else if(m1!==undefined&&m1!==null)parts.push("1개월 "+(m1>=0?"+":"")+Math.round(m1)+"% "+(m1>=0?"반등":"조정"));
  return parts.length?parts.join(", "):(t||"-"); }
const TR2=[1500,950,950,950,950,950,950,1500,1600]; const TR2TOT=TR2.reduce((a,b)=>a+b,0);
function trend2Header(){ return new TableRow({children:["현재가","1일","1주","1개월","3개월","6개월","1년","추세(1Y)","추세 평가"].map((x,i)=>cell(x,{width:TR2[i],header:true,align:AlignmentType.CENTER}))}); }
function trend2Rows(items){ const rows=[trend2Header()];
  items.forEach((it,i)=>{ const alt=i%2===1; const m=it.m||{};
    rows.push(new TableRow({children:[ new TableCell({borders,columnSpan:9,width:{size:TR2TOT,type:WidthType.DXA},shading:alt?altShading:undefined,margins:{top:70,bottom:30,left:120,right:120},children:[new Paragraph({children:it.desc})]}) ]}));
    rows.push(new TableRow({children:[
      cell("",{width:TR2[0],alt,align:AlignmentType.RIGHT,runs:curCellRuns(it.current,m,{prefix:it.curPrefix,suffix:it.curSuffix,curText:it.curText,curColor:it.changed?negativeColor:undefined})}),
      cell(fmtPct(day1pct(m)),{width:TR2[1],alt,align:AlignmentType.RIGHT,color:pctColor(day1pct(m))}),
      cell(fmtPct(m['1w_pct']),{width:TR2[2],alt,align:AlignmentType.RIGHT,color:pctColor(m['1w_pct'])}),
      cell(fmtPct(m['1mo_pct']),{width:TR2[3],alt,align:AlignmentType.RIGHT,color:pctColor(m['1mo_pct'])}),
      cell(fmtPct(m['3mo_pct']),{width:TR2[4],alt,align:AlignmentType.RIGHT,color:pctColor(m['3mo_pct'])}),
      cell(fmtPct(m['6mo_pct']),{width:TR2[5],alt,align:AlignmentType.RIGHT,color:pctColor(m['6mo_pct'])}),
      cell(fmtPct(m['1y_pct']),{width:TR2[6],alt,align:AlignmentType.RIGHT,color:pctColor(m['1y_pct'])}),
      imgCellSpark(it.chart,TR2[7],alt,150,46),
      cell(it.trend||koTrend(m),{width:TR2[8],alt,size:16}) ]}));
  });
  return rows; }
function trendRowC(name,m,i,chart,changed){ return new TableRow({children:[
  cell(name,{width:tw2[0],alt:i%2===1,bold:true}),
  cell(fmtNum(m&&m.current),{width:tw2[1],alt:i%2===1,align:AlignmentType.RIGHT,bold:changed===true,color:changed===true?negativeColor:undefined}),
  cell(fmtPct(m&&m['1w_pct']),{width:tw2[2],alt:i%2===1,align:AlignmentType.RIGHT,color:pctColor(m&&m['1w_pct'])}),
  cell(fmtPct(m&&m['1mo_pct']),{width:tw2[3],alt:i%2===1,align:AlignmentType.RIGHT,color:pctColor(m&&m['1mo_pct'])}),
  cell(fmtPct(m&&m['3mo_pct']),{width:tw2[4],alt:i%2===1,align:AlignmentType.RIGHT,color:pctColor(m&&m['3mo_pct'])}),
  cell(fmtPct(m&&m['6mo_pct']),{width:tw2[5],alt:i%2===1,align:AlignmentType.RIGHT,color:pctColor(m&&m['6mo_pct'])}),
  cell(fmtPct(m&&m['1y_pct']),{width:tw2[6],alt:i%2===1,align:AlignmentType.RIGHT,color:pctColor(m&&m['1y_pct'])}),
  imgCellSpark(chart,tw2[7],i%2===1),
  cell(koTrend(m),{width:tw2[8],alt:i%2===1})]}); }
function renderMarketBlockC(title,obj,labels,prev,comment){ if(!obj)return; children.push(h(title,2)); const items=[];
  for(const [k,v] of Object.entries(obj)){ if(v===null||typeof v!=="object")continue; const ch=prev&&prev[k]!==undefined&&prev[k]!==null&&Number(prev[k])!==Number(v&&v.current);
    items.push({desc:[new TextRun({text:((labels&&labels[k])||k.toUpperCase()),bold:true,size:20})],m:v,current:v&&v.current,chart:"charts/spark_"+k+".png",changed:ch}); }
  children.push(makeTable(TR2,trend2Rows(items))); if(comment)children.push(p("추세 평가: "+comment,{bold:true,color:"0F766E"})); children.push(p("")); }
function renderBerkshire(){ const b=data.berkshire; if(!b)return;
  children.push(new Paragraph({children:[new PageBreak()]}));
  children.push(h("[부록A] 워런 버핏 · 버크셔 해서웨이 보유 종목 변동 (13F)",1));
  children.push(p("공시 분기: "+(b.quarter||"-")+"    |    제출일: "+(b.filing_date||"-"),{bold:true}));
  if(b.summary)children.push(p(b.summary));
  if(b.cash)children.push(p("현금성 관련: "+b.cash,{size:18,color:"64748B"}));
  const sec=(title,arr)=>{ children.push(h(title,2));
    if(Array.isArray(arr)&&arr.length){ simpleTable([2400,1700,5900],["종목","티커","내용"],arr.map(x=>[x.name||x.ticker||"-",x.ticker||"-",x.detail||x.note||x.reason||"-"]),{left:[2]}); }
    else children.push(p("(이번 분기 해당 종목 없음)",{italics:true,color:"94A3B8",size:18})); };
  sec("A.1 신규 매수 (New)",b.new_buys);
  sec("A.2 비중 확대 (Added)",b.added);
  sec("A.3 비중 축소 (Reduced)",b.reduced);
  sec("A.4 전량 매도 (Exited)",b.exited);
  if(Array.isArray(b.top_holdings)&&b.top_holdings.length){ children.push(h("A.5 상위 보유 종목",2));
    simpleTable([2300,1500,2400,3800],["종목","티커","비중/평가액","비고"],b.top_holdings.map(x=>[x.name||"-",x.ticker||"-",x.weight_or_value||"-",x.note||"-"]),{left:[3]}); }
  children.push(p("※ 13F는 미국 상장 주식 롱 포지션만 공시하며 분기 종료 후 최대 45일의 시차가 있습니다. 새 분기 13F가 공시되면 이 섹션을 업데이트합니다.",{size:18,italics:true,color:"64748B"}));
  if(Array.isArray(b.sources)&&b.sources.length){ children.push(p("출처:",{bold:true,size:18}));
    b.sources.forEach(sr=>children.push(reportBullet(sr))); }
}
function markStance(s){ s=String(s||""); if(s.includes("매파"))return negativeColor; if(s.includes("비둘기"))return positiveColor; return "334155"; }

function hdrRow(labels,w){ return new TableRow({children:labels.map((x,i)=>cell(x,{width:w[i],header:true,align:AlignmentType.CENTER}))}); }

function renderMacroIndicators(){
  const M=data.markets||{}; const x=M.macro; if(!x)return;
  children.push(h("3.1 주요지표 (매크로 대시보드)",2));
  children.push(p("증시 방향을 좌우하는 금리·물가·고용·심리 지표를 의미·발표주기·시장영향과 함께 정리한다.",{italics:true,color:"64748B"}));

  // 3.1.1 금리·통화정책 (REQ2 순서: 美10년물 → 장단기차 → HY → 기준금리 → FOMC회의 → 점도표)
  const r=x.rates||{};
  children.push(h("3.1.1 금리·통화정책 (가장 직접적 영향)",3));
  // [1] 美 10년물 국채금리 (매일 실측)
  if(r.us10y){ const o=r.us10y; const w=[1500,1100,700,700,700,700,700,700,1200,1900];
    children.push(p("■ 美 10년물 국채금리",{bold:true,color:"1E40AF",size:22,before:60}));
    const rows=[hdrRow(["지표","현재가","1일","1주","1개월","3개월","6개월","1년","추세(1Y)","추세 평가"],w)];
    rows.push(new TableRow({children:[cell("美 10년물 국채금리",{width:w[0],bold:true}),
      cell("",{width:w[1],align:AlignmentType.RIGHT,runs:curCellRuns(o.current,o,{suffix:"%"})}),
      cell(fmtPct(day1pct(o)),{width:w[2],align:AlignmentType.RIGHT,color:pctColor(day1pct(o))}),
      cell(fmtPct(o["1w_pct"]),{width:w[3],align:AlignmentType.RIGHT,color:pctColor(o["1w_pct"])}),cell(fmtPct(o["1mo_pct"]),{width:w[4],align:AlignmentType.RIGHT,color:pctColor(o["1mo_pct"])}),
      cell(fmtPct(o["3mo_pct"]),{width:w[5],align:AlignmentType.RIGHT,color:pctColor(o["3mo_pct"])}),cell(fmtPct(o["6mo_pct"]),{width:w[6],align:AlignmentType.RIGHT,color:pctColor(o["6mo_pct"])}),
      cell(fmtPct(o["1y_pct"]),{width:w[7],align:AlignmentType.RIGHT,color:pctColor(o["1y_pct"])}),imgCellSpark(o.spark,w[8],false,150,40),cell(o.trend||"-",{width:w[9],size:16})]}));
    children.push(makeTable(w,rows));
    children.push(p("의미: 장기 금리·기준이자율 역할 · 시장영향: 10년물↑ → 기술·성장주 부담·채권↓",{size:16,color:"64748B"}));
    children.push(p("업데이트: 매일 (Yahoo ^TNX·FMP 실측). 현재가 옆=당일 전일대비 변동(▲/▼·%), '1일'=직전 거래일의 1일 변동률.",{size:15,italics:true,color:"94A3B8"})); }
  // [2] 미국 장단기 금리차 (10Y-2Y, 매일 실측)
  if(r.yield_curve){ const yc=r.yield_curve;
    children.push(p("■ "+(yc.label||"미국 장단기 금리차(수익률곡선)(10Y-2Y)"),{bold:true,size:22,color:"1E40AF",before:140}));
    children.push(p((yc.spread>=0?"+":"")+yc.spread+"%p → "+yc.status+"  ("+(yc.note||"")+")",{bold:true,size:22,color:"1E40AF"}));
    children.push(p("의미: "+(yc.meaning||"")+" · 시장영향: "+(yc.impact||""),{size:16,color:"64748B"}));
    children.push(p("업데이트: 매일 (FRED T10Y2Y 실측, 최근 1년 추이).",{size:15,italics:true,color:"94A3B8"}));
    const cc=imagePara(yc.chart,648,176); if(cc)children.push(cc); }
  // [3] 하이일드(HY) 스프레드 (매일)
  renderHY();
  // [4] FOMC 기준금리 + 6개국 정책금리 (변동 시 갱신·실측)
  if(r.fed_funds){ const f=r.fed_funds;
    children.push(p("■ FOMC 기준금리(현재): "+f.current+"%   ("+f.decision+" / "+f.bias+")",{bold:true,size:23,color:"1E40AF",before:140}));
    children.push(p("의미: "+f.meaning+" · 발표: "+f.freq+" · 시장영향: "+f.impact,{size:17,color:"64748B"}));
    children.push(p("업데이트: 매 실행 변동 여부만 체크 → FOMC 결정으로 변동 시에만 갱신, 없으면 기존 자료 유지 (FMP 실측).",{size:15,italics:true,color:"94A3B8"})); }
  if(Array.isArray(r.policy_rates)){
    const w=[2100,1600,1700,4680]; const rows=[hdrRow(["국가","현재 정책금리","기준일","비고"],w)];
    r.policy_rates.forEach((c,i)=>rows.push(new TableRow({children:[cell(c.country,{width:w[0],alt:i%2===0,bold:true}),
      cell(c.rate!=null?c.rate+"%":"-",{width:w[1],alt:i%2===0,align:AlignmentType.CENTER}),cell(c.asof||"-",{width:w[2],alt:i%2===0,align:AlignmentType.CENTER}),cell(c.note||"",{width:w[3],alt:i%2===0,size:16})]})));
    children.push(makeTable(w,rows));
    children.push(p("주요 6개국 정책금리 — 각국 중앙은행 실측치(추정 아님). 업데이트: 매 실행 변동 체크 → 변동 시에만 갱신.",{size:15,italics:true,color:"94A3B8"}));
    const pc=imagePara(r.policy_rates_chart,648,243); if(pc){children.push(pc);} }
  // [5] FOMC 회의 일정·정책방향 (신규 회의 시 갱신)
  if(Array.isArray(r.fomc_meetings)){
    children.push(p("■ FOMC 회의 일정·정책방향 (최근 1년 · 최신순)",{bold:true,color:"1E40AF",before:140,size:22}));
    const w=[2200,2300,5580]; const rows=[hdrRow(["회의일","정책방향","결정·코멘트"],w)];
    r.fomc_meetings.slice().reverse().forEach((mt,i)=>rows.push(new TableRow({children:[
      cell(mt.date,{width:w[0],alt:i%2===0,align:AlignmentType.CENTER,bold:true}),
      cell(mt.stance,{width:w[1],alt:i%2===0,align:AlignmentType.CENTER,bold:true,color:markStance(mt.stance)}),
      cell(mt.note||"",{width:w[2],alt:i%2===0})]})));
    children.push(makeTable(w,rows));
    children.push(p("의미: 연준 정책방향(매파/비둘기파) · 발표: 회의 후 즉시",{size:16,color:"64748B"}));
    children.push(p("업데이트: 매 실행 신규 FOMC 개최 여부 체크 → 새 회의 있을 때만 갱신, 없으면 기존 자료 유지.",{size:15,italics:true,color:"94A3B8"}));
    if(r.fomc_market_impact)children.push(p("시장영향: "+r.fomc_market_impact,{size:17,bold:true,color:"334155"})); }
  // [6] FOMC 점도표
  renderFomcDotplot();
  children.push(p(""));

  // 3.1.2 물가 — 추세1Y 제거, 통합 그래프 하나
  const inf=x.inflation||{};
  children.push(h("3.1.2 물가·인플레이션 (금리 방향 결정)",3));
  children.push(p("업데이트: 매일 체크 → 신규 지표 발표 시에만 갱신, 없으면 기존 자료 유지 (FMP/FRED 실측, 추정 미사용).",{size:15,italics:true,color:"94A3B8"}));
  children.push(p("발표주기: 모두 매월 · 1년 월별 추세는 아래 통합 그래프 1개로 표시.",{italics:true,size:16,color:"94A3B8"}));
  { const w=[1900,900,900,1000,2300,3080]; const rows=[hdrRow(["지표","YoY","MoM","기준월","의미","시장영향"],w)];
    (inf.rows||[]).forEach((o,i)=>{ const a=i%2===1; rows.push(new TableRow({children:[
      cell(o.name,{width:w[0],alt:a,bold:true}), cell((o.yoy>=0?"+":"")+o.yoy+"%",{width:w[1],alt:a,align:AlignmentType.CENTER}),
      cell((o.mom>=0?"+":"")+o.mom+"%",{width:w[2],alt:a,align:AlignmentType.CENTER}), cell(o.asof,{width:w[3],alt:a,align:AlignmentType.CENTER}),
      cell(o.meaning,{width:w[4],alt:a,size:16}), cell(o.impact,{width:w[5],alt:a,size:16})]})); });
    children.push(makeTable(w,rows)); }
  { const ic=imagePara(inf.chart,660,259); if(ic){ children.push(ic); children.push(p("CPI·Core CPI·PCE·Core PCE·PPI 최근 12개월 YoY 통합 추이",{size:15,color:"94A3B8"})); } }
  if(inf.infl_exp_10y){ const e=inf.infl_exp_10y;
    children.push(p("■ 기대인플레이션 (10년 BEI)",{bold:true,color:"1E40AF",before:120}));
    children.push(p("현재값: "+e.current+"%   "+(e.trend||""),{bold:true,size:22,color:"1E40AF"}));
    const ic2=imagePara(e.chart,648,176); if(ic2){ children.push(ic2); children.push(p("기대인플레이션 10년(BEI) 최근 1년 추이 · 점선=2%",{size:15,color:"94A3B8"})); }
    children.push(p("의미: "+e.meaning+" · 발표주기: "+e.freq+" · 시장영향: "+e.impact,{size:16,color:"64748B"})); }
  children.push(p(""));

  // 3.1.3 고용 — 추세1Y 제거, 통합 그래프 하나
  const emp=x.employment||{};
  children.push(h("3.1.3 고용·경기 (금리 간접 영향)",3));
  { const w=[2100,1400,1200,2300,3080]; const rows=[hdrRow(["지표","최신 수치","기준","의미","시장영향"],w)];
    (emp.rows||[]).forEach((o,i)=>{ const a=i%2===1; rows.push(new TableRow({children:[
      cell(o.name,{width:w[0],alt:a,bold:true}), cell(o.value,{width:w[1],alt:a,align:AlignmentType.CENTER,bold:true}),
      cell(o.asof,{width:w[2],alt:a,align:AlignmentType.CENTER}), cell(o.meaning+" · "+o.freq,{width:w[3],alt:a,size:16}), cell(o.impact,{width:w[4],alt:a,size:16})]})); });
    children.push(makeTable(w,rows)); }
  { const ec=imagePara(emp.chart,660,288); if(ec){ children.push(ec); children.push(p("NFP·실업률·GDP·ISM 제조/서비스·소매판매 최근 1년 통합",{size:15,color:"94A3B8"})); } }
  children.push(p(""));

  // 3.1.4 심리 — 6개월 추가
  const s=x.sentiment||{};
  children.push(h("3.1.4 심리·자금흐름 보조지표",3));
  { const w=[1400,1050,700,700,700,700,700,700,1230,2000]; const rows=[hdrRow(["지표","현재가","1일","1주","1개월","3개월","6개월","1년","추세(1Y)","추세 평가"],w)];
    (s.rows||[]).forEach((o,i)=>{ const a=i%2===1; rows.push(new TableRow({children:[
      cell(o.name,{width:w[0],alt:a,bold:true}), cell("",{width:w[1],alt:a,align:AlignmentType.RIGHT,runs:curCellRuns(o.current,o,{})}),
      cell(fmtPct(day1pct(o)),{width:w[2],alt:a,align:AlignmentType.RIGHT,color:pctColor(day1pct(o))}),
      cell(fmtPct(o['1w_pct']),{width:w[3],alt:a,align:AlignmentType.RIGHT,color:pctColor(o['1w_pct'])}), cell(fmtPct(o['1mo_pct']),{width:w[4],alt:a,align:AlignmentType.RIGHT,color:pctColor(o['1mo_pct'])}),
      cell(fmtPct(o['3mo_pct']),{width:w[5],alt:a,align:AlignmentType.RIGHT,color:pctColor(o['3mo_pct'])}), cell(fmtPct(o['6mo_pct']),{width:w[6],alt:a,align:AlignmentType.RIGHT,color:pctColor(o['6mo_pct'])}),
      cell(fmtPct(o['1y_pct']),{width:w[7],alt:a,align:AlignmentType.RIGHT,color:pctColor(o['1y_pct'])}), imgCellSpark(o.spark,w[8],a,150,40), cell(o.trend,{width:w[9],alt:a,size:16})]})); });
    children.push(makeTable(w,rows)); }
  { const w=[2000,2900,5180]; const rows=[hdrRow(["지표","의미","활용"],w)];
    (s.rows||[]).forEach((o,i)=>rows.push(new TableRow({children:[cell(o.name,{width:w[0],alt:i%2===1,bold:true}),
      cell(o.meaning,{width:w[1],alt:i%2===1,size:17}),cell(o.use,{width:w[2],alt:i%2===1,size:17})]})));
    children.push(makeTable(w,rows)); }
  children.push(p(""));
  children.push(h("3.1.5 지수·Forward EPS·PER (실적 vs 밸류에이션)",3));
  children.push(p("선행 EPS(향후 12개월 예상 이익)와 지수·선행 PER 의 관계로 '실적장세 vs 밸류 부담'을 점검한다. 지수는 실측, 선행 EPS 는 컨센서스 기반 추정.",{italics:true,color:"64748B"}));
  if(s.spx_fwd){ const e=s.spx_fwd;
    children.push(p("■ S&P500 12M Forward EPS: $"+e.fwd_eps+"  ·  선행 PER: "+e.fwd_per+"배  (지수 약 7,500 / "+e.asof+")",{bold:true,color:"1E40AF",before:100}));
    const c=imagePara(e.chart,660,241); if(c)children.push(c); if(e.note)children.push(p(e.note,{size:15,color:"94A3B8"})); }
  if(s.kospi_fwd){ const e=s.kospi_fwd;
    children.push(p("■ KOSPI 12M Forward EPS: "+e.fwd_eps+"  ·  선행 PER: "+e.fwd_per+"배  (지수 약 9,000 / "+e.asof+")",{bold:true,color:"1E40AF",before:80}));
    const c=imagePara(e.chart,660,241); if(c)children.push(c); if(e.note)children.push(p(e.note,{size:15,color:"94A3B8"})); }
  children.push(p("선행EPS 해석: EPS↑+지수↑=실적장세 · EPS↑인데 지수 정체=밸류부담 점검 · EPS 꺾이면 성장주 탄력 둔화",{size:16,color:"64748B"}));
  children.push(p(""));
  renderCapex();
  renderHBM();
}

if (data.markets) {
  renderMacroIndicators();
  renderMarketBlock("3.2 한국 증시",data.markets.korea,{kospi:"코스피",kosdaq:"코스닥"});
  renderKoreaExtras();
  renderMarketBlockC("3.3 미국 증시",{sp500:(data.markets.us_markets||{}).sp500,nasdaq:(data.markets.us_markets||{}).nasdaq,dow:(data.markets.us_markets||{}).dow},{sp500:"S&P 500",nasdaq:"나스닥",dow:"다우"},data.markets.us_prev);
  children.push(p("※ 현재치는 매 실행 시 최신값으로 갱신되며, 직전 보고서 대비 값이 변동된 항목은 빨간색으로 강조됩니다.",{size:16,italics:true,color:"94A3B8"}));
  // (VIX 설명은 3.1.4 주요지표 심리지표로 이동)
  renderUSExtras();
  renderMarketBlockC("3.4 아시아 증시",data.markets.asia_markets,{nikkei:"닛케이 225",shanghai:"상하이종합",hsi:"홍콩 항셍",taiwan:"대만 가권",sensex:"인도 센섹스",vietnam:"베트남 (VNM)"});
  renderMarketBlockC("3.5 유럽 증시",data.markets.europe_markets,{stoxx50:"유로 스톡스 50",dax:"독일 DAX",ftse:"영국 FTSE 100"});
}
children.push(new Paragraph({children:[new PageBreak()]}));
children.push(h("4. 원자재 종합 - 에너지·금속·희토류·농산물",1));
if (data.commodities) {
  renderMarketBlockC("4.1 에너지",data.commodities.energy,{wti:"WTI 원유",brent:"Brent 원유",natgas:"천연가스"},null,data.commodities.energy_comment);
  renderMarketBlockC("4.2 금속",data.commodities.metals,{gold:"금",silver:"은",copper:"구리",platinum:"백금"},null,data.commodities.metals_comment);
  renderMarketBlockC("4.3 농산물",data.commodities.agriculture,{corn:"옥수수",soybean:"대두",wheat:"밀"},null,data.commodities.agri_comment);
  if(data.commodities.commentary){ children.push(h("4.4 원자재 종합 코멘트",2)); children.push(p(data.commodities.commentary)); }
  renderStrategicMetals();
}
children.push(new Paragraph({children:[new PageBreak()]}));
children.push(h("5. 주요 환율 단·중·장기 추세",1));
if (data.markets && data.markets.fx_markets) {
  children.push(p("환율 상승 = 원화 약세. DXY는 6개 주요통화 대비 달러 가치.",{italics:true,color:"64748B"}));
  const fl={usd_krw:"USD/KRW",eur_krw:"EUR/KRW",jpy_krw:"JPY/KRW (100엔)",cny_krw:"CNY/KRW",hkd_krw:"HKD/KRW"};
  const fitems=[];
  for(const [k,v] of Object.entries(data.markets.fx_markets)){ if(v&&typeof v==="object") fitems.push({desc:[new TextRun({text:(fl[k]||k.toUpperCase()),bold:true,size:20})],m:v,current:v.current,chart:"charts/spark_"+k+".png"}); }
  if(data.markets.us_markets&&data.markets.us_markets.dxy){ fitems.push({desc:[new TextRun({text:"달러인덱스 (DXY)",bold:true,size:20})],m:data.markets.us_markets.dxy,current:data.markets.us_markets.dxy.current,chart:"charts/spark_dxy.png"}); }
  if(data.markets.fx_usd){ const fu=data.markets.fx_usd; const um={usd_jpy:["USD/JPY","spark_usd_jpy"],usd_cny:["USD/CNY","spark_usd_cny"],usd_eur:["USD/EUR","spark_usd_eur"]};
    for(const k of Object.keys(um)){ if(fu[k]){ fitems.push({desc:[new TextRun({text:um[k][0],bold:true,size:20})],m:fu[k],current:fu[k].current,chart:"charts/"+um[k][1]+".png"}); } } }
  children.push(makeTable(TR2,trend2Rows(fitems)));
  children.push(p("USD/KRW~HKD/KRW는 원화 기준(상승=원화 약세), USD/JPY·USD/CNY·USD/EUR는 미국달러 기준 국제 환율. USD/EUR은 1달러당 유로(EUR/USD의 역수)로 표기.",{size:16,italics:true,color:"94A3B8"}));
}
if (data.news && data.news.fx_snapshot && (data.news.fx_snapshot.krw_trend||data.news.fx_snapshot.krw_comment)) {
  const fx=data.news.fx_snapshot; children.push(p("")); children.push(p(`원화 톤: ${fx.krw_trend||'-'}`,{bold:true})); if(fx.krw_comment) children.push(p(fx.krw_comment));
}
children.push(new Paragraph({children:[new PageBreak()]}));
children.push(h("6. 암호화폐 시장",1));
if (data.crypto) {
  const c=data.crypto;
  if (c.market_overview) { children.push(h("6.1 시장 개요",2)); const mo=c.market_overview; const vol=Number(mo.total_volume_24h_usd);
    children.push(bullet(`24시간 거래량: ${isNaN(vol)||!vol?"-":"$"+(vol/1e8).toFixed(1)+"억"}`));
    children.push(bullet(`평균 변동: ${mo.avg_change_pct??"-"}%`));
    children.push(bullet(`상승 ${mo.coins_up??"-"}개 / 하락 ${mo.coins_down??"-"}개`));
    if(mo.btc_dominance!==undefined&&mo.btc_dominance!==null) children.push(bullet(`BTC Dominance: ${mo.btc_dominance}%`)); }
  if(c.charts){ children.push(h("6.2 주요 코인 1년 차트 (가격·거래량) · 공포·탐욕 지수",2));
    const cc=c.charts; const cells=[["BTC",cc.btc],["ETH",cc.eth],["XRP",cc.xrp],["SOL",cc.sol]];
    const imgCell=(pth)=>{ const ip=imagePara(pth,232,137); return new TableCell({borders,width:{size:4900,type:WidthType.DXA},margins:{top:50,bottom:50,left:50,right:50},children:[ip||p("(차트 없음)")]}); };
    for(let rr=0;rr<2;rr++){ children.push(makeTable([4900,4900],[new TableRow({children:[imgCell(cells[rr*2][1]),imgCell(cells[rr*2+1][1])]})])); }
    const fgi=imagePara(cc.fng,560,153); if(fgi){ children.push(p("공포·탐욕 지수 (Crypto Fear & Greed, 1년)",{bold:true,color:"1E40AF",before:80})); children.push(fgi); children.push(p("배경: 빨강=극공포 / 주황=공포 / 노랑=중립 / 연두~초록=탐욕",{size:15,color:"94A3B8"})); } }
  if (c.kimchi_premium && Array.isArray(c.kimchi_premium.coins) && c.kimchi_premium.coins.length) {
    children.push(h("6.3 김치 프리미엄",2)); children.push(p(`기준 환율: 1 USD = ${c.kimchi_premium.rate_usd_krw??"-"} KRW`));
    const kA=co=>({u:co.upbit_krw??co.upbit_price_krw,b:co.binance_usd??co.global_price_usd??co.binance_price_usd,pp:co.premium_pct??co.premium_percent});
    const kr=[["코인","업비트 (KRW)","바이낸스 (USD)","프리미엄","상태"],...c.kimchi_premium.coins.map(co=>{const a=kA(co);return [co.symbol??"-",(a.u!==undefined&&a.u!==null)?`₩${Number(a.u).toLocaleString()}`:"-",(a.b!==undefined&&a.b!==null)?`$${a.b}`:"-",(a.pp!==undefined&&a.pp!==null)?`${a.pp}%`:"-",co.status||"-"];})].map((r,i)=>new TableRow({children:r.map((cc,j)=>cell(cc,{width:[1200,2500,2400,1660,1600][j],header:i===0,alt:i>0&&i%2===0,align:AlignmentType.CENTER,bold:(j===0||j===3)&&i>0,color:(j===3&&i>0)?pctColor(kA(c.kimchi_premium.coins[i-1]).pp):undefined}))}));
    children.push(makeTable([1200,2500,2400,1660,1600],kr)); }
  if (Array.isArray(c.top_gainers) && c.top_gainers.length) {
    children.push(h("6.4 24h Top Gainers / Losers",2)); const g=(c.top_gainers||[]).slice(0,5),l=(c.top_losers||[]).slice(0,5),mx=Math.max(g.length,l.length);
    const gr=[["순위","Top Gainer","변동","Top Loser","변동"]];
    for(let i=0;i<mx;i++){ gr.push([String(i+1),g[i]?g[i].symbol:"-",g[i]?fmtPct(g[i].change_pct):"-",l[i]?l[i].symbol:"-",l[i]?fmtPct(l[i].change_pct):"-"]); }
    children.push(makeTable([1000,2400,1900,2400,1660],gr.map((r,i)=>new TableRow({children:r.map((cc,j)=>cell(cc,{width:[1000,2400,1900,2400,1660][j],header:i===0,alt:i>0&&i%2===0,align:AlignmentType.CENTER,color:(j===2&&i>0)?positiveColor:(j===4&&i>0)?negativeColor:undefined}))})))); }

}
children.push(new Paragraph({children:[new PageBreak()]}));
children.push(h("7. 한국 주요 증권사 리서치",1));
const secLabels={samsung:"삼성증권",miraeasset:"미래에셋증권",korea_inv:"한국투자증권",shinhan:"신한투자증권",kiwoom:"키움증권",meritz:"메리츠증권",hana:"하나증권",kyobo:"교보증권",yuanta:"유안타증권",hyundai:"현대차증권"};
const secVF={shinhan:["asset_allocation_view","자산배분 시각"],miraeasset:["etf_emerging_view","ETF·신흥국 시각"],samsung:["derivatives_view","파생·선물 시각"],korea_inv:["ib_china_view","IB·중국 시각"],kiwoom:["global_etf_view","글로벌 ETF·신흥국 시각"],meritz:["sector_view","섹터·반도체 시각"],hana:["china_view","중국·글로벌 시각"],kyobo:["bond_view","채권·매크로 시각"],yuanta:["daily_view","데일리 섹터 시각"],hyundai:["industrial_view","산업·방산 시각"]};
const coreSet=new Set(["samsung","miraeasset","korea_inv","shinhan","kiwoom","meritz"]);
if (data.securities) { let idx=0;
  for(const key of Object.keys(secLabels)){ const sec=data.securities[key]; if(!sec||!coreSet.has(key))continue; idx++;
    children.push(h(`7.${idx} ${secLabels[key]}`,2));
    if(sec.strength) children.push(p(`핵심 강점: ${sec.strength}`,{bold:true,color:"1E40AF"}));
    if(Array.isArray(sec.channels)&&sec.channels.length) children.push(p(`주요 채널: ${sec.channels.join(' / ')}`,{italics:true,color:"475569"}));
    if(sec.key_message) children.push(p(`오늘의 메시지: ${viewText(sec.key_message)}`));
    const vf=secVF[key]; if(vf&&sec[vf[0]]) children.push(p(`${vf[1]}: ${viewText(sec[vf[0]])}`,{color:"0F766E"}));
    if(Array.isArray(sec.key_reports)&&sec.key_reports.length){ children.push(p("대표 리포트:",{bold:true,after:40})); sec.key_reports.forEach(r=>children.push(reportBullet(r))); }
    else children.push(p("(리포트 수집 실패 - 사이트 접근 제한)",{italics:true,color:"94A3B8"})); }
  const others=Object.keys(secLabels).filter(k=>!coreSet.has(k)&&data.securities[k]);
  if(others.length){ idx++; children.push(h(`7.${idx} 기타 증권사 (핵심 메시지 요약)`,2)); others.forEach(key=>{ const sec=data.securities[key]; const km=viewText(sec.key_message)||"(수집)"; children.push(p(`${secLabels[key]}: ${km}`)); }); }
  if(Array.isArray(data.securities.common_themes)&&data.securities.common_themes.length){ idx++; children.push(h(`7.${idx} 공통 핵심 주제`,2)); data.securities.common_themes.forEach(t=>children.push(bullet(t))); }
  // (7.9 투자자 유형별 추천 조합 — 사용자 요청으로 삭제됨)
}
children.push(new Paragraph({children:[new PageBreak()]}));
children.push(h("8. 글로벌 주요 IB 리서치 (UBS·GS·JPM·MS·BlackRock)",1));
const gL={ubs:"UBS",goldman:"Goldman Sachs",jpmorgan:"J.P. Morgan",morgan_stanley:"Morgan Stanley",blackrock:"BlackRock"};
const gVF={ubs:["house_view","CIO 하우스 뷰"],goldman:["macro_commodity_view","매크로·원자재 시각"],jpmorgan:["global_strategy_view","글로벌 전략 시각"],morgan_stanley:["us_equity_view","미국주식 전략 시각"],blackrock:["etf_allocation_view","ETF·자산배분 시각"]};
if (data.global_securities) { let gi=0;
  for(const key of Object.keys(gL)){ const sec=data.global_securities[key]; if(!sec)continue; gi++;
    children.push(h(`8.${gi} ${gL[key]}`,2));
    if(sec.strength) children.push(p(`핵심 강점: ${sec.strength}`,{bold:true,color:"1E40AF"}));
    if(Array.isArray(sec.channels)&&sec.channels.length) children.push(p(`공개 채널: ${sec.channels.join(' / ')}`,{italics:true,color:"475569"}));
    if(sec.key_message) children.push(p(`오늘의 메시지: ${viewText(sec.key_message)}`));
    const vf=gVF[key]; if(vf&&sec[vf[0]]) children.push(p(`${vf[1]}: ${viewText(sec[vf[0]])}`,{color:"0F766E"}));
    if(Array.isArray(sec.key_reports)&&sec.key_reports.length){ children.push(p("대표 발간물:",{bold:true,after:40})); sec.key_reports.forEach(r=>children.push(reportBullet(r))); }
    else if(!sec.key_message&&!(gVF[key]&&sec[gVF[key][0]])) children.push(p("(수집 실패 또는 비공개)",{italics:true,color:"94A3B8"})); }
  if(Array.isArray(data.global_securities.common_themes)&&data.global_securities.common_themes.length){ children.push(h("8.6 글로벌 IB 공통 핵심 주제",2)); data.global_securities.common_themes.forEach(t=>children.push(bullet(t))); }
  if(data.global_securities.wall_street_consensus){ var _w=data.global_securities.wall_street_consensus; var _ws=(_w&&typeof _w==="object")?Object.keys(_w).map(function(k){var v=_w[k];return k+": "+((v&&typeof v==="object")?Object.keys(v).map(function(a){return a+" "+v[a];}).join(", "):String(v));}).join("  /  "):String(_w); children.push(h("8.7 월가 컨센서스",2)); children.push(p(_ws)); }
  children.push(p("※ 해외 IB 원문은 고객 전용 — 공개 Insights·언론 보도 기반 요약입니다.",{italics:true,color:"94A3B8",size:18}));
} else children.push(p("(글로벌 IB 데이터 없음)"));
children.push(new Paragraph({children:[new PageBreak()]}));
children.push(h("9. 종합 분석 - 매크로·테마·리스크",1));
children.push(p("※ 이하 9~12장은 앞 장 데이터에 근거한 AI 의견이며 투자 권유가 아닙니다.",{italics:true,color:"B45309",size:18}));
if (data.analysis) { const a=data.analysis;
  if(a.macro_view){ children.push(h("9.1 매크로 톤",2)); children.push(p(a.macro_view)); }
  if(Array.isArray(a.key_themes)&&a.key_themes.length){ children.push(h("9.2 핵심 테마",2)); const th=[["테마","방향","코멘트"]]; a.key_themes.forEach(t=>th.push([t.theme||"-",t.direction||"-",t.comment||"-"]));
    children.push(makeTable([2400,1400,5560],th.map((r,i)=>new TableRow({children:r.map((cc,j)=>cell(cc,{width:[2400,1400,5560][j],header:i===0,alt:i>0&&i%2===0,bold:(j===0||j===1)&&i>0,align:j===1?AlignmentType.CENTER:AlignmentType.LEFT,color:(j===1&&i>0)?markColor(cc):undefined}))})))); }
  if(Array.isArray(a.key_risks)&&a.key_risks.length){ children.push(h("9.3 핵심 리스크",2)); a.key_risks.forEach(r=>children.push(bullet(r,{color:negativeColor}))); }
}
if (data.analysis && data.analysis.asset_view) {
  children.push(new Paragraph({children:[new PageBreak()]})); children.push(h("10. 자산별 단·중·장기 견해",1)); const av=data.analysis.asset_view;
  const am=[["미국 주식",av.us_equity],["한국 주식",av.kr_equity],["중국 주식",av.china_equity||av.cn_equity],["일본 주식",av.japan_equity||av.jp_equity],["신흥시장 주식",av.em_equity],["유럽 주식",av.europe_equity||av.eu_equity],["한국 채권",av.kr_treasury||av.kr_bond],["美 국채",av.us_treasury||av.us_bond],["금 (Gold)",av.gold],["원유 (Oil)",av.oil],["비트코인 (BTC)",av.btc]];
  children.push(makeTable([2400,6960],[["자산군","단·중·장기 견해"],...am].map((r,i)=>new TableRow({children:r.map((cc,j)=>cell(cc||"-",{width:[2400,6960][j],header:i===0,alt:i>0&&i%2===0,bold:j===0&&i>0}))}))));
}
if (data.analysis && data.analysis.portfolios) {
  children.push(new Paragraph({children:[new PageBreak()]})); children.push(h("11. 추천 포트폴리오 (공격형 · 중립형 · 안정형)",1));
  children.push(p("아래 포트폴리오는 모델 예시이며 개인 위험감내도·투자목표·세금 상황에 따라 조정해야 한다.",{italics:true,color:"64748B"}));
  const pf=data.analysis.portfolios;
  [{key:'aggressive'},{key:'balanced'},{key:'conservative'}].forEach((o,idx)=>{ const pfo=pf[o.key]; if(!pfo)return;
    children.push(h(`11.${idx+1} ${pfo.label||o.key}`,2));
    [['기대수익',pfo.expected_return],['최대 낙폭(MDD)',pfo.max_drawdown],['리밸런싱 주기',pfo.rebalance]].forEach(([k,v])=>{ if(v) children.push(bullet(`${k}: ${v}`)); });
    if(pfo.basis) children.push(p(`산출 근거: ${pfo.basis}`,{italics:true,color:"64748B",size:18})); else children.push(p("산출 근거: (미기재 — 추정치 신뢰도 주의)",{italics:true,color:"B45309",size:18}));
    if(Array.isArray(pfo.allocation)){ const ws=pfo.allocation.reduce((s,a)=>s+(Number(a.weight_pct)||0),0); if(ws!==100) console.error(`  (경고) ${o.key} 비중합 ${ws}%`);
      children.push(makeTable([3400,1200,4760],[["자산","비중","구체적 방안 (종목·ETF)"],...pfo.allocation.map(a=>[a.asset||"-",`${a.weight_pct??"-"}%`,a.vehicle||"-"])].map((r,i)=>new TableRow({children:r.map((cc,j)=>cell(cc,{width:[3400,1200,4760][j],header:i===0,alt:i>0&&i%2===0,bold:(j===0||j===1)&&i>0,align:j===1?AlignmentType.CENTER:AlignmentType.LEFT}))})))); children.push(p("")); }
  });
}
if (data.analysis && Array.isArray(data.analysis.action_items) && data.analysis.action_items.length) {
  children.push(new Paragraph({children:[new PageBreak()]})); children.push(h("12. 액션 아이템 - 단기·중기·장기 체크리스트",1));
  data.analysis.action_items.forEach(it=>children.push(bullet((it&&typeof it==="object")?((it.horizon?("["+it.horizon+"] "):"")+(it.item||it.text||it.action||"")):String(it))));
}
children.push(new Paragraph({children:[new PageBreak()]}));
children.push(h("13. 주의 사항 및 출처",1));
children.push(p("본 보고서는 AI가 공개 데이터(Yahoo Finance, CoinGecko, 한국경제, 주요 증권사·글로벌 IB 공개 리서치 등)를 자동 수집·종합해 생성한 참고용 자료입니다.",{italics:true}));
children.push(p("자동 생성(AI) 특성상 오류·환각이 포함될 수 있습니다. 1~8장은 출처 링크로 검증 가능하며, 9~12장은 AI 의견입니다.",{italics:true,color:"B45309"}));
children.push(p("어떤 내용도 매수·매도 권유나 보장 수익을 약속하지 않으며, 투자 판단의 최종 책임은 이용자에게 있습니다.",{italics:true,color:"64748B"}));
children.push(p(""));
const genAt=(data.metadata&&data.metadata.generated_at)?String(data.metadata.generated_at):"-";
children.push(p(`데이터 기준일: ${reportDate}  |  보고서 생성시각: ${genAt}`,{size:18,color:"64748B"}));
children.push(p("주요 출처: Yahoo Finance / CoinGecko / 한국경제 / 신한·미래에셋·삼성·한국투자·키움 / UBS·GS·JPM·MS·BlackRock 공개 채널",{size:18,color:"94A3B8"}));

function renderAITrends(){ const a=data.ai_trends; if(!a)return;
  const items=Array.isArray(a)?a:(Array.isArray(a.items)?a.items:[]); if(!items.length)return;
  const asOf=(!Array.isArray(a)&&a.as_of)||(data.metadata&&data.metadata.report_date)||"-";
  const srcs=(!Array.isArray(a)&&Array.isArray(a.sources_checked))?a.sources_checked:[];
  children.push(new Paragraph({children:[new PageBreak()]}));
  children.push(h("[부록B] 최신 AI Trends (국문·영문 병기)",1));
  children.push(p("기준: "+asOf+(srcs.length?("   ·   확인 소스: "+srcs.join(", ")):""),{size:17,color:"94A3B8"}));
  items.forEach((it,k)=>{ const tag=it.tag?("["+it.tag+"] "):"";
    children.push(p((k+1)+". "+tag+(it.title||"-"),{bold:true,size:22,before:80}));
    if(it.summary)children.push(p(it.summary,{size:20}));
    if(it.title_en)children.push(p("EN ▸ "+it.title_en,{bold:true,size:19,color:"1E40AF",before:40}));
    if(it.summary_en)children.push(p(it.summary_en,{size:18,color:"475569"}));
    const meta=[it.source,it.date].filter(Boolean).join(" · ");
    if(it.url&&HAS_LINK){ children.push(new Paragraph({spacing:{after:80},children:[ new TextRun({text:(meta?meta+"   ":""),size:16,color:"64748B"}), new ExternalHyperlink({link:String(it.url),children:[new TextRun({text:"[원문 링크]",size:16,color:"1D4ED8",underline:{}})]}) ]})); }
    else if(meta){ children.push(p(meta,{size:16,color:"64748B"})); }
  });
  children.push(p("※ 본 부록은 news.hada.io · news.hada.io/weekly · 특이점 갤러리 등 공개 소스와 웹 검색으로 큐레이션한 참고용 요약입니다.",{size:16,italics:true,color:"94A3B8"}));
}
renderBerkshire();
renderAITrends();
const doc=new Document({ ...(embedFontData?{fonts:[{name:FONT,data:embedFontData}]}:{}),
  styles:{ default:{document:{run:{font:FONT,size:22}}},
  paragraphStyles:[
    {id:"Heading1",name:"Heading 1",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:36,bold:true,font:FONT,color:"1E3A8A"},paragraph:{spacing:{before:360,after:200},outlineLevel:0}},
    {id:"Heading2",name:"Heading 2",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:28,bold:true,font:FONT,color:"1E40AF"},paragraph:{spacing:{before:240,after:140},outlineLevel:1}},
    {id:"Heading3",name:"Heading 3",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:24,bold:true,font:FONT,color:"334155"},paragraph:{spacing:{before:180,after:100},outlineLevel:2}}]},
  numbering:{config:[{reference:"bullets",levels:[{level:0,format:LevelFormat.BULLET,text:"•",alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:720,hanging:360}}}}]}]},
  sections:[{ properties:{page:{size:{width:12240,height:15840},margin:{top:1080,right:1080,bottom:1080,left:1080}}},
    headers:{default:new Header({children:[new Paragraph({alignment:AlignmentType.RIGHT,children:[new TextRun({text:`글로벌 금융시장 종합 시황 보고서 | ${reportDate}`,size:18,color:"64748B"})]})]})},
    footers:{default:new Footer({children:[new Paragraph({alignment:AlignmentType.CENTER,children:[new TextRun({text:"Page ",size:18,color:"64748B"}),new TextRun({children:[PageNumber.CURRENT],size:18,color:"64748B"}),new TextRun({text:" / ",size:18,color:"64748B"}),new TextRun({children:[PageNumber.TOTAL_PAGES],size:18,color:"64748B"}),new TextRun({text:"  |  v3.6.26",size:18,color:"64748B"})]})]})},
    children }] });
Packer.toBuffer(doc).then(buffer=>{ fs.mkdirSync(path.dirname(outPath),{recursive:true}); fs.writeFileSync(outPath,buffer);
  console.log("OK "+(buffer.length/1024).toFixed(1)+"KB tbl "+tableCount);
}).catch(e=>{ console.error("FAIL "+e.message); process.exit(1); });
// EOF — namoobi-market-report v3.6.26
