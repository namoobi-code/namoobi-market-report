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
// 표준키가 비었을 때만 복사(실데이터 보존), 데이터 전체 재귀. → 3.1.12 등 1·3·6개월 '-' 키드리프트 버그를 코드로 영구 차단.
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
  if (M.us_credit || M.hy_spread){ if(!M.hy_spread || M.hy_spread.current==null) warn.push("hy_spread.current 없음 → 3.1.1 HY 표/그래프 비거나 누락"); }
  if (!Array.isArray(M.korea_leading) || !M.korea_leading.length) warn.push("korea_leading 비어있음 → 3.1.5 경기선행지수 누락(통계청 KOSIS 수집 필요)");
  if (M.fx_markets){ const need=['usd_krw','eur_krw','jpy_krw','cny_krw','hkd_krw'];
    const miss=need.filter(k=>{try{return !fs.existsSync('charts/spark_'+k+'.png');}catch(e){return true;}});
    if(miss.length===need.length) warn.push("환율 추세 스파크라인 전무 → 5장 추세열 빈칸(nmr_series2.fx 시계열 수집 필요)"); }
  // (v3.6.33) ask-don't-degrade 차단 게이트 — 데이터는 있는데 차트가 없으면 조용히 "-"로 넘기지 말고 blocking 처리.
  //   --validate 가 issues 가 있으면 exit 1 → 워크플로(SKILL Phase 3.6)가 멈추고 사용자에게 어찌할지 묻는다.
  const needChart=(cond,file,msg)=>{ if(cond){ try{ if(!fs.existsSync(file)) issues.push("[차트누락] "+msg+" → "+file+" 없음 (데이터는 있으나 차트 미생성 — 사용자 확인 필요)"); }catch(e){ issues.push("[차트누락] "+msg);} } };
  needChart(M.korea_investors&&M.korea_investors.kospi, "charts/kospi_tech.png","3.2.1 코스피 일봉 캔들");
  needChart(M.korea_investors&&M.korea_investors.kosdaq, "charts/kosdaq_tech.png","3.2.1 코스닥 일봉 캔들");
  needChart(Array.isArray(M.korea_leading)&&M.korea_leading.length, "charts/leading_cycle.png","3.1.5 경기선행지수 차트");
  if (!M.oecd_cli || !Array.isArray((M.oecd_cli||{}).months) || !M.oecd_cli.months.length) warn.push("oecd_cli 비어있음 → 3.1.4 OECD 경기선행지수 누락(db/oecd_cli.json 확인)");
  needChart(M.oecd_cli&&Array.isArray(M.oecd_cli.months)&&M.oecd_cli.months.length, "charts/oecd_cli.png","3.1.4 OECD CLI 통합 차트");
  if(M.customs&&M.customs.series){ needChart(true,"charts/수출_전체_24개월.png","3.1.10 수출 전체 차트"); needChart(true,"charts/수출_반도체_24개월.png","3.1.10 수출 반도체 차트"); }
  needChart(M.hy_spread, "charts/hy_oas.png","3.1.1 HY 스프레드 차트");
  if(M.kr_liquidity) for(let i=1;i<=4;i++) needChart(true,"charts/krliq_"+i+".png","3.1.14 유동성·레버리지 차트 "+i);
  { const KB=M.krx_brief||{};  // (v3.54) 3.2.4/3.2.5 KRX 브리프 — 데이터 있으면 캡쳐 필수
    if(KB.krx&&KB.krx.pages) for(let i=1;i<=KB.krx.pages;i++) needChart(true,"charts/krx_brief_p"+i+".png","3.2.4 KRX 증시 Brief 캡쳐 p"+i);
    if(KB.short&&KB.short.pages) for(let i=1;i<=KB.short.pages;i++) needChart(true,"charts/short_brief_p"+i+".png","3.2.5 공매도 데일리 브리프 캡쳐 p"+i); }
  (M.semi_ai_stocks||[]).forEach((x,i)=>needChart(true,"charts/semi_s_"+i+".png","3.2.3 반도체 종목 추세("+((x&&x.name)||i)+")"));
  (M.semi_ai_etfs||[]).forEach((x,i)=>needChart(true,"charts/semi_e_"+i+".png","3.2.3 반도체 ETF 추세("+((x&&x.name)||i)+")"));
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
  if(w>=450){ const _k=744/w; w=Math.round(w*_k); hgt=Math.round(hgt*_k); }  // 풀폭 차트 좌우 꽉 채움(콘텐츠 744px·비율 유지)
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
function day1pct(m){ if(!m)return null; if(m.prev_pct!==undefined&&m.prev_pct!==null)return m.prev_pct; return (m["1d_pct"]!==undefined&&m["1d_pct"]!==null&&m["1d_pct"]!=="")?m["1d_pct"]:null; } // (req3 2026-07-05) prev_pct 없으면 1d_pct 폴백 — "-" 방지
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
// (v3.49) 3.1 그룹 소제목(①~④) — 번호 없는 소제목(방법 B): 개요 번호 체계 밖, 좌측 파란 바+연한 음영으로만 구분
function gh(text){ return new Paragraph({ spacing:{before:320,after:140}, shading:{fill:"EAF1F8",type:ShadingType.CLEAR},
  border:{left:{style:BorderStyle.SINGLE,size:24,color:"2E75B6",space:4}}, indent:{left:120},
  children:[new TextRun({text:String(text),bold:true,size:25,color:"1F4E79"})] }); }
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
const CONTENT_W=11160; // 페이지 12240 - 좌우 margin(540*2). 모든 표를 이 폭으로 꽉 채움(비율 유지)
function makeTable(cw,rows){ tableCount++; const t0=cw.reduce((a,b)=>a+b,0)||1; const k=CONTENT_W/t0; const cw2=cw.map(x=>Math.max(1,Math.round(x*k))); const total=cw2.reduce((a,b)=>a+b,0); return new Table({width:{size:total,type:WidthType.DXA},columnWidths:cw2,rows}); }
// ===== (v3.6.0) 추가 섹션 렌더러 — 데이터 없으면 자동 생략 =====
function simpleTable(w,header,body,opts){ opts=opts||{}; const leftCols=opts.left||[header.length-1];
  const rows=[header,...body].map((r,i)=>new TableRow({children:r.map((c,j)=>cell(c,{width:w[j],header:i===0,alt:i>0&&i%2===0,
    bold:(j===0||(opts.boldCols&&opts.boldCols.includes(j)))&&i>0, align:leftCols.includes(j)?AlignmentType.LEFT:AlignmentType.CENTER,
    color:(i>0&&opts.markCols&&opts.markCols.includes(j))?markColor(c):undefined}))}));
  children.push(makeTable(w,rows)); }
function renderBigtechEvents(){ const ev=data.news&&data.news.bigtech_events; if(!Array.isArray(ev)||!ev.length)return;
  children.push(h("2.3 빅테크 주요 이벤트 (신제품·신기술)",2));
  { const bw=[1300,2900,900,2680,1700];
    const brows=[new TableRow({children:["시기","이벤트","중요도","예상 영향","출처"].map((c,j)=>cell(c,{width:bw[j],header:true,align:AlignmentType.CENTER}))}),
      ...ev.map((e,k)=>{ const alt=(k+1)%2===0;
        const srcRuns=(e.source||e.source_url)?[linkRun(e.source||"링크",e.source_url,{size:18})]:[cellRun("-",{size:18})];
        return new TableRow({children:[cell(e.date??"-",{width:bw[0],alt,align:AlignmentType.CENTER}),
          cell(e.event??"-",{width:bw[1],alt,bold:true}),
          cell(e.importance??"-",{width:bw[2],alt,align:AlignmentType.CENTER}),
          cell(e.expected_impact??e.impact??"-",{width:bw[3],alt}),
          cell("",{width:bw[4],alt,runs:srcRuns})]}); })];
    children.push(makeTable(bw,brows)); }
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
  { children.push(h("3.2.3 순환매 대비 테마별 현황 (대표 ETF·추세·수익률)",3));
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
    const THEME_ORDER=["반도체/AI","전력기기","조선","방산","원자력","증권","로봇","우주","건설","건설기계","항공","정유","K푸드","K화장품"];  // (v3.50) 건설 + (v3.50.1) 건설기계·항공·정유 + (v3.63) K푸드·K화장품 추가
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
    const fmtAUM=(v)=>{ if(v==null||v==="")return "- (시총/AUM 미확인)"; if(/[조억원만]/.test(String(v)))return String(v);
      const n=(typeof v==="number")?v:parseFloat(String(v).replace(/[^0-9.]/g,"")); if(!isFinite(n)||n<=0)return String(v);
      if(n>=10000){const jo=Math.floor(n/10000),eok=Math.round(n%10000); return eok?(jo.toLocaleString()+"조 "+eok.toLocaleString()+"억원"):(jo.toLocaleString()+"조원");}
      return Math.round(n).toLocaleString()+"억원"; };
    // (v3.64) 네이버 보강 — 당일 수급·목표주가 컨센서스·외인소진율.
    //   Yahoo 는 종가·수익률만 준다. 한국 종목에서 '오늘 누가 사고 팔았나'와
    //   '애널리스트 목표주가'가 빠져 있었다(KRX OPEN API 는 T+1 이라 오늘 수급을 못 준다).
    const _kq=(v)=>{ const n=parseFloat(String(v||"").replace(/[+,]/g,"")); if(!isFinite(n))return null;
      const a=Math.abs(n); const s2=(n>0?"+":"−");
      return s2+(a>=10000?(a/10000).toFixed(1)+"만주":Math.round(a).toLocaleString()+"주"); };
    const semiDesc=(x)=>{ const runs=[ new TextRun({text:(x.name||"-")+"  ",bold:true,size:20}),
      new TextRun({text:("시총/AUM: "+fmtAUM(x.aum)),size:16,color:"475569"}),
      new TextRun({text:(x.note?("   — "+x.note):""),size:16,color:"64748B"}) ];
      const f=x.flows, c=x.consensus;
      if(f){ const F=_kq(f.foreign),I=_kq(f.inst),P=_kq(f.indiv);
        runs.push(new TextRun({text:"수급("+String(f.date||"").replace(/(\d{4})(\d{2})(\d{2})/,"$2/$3")+")  ",size:14,color:"94A3B8",break:1}));
        if(F) runs.push(new TextRun({text:"외국인 "+F+"   ",size:14,bold:true,color:/−/.test(F)?"2563EB":"DC2626"}));
        if(I) runs.push(new TextRun({text:"기관 "+I+"   ",size:14,bold:true,color:/−/.test(I)?"2563EB":"DC2626"}));
        if(P) runs.push(new TextRun({text:"개인 "+P,size:14,bold:true,color:/−/.test(P)?"2563EB":"DC2626"}));
        if(x.foreign_rate!=null) runs.push(new TextRun({text:"   외인소진율 "+x.foreign_rate+"%",size:14,color:"64748B"})); }
      if(c&&c.target){ runs.push(new TextRun({text:"목표주가 "+Math.round(c.target).toLocaleString()+"원",size:14,bold:true,color:"7C3AED",break:1}));
        if(c.upside_pct!=null) runs.push(new TextRun({text:"  (상승여력 "+(c.upside_pct>0?"+":"")+c.upside_pct+"%)",size:14,color:c.upside_pct>0?"DC2626":"2563EB"}));
        runs.push(new TextRun({text:"  · 투자의견 "+(c.recomm||"-")+" · 기준 "+(c.asof||"-"),size:13,color:"94A3B8"}));
        if(x.fwd_per!=null) runs.push(new TextRun({text:"  · 추정PER "+x.fwd_per+"배",size:13,color:"64748B"})); }
      return runs; };
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
  // (v3.54) 3.2.4 KRX 증시 Brief / 3.2.5 공매도 데일리 브리프 — open.krx.co.kr 종합시황 최신 PDF 페이지 캡쳐 삽입.
  //   데이터=markets.krx_brief (fetch_krx_brief.py — 회차 att_seq 마커 DB화, 동일 회차면 저장본 재사용).
  //   항목 데이터 없으면 해당 소섹션 자동 생략(비차단). 캡쳐 PNG 는 charts/krx_brief_p*.png / short_brief_p*.png.
  { const kb=m.krx_brief||{};
    const kbBlk=(sec,ti,d,prefix)=>{ if(!d||!d.pages)return;
      children.push(h(sec+" "+ti,3));
      children.push(p("업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지 (회차 마커=게시글 att_seq · 원문 PDF 페이지 캡쳐)",{size:16,color:"94A3B8"}));
      const _svKB=((data.markets||{}).server_notes||{}).krx_brief; if(_svKB) children.push(p(_svKB,{size:15,italics:true,color:"7C3AED"}));
      children.push(p((d.title||ti)+"   등록: "+(d.date||"-")+(d.stale_note?("   ⚠ "+d.stale_note):""),{bold:true,color:"1E40AF",before:80}));
      let shown=0;
      for(let i=1;i<=d.pages;i++){ const img=imagePara("charts/"+prefix+"_p"+i+".png",700,990); if(img){children.push(img);shown++;} }
      if(!shown)children.push(p("(캡쳐 이미지 누락 — fetch_krx_brief.py 재실행 필요)",{italics:true,color:"B45309",size:16}));
      children.push(p("출처: 한국거래소 "+(kb.source||"KRX 시장 > 시장동향 > 종합시황")+" ("+(kb.source_url||"https://open.krx.co.kr/contents/MKD/01/0101/01010000/MKD01010000.jsp")+")",{size:15,color:"94A3B8"}));
      children.push(p("")); };
    kbBlk("3.2.4","KRX 증시 Brief (KRX)",kb.krx,"krx_brief");
    kbBlk("3.2.5","공매도 데일리 브리프 (KRX)",kb.short,"short_brief");
  }
 }
// (v3.12.0→v3.49) 3.1.9 메모리+HBM 대시보드 — 3.1(매크로 대시보드)로 이동. renderMacroIndicators 에서 호출.
function renderHBM(){ const m=data.markets||{}; const hbm=(m.hbm)||{};
  children.push(h("3.1.9 반도체 주가 체크용 메모리+HBM 지표",3));
  const _svMEM=((data.markets||{}).server_notes||{}).memory; if(_svMEM) children.push(p(_svMEM,{size:15,italics:true,color:"7C3AED"}));
  const img=imagePara((hbm.chart)||"charts/hbm_dashboard.png",720,980);
  const mem=(m.memory&&m.memory.tables)?m.memory:null;
  if(img){ children.push(p("① DRAM 현물(스팟) / ② DRAM 고정거래(계약) / ③ NAND 현물 / ④ NAND 고정거래 / ⑤ 스팟-계약 갭 / ⑥ HBM 업체별 점유율 / ⑦ HBM ASP 추이 / ⑧ HBM 시장규모·수요 증가율(연간, Yole·추정) / ⑨ HBM:DDR5 GB당 단가 격차(환산 추정) / ⑩ 선행지표 1년 성과 / ⑪ 메모리/GPU 상대강도 — 11개 패널. 가격·주가=공개 소스 실측, ⑦⑧⑨=공개 추정치 환산.",{italics:true,color:"64748B"})); children.push(img);
    children.push(p("기준: "+((mem&&mem.asof)||hbm.asof||"최신")+" · 자료: TrendForce 공개 가격표(가격 21종) + Silicon Analysts 공개 API(HBM 점유율·ASP) + Yahoo Finance(선행지표 6종)",{size:15,color:"94A3B8"}));
    children.push(p("업데이트: fetch_memory.py 가 매 실행 수집 + 서버 daily cron(08:30 KST) 이 매일 누적 → db/memory.json(스냅샷) · db/series_mem_*(시계열). 누적이 2일 이상이면 막대가 추세선으로 자동 전환된다. ※ TrendForce 과거 시계열·DXI 지수는 유료 회원 전용이라 과거를 사지 않고 오늘부터 직접 쌓는다.",{size:13,italics:true,color:"94A3B8"}));
    if(hbm.current_anchors) children.push(p("현재 현물 앵커("+(hbm.asof||"")+"): "+hbm.current_anchors,{size:13,color:"475569"}));
    if(hbm.series_note) children.push(p("※ "+hbm.series_note,{size:12,italics:true,color:"94A3B8"})); }
  // (v3.59) 스팟-계약 갭 — 계약가 인상 압력 선행지표. db/memory.json 의 현물·계약 표를 규격끼리 매칭.
  if(mem){
    const g=(k)=>{const t=mem.tables[k]||{}; const o={}; (t.rows||[]).forEach(r=>{o[r.item]=r.avg;}); return o;};
    const ds=g("dram_spot"), dc=g("dram_contract"), ns=g("nand_spot"), nc=g("nand_contract");
    const PAIRS=[["DDR4 8Gb","DDR4 8Gb (1Gx8) 3200","DDR4 8Gb 1Gx8",ds,dc],
                 ["DDR4 16Gb","DDR4 16Gb (2Gx8) 3200","DDR4 16Gb 2Gx8",ds,dc],
                 ["NAND 64Gb","MLC 64Gb 8GBx8","NAND 64Gb 8Gx8 MLC",ns,nc],
                 ["NAND 32Gb","MLC 32Gb 4GBx8","NAND 32Gb 4Gx8 MLC",ns,nc]];
    const gr=[];
    PAIRS.forEach(([lab,si,ci,S,K])=>{ const sp=S[si], ct=K[ci];
      if(sp!=null&&ct){ gr.push([lab,sp,ct,(sp/ct-1)*100]); } });
    if(gr.length){
      children.push(p("■ 스팟-계약 갭 (계약가 인상 압력 선행지표)",{bold:true,color:"1E40AF",before:100,size:20}));
      children.push(p("현물가가 계약가를 크게 상회하면 다음 계약 협상에서 인상 압력으로 작용한다 — 메모리 3사 실적의 선행지표.",{size:14,italics:true,color:"64748B"}));
      const gw=[2000,1900,1900,1500,2440];
      const grows=[hdrRow(["규격","현물(스팟)","계약","갭","해석"],gw)];
      gr.forEach(([lab,sp,ct,gp],i)=>{ const a=i%2===1; const pos=gp>0;
        grows.push(new TableRow({children:[
          cell(lab,{width:gw[0],alt:a,bold:true}),
          cell(sp.toFixed(2),{width:gw[1],alt:a,size:13,align:AlignmentType.RIGHT}),
          cell(ct.toFixed(2),{width:gw[2],alt:a,size:13,align:AlignmentType.RIGHT}),
          cell((pos?"+":"")+gp.toFixed(1)+"%",{width:gw[3],alt:a,size:13,bold:true,align:AlignmentType.RIGHT,color:pos?"DC2626":"2563EB"}),
          cell(pos?("현물이 계약가 "+gp.toFixed(0)+"% 상회 → 인상 압력"):("현물이 계약가 "+Math.abs(gp).toFixed(0)+"% 하회 → 압력 없음"),
               {width:gw[4],alt:a,size:12,color:"64748B"})]})); });
      children.push(makeTable(gw,grows));
      // (req11 2026-07-12) 기준 날짜·출처 명시
      { const _ta=(k)=>((mem.tables[k]||{}).asof)||((mem.tables[k]||{}).last_update)||null;
        const _sp_as=_ta("dram_spot")||mem.asof||"-", _ct_as=_ta("dram_contract")||"최근 고정거래 협상월";
        children.push(p("기준: 현물 "+_sp_as+" (TrendForce 스팟 세션) · 계약 "+_ct_as+" (고정거래가, 월 1회 갱신) · 출처: TrendForce 공개 가격표 · 갭 = (현물평균 − 계약평균) ÷ 계약평균",{size:13,italics:true,color:"94A3B8"})); }
    }
  }
  // (v3.60) 선행지표 — 전부 일별 갱신. 메모리 가격보다 먼저 움직이는 시장 신호.
  const LD=(mem&&mem.leading)?mem.leading:null;
  if(LD&&Object.keys(LD).length){
    children.push(p("■ 선행지표 — 메모리 가격보다 먼저 움직이는 신호 (전 항목 매일 갱신)",{bold:true,color:"1E40AF",before:100,size:20}));
    const lw=[2100,1350,1150,1150,4410];
    const lrows=[hdrRow(["지표","현재값","1년","1개월","왜 선행지표인가"],lw)];
    const _pc=(v)=>(v==null)?"-":((v>0?"+":"")+v.toFixed(1)+"%");
    const _cl=(v)=>(v==null)?"64748B":(v>0?"DC2626":"2563EB");
    let i=0;
    ["SOX","NVDA","AMD","TSM","KOSPI","MU"].forEach(k=>{ const o=LD[k]; if(!o||o.price==null)return;
      const a=(i++)%2===1;
      lrows.push(new TableRow({children:[
        cell(o.label||k,{width:lw[0],alt:a,bold:true,size:14}),
        cell(Number(o.price).toLocaleString(undefined,{maximumFractionDigits:2}),{width:lw[1],alt:a,size:13,align:AlignmentType.RIGHT}),
        cell(_pc(o.chg_1y_pct),{width:lw[2],alt:a,size:13,bold:true,align:AlignmentType.RIGHT,color:_cl(o.chg_1y_pct)}),
        cell(_pc(o.chg_1m_pct),{width:lw[3],alt:a,size:13,align:AlignmentType.RIGHT,color:_cl(o.chg_1m_pct)}),
        cell(o.why||"",{width:lw[4],alt:a,size:12,color:"64748B"})]})); });
    if(i) children.push(makeTable(lw,lrows));
    const rs=LD.MEM_VS_GPU;
    if(rs&&rs.value!=null){
      const up=rs.value>1;
      children.push(p("★ 메모리 / GPU 상대강도 = "+rs.value+"배  ("+(rs.signal||"")+")",
        {bold:true,size:19,color:up?"B45309":"2563EB",before:80}));
      children.push(p("마이크론이 엔비디아보다 1년간 "+rs.value+"배 더 올랐다. HBM 을 사는 쪽(엔비디아)보다 파는 쪽(마이크론)이 압도적으로 오른다는 것은, 가치가 수요처에서 공급자로 이동했다는 뜻 — 메모리가 협상력을 쥐었고 공급부족이 극심하다는 신호다. "+
        "이 비율이 꺾이기 시작하면 공급부족 완화 = 사이클 고점 경계 신호로 읽는다.",{size:14,color:"475569"}));
    }
    children.push(p("자료: Yahoo Finance 무인증 chart API — fetch_memory.py 가 매 실행 자동 수집, db/series_mem_leading_px · series_mem_mem_vs_gpu 로 매일 누적.",{size:12,italics:true,color:"94A3B8"}));
  }
  const ey=Array.isArray(hbm.eps_yearly)?hbm.eps_yearly:null;
  if(ey&&ey.length){ children.push(p("■ HBM 3사 연도별 EPS · PER 예상치 (실측·컨센서스)",{bold:true,color:"1E40AF",before:100,size:20}));
    const w=[1500,1760,1760,1760,1760,1200]; const rows=[hdrRow(["종목","2025(실적)","2026(E)","2027(E)","2028(E)","통화"],w)];
    const _fnum=(x)=>(typeof x==="number")?x.toLocaleString():x;
    // (v3.65) 네이버 연도별(실적/컨센서스)로 갱신된 셀은 출처를 표시한다 — 어느 값이 검증된 것인지 보이게.
    const cc=(e,pp,src)=>{ const he=(e!=null&&e!==""), hp=(pp!=null&&pp!=="");
      if(!he&&!hp)return "- 컨센서스 미공개";
      const base=(he?("EPS "+_fnum(e)):"EPS -")+(hp?(" · PER "+pp+"x"):" · PER -");
      return base+(src?("\n["+src+"]"):""); };
    ey.forEach((o,i)=>{ const a=i%2===1; rows.push(new TableRow({children:[
      cell(o.name||"-",{width:w[0],alt:a,bold:true}),
      cell(cc(o.y2025_eps,o.y2025_per,o.y2025_src),{width:w[1],alt:a,size:13,align:AlignmentType.CENTER}),
      cell(cc(o.y2026_eps,o.y2026_per,o.y2026_src),{width:w[2],alt:a,size:13,align:AlignmentType.CENTER}),
      cell(cc(o.y2027_eps,o.y2027_per,o.y2027_src),{width:w[3],alt:a,size:13,align:AlignmentType.CENTER}),
      cell(cc(o.y2028_eps,o.y2028_per,o.y2028_src),{width:w[4],alt:a,size:13,align:AlignmentType.CENTER}),
      cell(o.currency||"",{width:w[5],alt:a,size:13,align:AlignmentType.CENTER})]})); });
    children.push(makeTable(w,rows));
    // (req13 2026-07-12) 대시보드 ⑩과 단일 소스(db/hbm_eps.json) — EPS=컨센서스(변동 시 갱신) · PER=최신 종가÷EPS 매일 재계산
    children.push(p("EPS 출처: [네이버 실적]·[네이버 컨센서스] = 네이버 기업실적분석에서 매일 자동 갱신(연도키·isConsensus 명시라 매핑 확실). 출처는 네이버 PC 종목분석(FnGuide) — 2025 실적 + 2026~2028 컨센서스 3년치를 매일 자동 갱신한다. 표기 없는 셀은 기존 소스(MCP/DB). PER = 최신 종가 ÷ EPS 매일 재계산. "+(hbm.eps_note||""),{size:13,italics:true,color:"94A3B8"}));
    // (v3.64) 네이버 당일 컨센서스 병기 — 위 표는 DB carry-forward 라 컨센서스 상향이 반영 안 될 수 있다.
    //   2026-07-13 실측: SK하이닉스 DB 2026 EPS 110,559(PER 16.7배) vs 네이버 당일 318,735(PER 5.79배) — 3배 괴리.
    //   PER 16.7배와 5.8배는 투자판단이 완전히 다르므로 정본(당일값)을 나란히 보여주고 괴리를 경고한다.
    const _lv=ey.filter(o=>o&&o.consensus_live);
    if(_lv.length){
      children.push(p("■ 당일 컨센서스 (네이버 — 국내 증권사 집계, 매일 갱신)",{bold:true,color:"7C3AED",before:100,size:19}));
      const lw2=[1700,2000,1400,2000,3060];
      const lr=[hdrRow(["종목","추정EPS (당해년도)","추정PER","목표주가","위 표(DB 추정치)와의 괴리"],lw2)];
      _lv.forEach((o,i)=>{ const a=i%2===1; const c=o.consensus_live||{}; const gap=o.consensus_gap_pct;
        lr.push(new TableRow({children:[
          cell(o.name||"-",{width:lw2[0],alt:a,bold:true,size:14}),
          cell(c.fwd_eps!=null?Math.round(c.fwd_eps).toLocaleString():"-",{width:lw2[1],alt:a,size:13,align:AlignmentType.RIGHT}),
          cell(c.fwd_per!=null?(c.fwd_per+"배"):"-",{width:lw2[2],alt:a,size:13,bold:true,align:AlignmentType.RIGHT,color:"7C3AED"}),
          cell(c.target!=null?(Math.round(c.target).toLocaleString()+"원"):"-",{width:lw2[3],alt:a,size:13,align:AlignmentType.RIGHT}),
          cell(gap!=null?("⚠️ "+gap+"% 어긋남 — DB 추정치 재조사 필요"):"정합 (30% 이내)",
               {width:lw2[4],alt:a,size:12,bold:gap!=null,color:gap!=null?"DC2626":"64748B"})]})); });
      children.push(makeTable(lw2,lr));
      children.push(p("추정EPS = 당해년도 국내 증권사 컨센서스 집계(네이버, 매일 갱신). 위의 연도별 표는 DB carry-forward 값이라 컨센서스가 대폭 상향되면 낡을 수 있다 — 괴리가 크면 이 표의 당일값을 정본으로 본다. Micron 은 국내 컨센서스 미제공(MCP/DB 사용).",{size:13,italics:true,color:"94A3B8"}));
    }
     }
  // (req3) HBM 3사 연도별 매출·영업이익·영업이익률 (삼성전자 전사+DS부문 병기)
  const fy=Array.isArray(hbm.fin_yearly)?hbm.fin_yearly:null;
  if(fy&&fy.length){ children.push(p("■ HBM 3사 연도별 매출 · 영업이익 · 영업이익률 (실측·컨센서스)",{bold:true,color:"1E40AF",before:100,size:20}));
    const wf=[2100,1740,1740,1740,1740,1100]; const rowsF=[hdrRow(["종목","2024(실적)","2025(실적)","2026(E)","2027(E)","통화"],wf)];
    const _ff=(x)=>(x==null||x==="")?null:((typeof x==="number")?x.toLocaleString():String(x));
    const fcf=(rev,op,opm)=>{ const hr=(rev!=null&&rev!==""),ho=(op!=null&&op!==""),hm=(opm!=null&&opm!=="");
      if(!hr&&!ho&&!hm)return "- 미공개";
      return "매출 "+(hr?_ff(rev):"-")+" · 영익 "+(ho?_ff(op):"-")+" · OPM "+(hm?(_ff(opm)+"%"):"-"); };
    fy.forEach((o,i)=>{ const a=i%2===1; rowsF.push(new TableRow({children:[
      cell(o.name||"-",{width:wf[0],alt:a,bold:true,size:13}),
      cell(fcf(o.y2024_rev,o.y2024_op,o.y2024_opm),{width:wf[1],alt:a,size:12,align:AlignmentType.CENTER}),
      cell(fcf(o.y2025_rev,o.y2025_op,o.y2025_opm),{width:wf[2],alt:a,size:12,align:AlignmentType.CENTER}),
      cell(fcf(o.y2026_rev,o.y2026_op,o.y2026_opm),{width:wf[3],alt:a,size:12,align:AlignmentType.CENTER}),
      cell(fcf(o.y2027_rev,o.y2027_op,o.y2027_opm),{width:wf[4],alt:a,size:12,align:AlignmentType.CENTER}),
      cell(o.currency||"",{width:wf[5],alt:a,size:12,align:AlignmentType.CENTER})]})); });
    children.push(makeTable(wf,rowsF));
    children.push(p("단위: 매출·영업이익=조원(KRW)/십억달러(USD), OPM=영업이익률(%). 삼성전자는 전사·반도체(DS)부문 병기. 실적=각사 IR, (E)=애널리스트 컨센서스.",{size:13,color:"94A3B8"})); }
  // (v3.60) 지표 사전 — 각 항목의 의미 / 해석 방법 / 실제 변동 주기.
  //   매일 변하지 않는 값은 실제 주기를 명시한다(계약가=월 1회 등). 계약가 추세선이 계단 모양인 건 정상.
  const MT=(mem&&mem.meta)?mem.meta:null;
  if(MT&&Object.keys(MT).length){
    children.push(p("■ 지표 사전 — 의미 · 해석 방법 · 변동 주기",{bold:true,color:"1E40AF",before:120,size:20}));
    children.push(p("※ '변동 주기'는 수집 주기가 아니라 값이 실제로 바뀌는 주기다. 계약가처럼 월 1회만 바뀌는 값은 추세선이 계단 모양으로 그려지는 것이 정상이다.",{size:13,italics:true,color:"64748B"}));
    const mw=[1850,1700,3300,3310];
    const mrows=[hdrRow(["지표","변동 주기","의미","해석 방법"],mw)];
    let j=0;
    Object.keys(MT).forEach(k=>{ const o=MT[k]||{}; if(!o.label)return; const a=(j++)%2===1;
      const daily=/매일/.test(String(o.cadence||""));
      mrows.push(new TableRow({children:[
        cell(o.label,{width:mw[0],alt:a,bold:true,size:13,color:(o.dbviz===true?"DC2626":undefined)}),
        cell(o.cadence||"-",{width:mw[1],alt:a,size:12,bold:true,color:daily?"15803D":"B45309"}),
        cell(o.meaning||"",{width:mw[2],alt:a,size:12,color:"334155"}),
        cell(o.howto||"",{width:mw[3],alt:a,size:12,color:"64748B"})]})); });
    if(j){ children.push(makeTable(mw,mrows));
      children.push(p("빨간 지표명=DB 누적·3.1.9 그래프/표로 업데이트 중인 지표. 녹색=매일 갱신 · 주황=주/월/분기/연 단위 갱신. 출처: TrendForce 공개 가격표 · Silicon Analysts 공개 API · Yahoo Finance · 관세청 오픈API.",{size:12,italics:true,color:"94A3B8"})); }
  }
  children.push(p("")); }

// (v3.45.0) 3.1.11 반도체 사이클 → 코스피 점검판 — DB화(db/semi_cycle.json), 매 실행 3대 신호 변동체크·미변동 재사용. 차트 없음(비차단·데이터 없으면 자동 생략).
function renderSemiCycle(){ const m=data.markets||{}; const sc=m.semi_cycle;
  if(!sc||typeof sc!=="object"||(!sc.headline&&!(Array.isArray(sc.signals)&&sc.signals.length)))return;
  children.push(h("3.1.11 반도체 사이클 → 코스피 점검판",3));
  children.push(p("업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지",{size:15,italics:true,color:"94A3B8"}));
  if(sc.phase) children.push(p("현재 국면: "+sc.phase+(sc.phase_peak?("  ·  "+sc.phase_peak):""),{bold:true,size:20,color:"1E40AF",before:60}));
  // (req6 2026-07-05·v2) 대시보드 레이아웃 — 단계 바 / 타일 1행4칸 / 점검 카드 2×2 그리드 (첨부 대시보드 스타일)
  const _mcell=(paras,w,fill)=>new TableCell({borders,width:{size:w,type:WidthType.DXA},
    shading:fill?{fill,type:ShadingType.CLEAR,color:"auto"}:undefined,
    margins:{top:110,bottom:110,left:160,right:160},children:paras});
  const stg=sc.stages;
  if(stg&&Array.isArray(stg.list)&&stg.list.length){
    const w=Math.floor(10160/stg.list.length); const sw2=stg.list.map(()=>w);
    const row=new TableRow({children:stg.list.map(s=>{const on=(s===stg.current);
      return _mcell([new Paragraph({alignment:AlignmentType.CENTER,children:[
        new TextRun({text:on?(s+" (현재)"):s,bold:on,size:on?19:15,color:on?"15803D":"94A3B8"})]})],w,on?"DCFCE7":"F8FAFC");})});
    children.push(makeTable(sw2,[row]));
    if(stg.note)children.push(p(stg.note,{size:15,italics:true,color:"64748B"})); }
  const tl=Array.isArray(sc.tiles)?sc.tiles:[];
  if(tl.length){
    const w=Math.floor(10160/tl.length); const tw2=tl.map(()=>w);
    const row=new TableRow({children:tl.map(t=>_mcell([
      new Paragraph({children:[new TextRun({text:String(t.lab||""),size:15,color:"64748B"})]}),
      new Paragraph({spacing:{before:30,after:20},children:[new TextRun({text:String(t.num||"-"),bold:true,size:30,color:"0F172A"})]}),
      new Paragraph({children:[new TextRun({text:String(t.sub||""),size:13,color:"94A3B8"})]})],w,"F8FAFC"))});
    children.push(makeTable(tw2,[row])); children.push(p("",{size:6})); }
  const pn=Array.isArray(sc.panels)?sc.panels:[];
  if(pn.length){
    const CW2=5080; const mkCard=cd=>{ if(!cd) return _mcell([new Paragraph({children:[]})],CW2);
      const paras=[new Paragraph({spacing:{after:60},children:[new TextRun({text:String(cd.title||""),bold:true,size:18,color:"1E40AF"})]})];
      (Array.isArray(cd.rows)?cd.rows:[]).forEach(rv=>{
        const k=Array.isArray(rv)?rv[0]:(rv&&rv.k); const v=Array.isArray(rv)?rv[1]:(rv&&rv.v);
        paras.push(new Paragraph({spacing:{before:20,after:20},children:[
          new TextRun({text:String(k||"")+"   ",bold:true,size:14,color:"64748B"}),
          new TextRun({text:String(v||""),size:15,color:"1E293B"})]})); });
      if(Array.isArray(cd.badges)&&cd.badges.length)
        paras.push(new Paragraph({spacing:{before:50},children:cd.badges.map((bg,i)=>
          new TextRun({text:(i?"   ":"")+String(bg),bold:true,size:14,color:/▼|하강|압박/.test(String(bg))?"B91C1C":"15803D"}))}));
      return _mcell(paras,CW2); };
    for(let i=0;i<pn.length;i+=2){
      children.push(makeTable([CW2,CW2],[new TableRow({children:[mkCard(pn[i]),mkCard(pn[i+1])]})]));
      children.push(p("",{size:6})); } }
  if(sc.headline){ children.push(p("■ 핵심 한 줄",{bold:true,size:20,color:"1E40AF",before:100}));
    children.push(p(sc.headline,{size:18})); }
  const rp=Array.isArray(sc.read_panel)?sc.read_panel:(sc.read_panel?[sc.read_panel]:[]);
  if(rp.length){ children.push(p("■ 읽는 방법",{bold:true,size:20,color:"1E40AF",before:100}));
    rp.forEach(x=>children.push(p("• "+x,{size:17,color:"334155"}))); }
  if(sc.kospi_weight) children.push(p("※ 코스피 쏠림: "+sc.kospi_weight,{size:15,italics:true,color:"475569"}));
  const wn=Array.isArray(sc.warning_now)?sc.warning_now:[];
  if(wn.length){ children.push(p("■ 지금 봐야 할 조기 경보 신호",{bold:true,size:20,color:"B91C1C",before:100}));
    wn.forEach(x=>children.push(p("• "+x,{size:17,bold:true,color:"B45309"}))); }
  const sg=Array.isArray(sc.signals)?sc.signals:[];
  if(sg.length){ children.push(p("■ 메모리 사이클 조기경보 점검",{bold:true,size:20,color:"1E40AF",before:120}));
    const sw=[2600,1900,1150,2560,2950];
    const st=(s)=>{ const t=String(s||""); if(/경보|위험|하강|red/i.test(t))return "B91C1C"; if(/주의|둔화|yellow|amber/i.test(t))return "B45309"; return "15803D"; };
    const rows=[hdrRow(["지표","현재값","판정","경보 임계선","비고"],sw)];
    sg.forEach((o,i)=>{ const a=i%2===1; rows.push(new TableRow({children:[
      cell(o.name||"-",{width:sw[0],alt:a,bold:true,size:15}),
      cell(o.value||"-",{width:sw[1],alt:a,size:15,align:AlignmentType.CENTER}),
      cell(o.status||"-",{width:sw[2],alt:a,size:15,align:AlignmentType.CENTER,color:st(o.status)}),
      cell(o.threshold||"-",{width:sw[3],alt:a,size:14}),
      cell(o.note||"-",{width:sw[4],alt:a,size:14})]})); });
    children.push(makeTable(sw,rows)); }
  // (req6) 3대 조기경보 미니차트(재고주수·계약가 QoQ·CAPEX YoY) + 캡션
  { const scChart=imagePara(sc.chart||"charts/semi_cycle_signals.png",680,175);
    if(scChart){ children.push(scChart);
      const S3=(sc.series||{});
      [["① 재고주수",(S3.inventory||{}).cap],["② 계약가 QoQ",(S3.price_qoq||{}).cap],["③ CAPEX YoY",(S3.capex_yoy||{}).cap]].forEach(([t,c])=>{
        if(c)children.push(p(t+" — "+c,{size:14,color:"64748B"})); }); } }
  if(sc.signal_summary) children.push(p("→ "+sc.signal_summary,{size:17,bold:true,color:"1E40AF",before:60}));
  if(sc.read_monitor){ children.push(p("■ 읽는 방법 (조기경보 점검)",{bold:true,size:20,color:"1E40AF",before:100}));
    children.push(p(sc.read_monitor,{size:17,color:"334155"})); }
  const src=Array.isArray(sc.sources)?sc.sources:[];
  if(src.length){ const runs=[new TextRun({text:"자료: ",size:14,color:"94A3B8"})];
    src.forEach((s,i)=>{ if(i)runs.push(new TextRun({text:" · ",size:14,color:"94A3B8"}));
      runs.push((HAS_LINK&&s&&s.url)?new ExternalHyperlink({link:String(s.url),children:[new TextRun({text:String(s.label||s.url),size:14,color:"1D4ED8",underline:{}})]}):new TextRun({text:String((s&&(s.label||s.url))||""),size:14,color:"64748B"})); });
    children.push(new Paragraph({spacing:{before:80,after:80},children:runs})); }
  children.push(p("기준: "+(sc.asof||"최신")+" · 비실시간 추정 — 자료: TrendForce/DRAMeXchange·각사 IR·시장조사(Counterpoint 등)·AI Research. 확인처: 계약가·현물가·DXI·재고주수=TrendForce, 실적·CAPEX=삼성·SK하이닉스 IR(마이크론 분기 선행).",{size:13,italics:true,color:"94A3B8"}));
  children.push(p("")); }

// (v3.31.0→v3.43.1) 3.1.5 경기선행지수(국내 순환변동치) — 3.1.4 OECD CLI 다음(확인 신호).
function renderKoreaLeading(){ const m=data.markets||{};
  if(Array.isArray(m.korea_leading)&&m.korea_leading.length){ children.push(h("3.1.5 경기선행지수 순환변동치 (주가 동행 선행지표)",3));
    const _svLD=((data.markets||{}).server_notes||{}).leading; if(_svLD) children.push(p(_svLD,{size:15,italics:true,color:"7C3AED"}));
    children.push(fsLink("출처 · 국가데이터처 e-나라지표 「산업활동동향」 선행종합지수 순환변동치(2020=100)", (m.korea_leading_source||"https://www.index.go.kr/unity/potal/main/EachDtlPageDetail.do?idx_cd=1057")));
    children.push(p("경기선행지수 순환변동치와 주식(특히 KOSPI)은 상당한 정비례 상관관계를 가지며, 선행지수 순환변동치가 주가를 약 2개월 정도 선행하여 움직이는 특징이 있습니다.",{italics:true,color:"64748B"}));
    children.push(p("• 100 이상 = 경기 확장 전망    • 100 이하 = 경기 침체 전망",{bold:true,size:18,color:"475569"}));
    children.push(p("• 구성항목: 재고순환지표(제조업), 기계류내수출하지수, 건설수주액(실질), 소비자기대지수, 구인구직비율, 장단기금리차, 코스피지수, 수출입물가비율, 순상품교역조건 등",{size:16,color:"475569"}));
    children.push(p("• 주식 선행 관점: OECD CLI(3.1.4)는 더 앞단의 \u201c방향 신호\u201d, 통계청 선행종합지수 순환변동치는 그 신호를 국내 경기 데이터로 한 번 더 다듬은 \u201c확인 신호\u201d로 함께 본다.",{size:16,color:"475569"}));
    children.push(p("업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지",{size:15,italics:true,color:"94A3B8"}));
    simpleTable([2200,2200,1800,3180],["시점","순환변동치","전월차","비고"],m.korea_leading.map(x=>[x.period??"-",(x.value!=null?String(x.value):"-"),x.mom??"-",x.note??"-"]),{left:[3]});
    { const lc=imagePara(m.korea_leading_chart||"charts/leading_cycle.png",648,243); if(lc){ children.push(lc); children.push(p("선행종합지수 순환변동치 장기 추이 (월별, 기준선 100 · 100 상회=확장 국면) · 출처: 국가데이터처 / INDEXerGO",{size:15,color:"94A3B8"})); } }
    if(m.korea_leading_comment)children.push(p(m.korea_leading_comment)); children.push(p("")); } }
// (v3.43.1) 3.1.4 OECD 경기선행지수(CLI) — 통합 DB(db/oecd_cli.json), KOSIS 자료갱신일 변동 시에만 재수집·차트 재생성. (3.1.5 국내 순환변동치보다 앞 — 방향 신호→확인 신호 순)
function renderOecdCli(){ const m=data.markets||{}; const oc=m.oecd_cli;
  if(!oc||!Array.isArray(oc.months)||!oc.months.length)return;
  children.push(h("3.1.4 OECD 경기선행지수 (OECD Composite Leading Indicators, CLI)",3));
  children.push(p("업데이트:매 실행 변동 여부만 체크(KOSIS 자료갱신일 기준), 변동없으면 기존 자료 유지",{size:15,italics:true,color:"94A3B8"}));
  const nC=Object.keys(oc.series||{}).length;
  const img=imagePara(oc.chart||"charts/oecd_cli.png",700,394);
  if(img){ children.push(img);
    children.push(p("전 국가 통합 그래프 — X축: 월별 총기간("+oc.months[0]+" ~ "+oc.months[oc.months.length-1]+"), Y축: 지수(진폭조정) · "+nC+"개국 · 기준선 100 · 대한민국 굵은 선 · 출처: "+(oc.source||"OECD · KOSIS(DT_2STES045)")+((oc.data_updated||oc.data_downloaded)?(" · 자료갱신일 "+(oc.data_updated||oc.data_downloaded)):""),{size:15,color:"94A3B8"})); }
  children.push(p("OECD 경기선행지수(CLI)는 경제의 방향성을 미리 예측하는 지표로, 경제활동의 전환점을 감지하는 데 사용됩니다. 이 지수는 OECD(경제협력개발기구)가 개발한 것으로, 경제 성장이나 둔화의 신호를 미리 파악하는 데 도움을 줍니다.",{italics:true,color:"64748B"}));
  children.push(p("1. OECD 경기선행지수란?",{bold:true,color:"1E40AF",before:100,size:20}));
  children.push(p("미래의 경기 변동을 예측하기 위해 여러 개별 경제 지표들을 종합하여 만든 지수로, 일반적으로 6~9개월 후의 경기 변화를 예측하는 데 활용됩니다.",{size:18}));
  children.push(p("단순한 경제 성장률이 아니라 경기의 전환점(고점·저점)을 예측하는 것이 목적입니다. 즉, 경제가 확장 국면에서 둔화 국면으로 전환하거나, 반대로 침체에서 회복 국면으로 전환하는 시점을 미리 감지하려는 것입니다.",{size:18}));
  children.push(p("2. 경기선행지수 구성 요소",{bold:true,color:"1E40AF",before:100,size:20}));
  children.push(p("• 신규 주문 지수: 제조업·서비스업 신규 주문량 변화    • 재고 수준: 재고 증가 또는 감소",{size:18}));
  children.push(p("• 소비자·기업 신뢰 지수: 소비자와 기업의 경제 전망    • 금융 지표: 장·단기 금리 차이, 주가 변동 등",{size:18}));
  children.push(p("• 수출입 데이터: 무역량·교역 조건 변화    • 산업 생산 지표: 공장 가동률, 제조업 생산량 등",{size:18}));
  children.push(p("이러한 개별 지표들을 종합하여 산출하며, 각국 경제 특성에 맞는 지표가 선택됩니다.",{size:17,color:"475569"}));
  children.push(p("3. 해석 방법 (기준점 100)",{bold:true,color:"1E40AF",before:100,size:20}));
  children.push(p("• 100 초과: 경기 확장 가능성이 큼 (경제 성장 국면)    • 100 이하: 경기 둔화 또는 수축 가능성",{size:18}));
  children.push(p("• 전월 대비 상승: 경기 개선 신호    • 전월 대비 하락: 경기 둔화 신호",{size:18}));
  children.push(p("보통 100을 넘어서면서 상승하면 성장 국면 진입, 100을 밑돌면서 하락하면 경기 둔화·침체 가능성이 커진다고 해석합니다.",{size:17,color:"475569"}));
  children.push(p("4. 한계",{bold:true,color:"1E40AF",before:100,size:20}));
  children.push(p("• 완벽한 예측이 아님: 과거 데이터·통계 기반이라 실제 경기 변화가 예상보다 늦거나 빠를 수 있음",{size:18}));
  children.push(p("• 단기 급변 반영 어려움: 급격한 경제 충격(코로나19 팬데믹·금융위기 등)에 대한 즉각적 반응이 제한적",{size:18}));
  children.push(p("• 국가별 차이: 각국 경제 구조가 달라 동일한 지수라도 해석이 다를 수 있음",{size:18}));
  children.push(p("")); }

// (v3.6.30) 3.2.2 FOMC 점도표(dot plot) — 데이터(markets.fomc_dotplot) 없으면 자동 생략.
function renderFomcDotplot(){ const f=data.markets&&data.markets.fomc_dotplot; if(!f||typeof f!=="object")return;
  if(!(Array.isArray(f.rows)&&f.rows.length)&&!f.summary)return;
  children.push(p("■ FOMC 점도표 (dot plot)",{bold:true,color:"1E40AF",before:140,size:22}));
  children.push(p("점도표(dot plot): FOMC 위원들이 향후 적정 정책금리 수준을 점으로 표시한 전망. 중간값이 상향되면 매파적(긴축)·하향되면 비둘기파(완화) 신호다.",{italics:true,color:"64748B"}));
  children.push(p("업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지",{size:15,italics:true,color:"94A3B8"}));
  if(f.summary)children.push(p(f.summary,{bold:true}));
  if(Array.isArray(f.rows)&&f.rows.length) simpleTable([3300,2300,2300,2300],["항목","6월 전망 (최신)","3월 전망 (이전)","변화"],f.rows.map(r=>[(r.item!=null?r.item:(r.year!=null?r.year:(r.period!=null?r.period:"-"))),(r.jun!=null&&r.jun!==""?r.jun:"- 미공개"),(r.mar!=null&&r.mar!==""?r.mar:"- 미공개"),(function(){ if(r.change!=null&&r.change!=="")return r.change; const j=parseFloat(String(r.jun||"").replace(/[^0-9.\-]/g,"")),m2=parseFloat(String(r.mar||"").replace(/[^0-9.\-]/g,"")); if(isFinite(j)&&isFinite(m2)){ const dd=+(j-m2).toFixed(2); return dd>0?("+"+dd+"%p 상향"):(dd<0?(dd+"%p 하향"):"변동 없음"); } return "-"; })()]),{left:[0]});
  if(Array.isArray(f.distribution)&&f.distribution.length){ children.push(p("연내 금리 전망 분포 (점 분포)",{bold:true,color:"1E40AF",before:100,size:20}));
    f.distribution.forEach(x=>children.push(p("• "+(x.label||"")+": "+(x.count||""),{size:19}))); }
  if(f.policy_rate)children.push(p("현 정책금리: "+f.policy_rate,{bold:true,before:60}));
  if(f.next_meeting)children.push(p("다음 점도표 발표: "+f.next_meeting,{size:18,color:"475569"}));
  if(Array.isArray(f.background)&&f.background.length){ children.push(p("배경 및 시장 영향",{bold:true,color:"1E40AF",before:100,size:20}));
    f.background.forEach(b=>children.push(p("• "+b,{size:19}))); }
  if(f.market_impact)children.push(p("시장 영향: "+f.market_impact,{color:"0F766E"}));
  if(Array.isArray(f.sources)&&f.sources.length)children.push(p("출처: "+f.sources.map(function(s){return (s&&typeof s==="object")?(s.source||s.item||s.url||""):s;}).filter(Boolean).join(" · "),{size:14,color:"94A3B8"}));
  children.push(p("")); }

// (v3.12.0→v3.49) 3.1.8 AI 빅테크 CAPEX — 3.1(매크로 대시보드)로 이동, 차트 풀폭(좌우 여백 제거).
function renderCapex(){ const m=data.markets||{};
  if(m.bigtech_capex&&Array.isArray(m.bigtech_capex.rows)&&m.bigtech_capex.rows.length){ const cx=m.bigtech_capex; children.push(h("3.1.8 AI 빅테크 자본지출(CAPEX)",3));
    if(Array.isArray(cx.change_log)&&cx.change_log.length){ children.push(p("■ CAPEX 변동 이력 (매일 체크 · 변경분):",{bold:true,size:14,color:"DC2626"})); cx.change_log.forEach(t=>children.push(p("• "+t,{size:14,color:"DC2626"}))); }
    // (v3.35) 기업별 4행: CAPEX / 매출 / Capex매출 / FCF — 표값으로 두 차트 구동
    const YR0=["2024","2025","2026","2027","2028","2029"]; const HD0=["2024","2025","2026E","2027E","2028E","2029E"];
    // (req8) 핵심지표(CAPEX/FCF) 전무한 (전망)연도 컬럼 드롭 + 확인불가/미확인/미공개 정규화
    const _bad=(t)=>t.includes("확인불가")||t.includes("미확인")||t.includes("미공개");
    const _cellHas=(v)=>{const t=(v==null?"":String(v)).trim();return t!==""&&t!=="-"&&!_bad(t);};
    const _keep=YR0.map((y,i)=>i).filter(i=>cx.rows.some(r=>["y","fcf"].some(pfx=>_cellHas(r[pfx+YR0[i]]))));
    const YR=_keep.map(i=>YR0[i]); const HD=_keep.map(i=>HD0[i]);
    const _cw=Math.max(820,Math.round(7050/Math.max(1,YR.length)));
    const w=[2050].concat(YR.map(()=>_cw));
    const num=(v)=>{let t=(v===null||v===undefined||v==="")?"-":(typeof v==="number"?(Number.isInteger(v)?String(v):v.toFixed(1)):String(v));return _bad(String(t))?"-":t;};
    const rows=[hdrRow(["항목 (십억 $)"].concat(HD),w)];
    cx.rows.forEach((r,ci)=>{ const a=ci%2===1;
      rows.push(new TableRow({children:[cell(r.company||"-",{width:w[0],alt:a,bold:true})].concat(
        YR.map((y,j)=>cell(num(r["y"+y]),{width:w[1+j],alt:a,align:AlignmentType.CENTER,bold:true})))}));
      rows.push(new TableRow({children:[cell("   └ 매출",{width:w[0],alt:a,size:16,color:"475569"})].concat(
        YR.map((y,j)=>cell(num(r["rev"+y]),{width:w[1+j],alt:a,align:AlignmentType.CENTER,size:16})))}));
      rows.push(new TableRow({children:[cell("   └ Capex/매출",{width:w[0],alt:a,size:16,color:"475569"})].concat(
        YR.map((y,j)=>{const v=r["ratio"+y];return cell((v==null||v===""||_bad(String(v)))?"-":v+"%",{width:w[1+j],alt:a,align:AlignmentType.CENTER,size:16,color:"1D4ED8"});}))}));
      rows.push(new TableRow({children:[cell("   └ FCF",{width:w[0],alt:a,size:16,color:"475569"})].concat(
        YR.map((y,j)=>{const v=r["fcf"+y];return cell(num(v),{width:w[1+j],alt:a,align:AlignmentType.CENTER,size:16,color:(typeof v==="number"&&v<0)?"DC2626":"0F172A"});}))}));
    });
    children.push(makeTable(w,rows));
    children.push(p("단위: 십억 달러(USD). CAPEX·매출·FCF 모두 연도별 조사값 — 2024~2025=FMP 실측(capitalExpenditure·revenue·freeCashFlow) · 2026~2029(E)=매출 애널리스트 컨센서스·CAPEX 회사 가이던스·FCF(직전 영업CF×매출성장−CAPEX) 추정. Capex/매출=CAPEX÷매출. ORCL은 FMP 플랜 제한으로 공개치·추정. 아래 두 차트는 이 표값으로 그려집니다.",{size:13,color:"94A3B8"}));
    if(cx.source_actual) children.push(p("출처(실적 2024·2025): "+cx.source_actual,{size:13,color:"64748B"}));
    if(cx.source_estimates) children.push(p("출처(전망 2026E~): "+cx.source_estimates,{size:13,color:"64748B"}));
    children.push(p("업데이트: 매일 자동 재수집 — 실적값(CAPEX·매출·FCF)은 매 실행 MCP(UsStockInfo get_financial_statement)로 각사 재무제표를 다시 읽어 db/capex.json 과 대조하고, 값이 바뀐 셀만 갱신한다(실제 변동은 분기 실적발표 시점). 미수집·결측 셀은 DB carry-forward. 전망값(2026E~, 수시 변동 가능)=각사 실적 컨퍼런스콜 CAPEX 가이던스 + 애널리스트 컨센서스. 기준일 "+(cx.as_of||"-"),{size:13,italics:true,color:"94A3B8"}));
    children.push(p("확인처 — 1차 출처: 각사 SEC 공시(EDGAR 10-K/8-K) · 데이터 API: FMP(Financial Modeling Prep)",{size:13,color:"64748B"}));
    children.push(fsLink("SEC EDGAR 기업 공시검색 (10-K/8-K 원문)","https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=10-K"));
    children.push(fsLink("FMP API 문서 (financial-statements · analyst-estimates)","https://site.financialmodelingprep.com/developer/docs"));
    // (req6 2026-07-12) 대시보드와 동일한 4분할 회사별 라인 차트(Microsoft·Amazon·Alphabet·Meta·Oracle)
    { const caps=[["charts/capex_capex.png","CAPEX 추이 (십억 달러) — 회사별"],["charts/capex_rev.png","매출 추이 (십억 달러) — 회사별"],
                  ["charts/capex_fcf.png","잉여현금흐름 FCF (십억 달러) — 회사별"],["charts/capex_ratio.png","CAPEX / 매출 — AI 투자 강도 (%)"]];
      let anyC=false;
      caps.forEach(([f,cap])=>{ const im=imagePara(f,660,248); if(im){ children.push(im); children.push(p(cap+" — 자료: 각사 SEC/FMP, AI Research",{size:15,color:"94A3B8"})); anyC=true; } });
      if(!anyC){ const c1=imagePara("charts/capex_stack_ratio.png",660,289); if(c1)children.push(c1); } }
    children.push(p("")); } }
// (v3.12.0) HY 스프레드 — 3.1.1 금리·통화정책에 통합(하위 블록).
function renderHY(){ const m=data.markets||{};
  if(m.hy_spread){ const c=m.hy_spread; children.push(p("■ 하이일드(HY) 스프레드",{bold:true,color:"1E40AF",before:140,size:22}));
    const _svHY=((data.markets||{}).server_notes||{}).hy; if(_svHY) children.push(p(_svHY,{size:15,italics:true,color:"7C3AED"}));
    children.push(p("의미: 하이일드 스프레드(HY Spread)는 고위험 회사채 수익률과 미국 국채 수익률의 차이로, 시장이 신용위험을 얼마나 크게 보는지 보여주는 지표.",{italics:true,color:"64748B"}));
    children.push(p("시장영향: HY Spread 확대 = 신용불안·리스크오프·주식 약세 압력, HY Spread 축소 = 신용정상화·리스크온·주식 회복 기대.",{italics:true,color:"64748B"}));
    // (req1 2026-07-17) 출처·관측 기준일 명시 — FRED 관측치는 T+1 공표라 기준일이 실행일과 다르다
    children.push(fsLink("출처 · FRED BAMLH0A0HYM2 (ICE BofA US High Yield Index Option-Adjusted Spread) · 관측 기준일 "+String(c.asof||"-")+" (FRED T+1 공표 — 최신 관측일 기준)","https://fred.stlouisfed.org/series/BAMLH0A0HYM2"));
    // (req1 2026-07-12) OAS 레벨 표 제거 — 차트+현재값 코멘트만 유지.
    if(c.current!=null)children.push(p("현재 OAS: "+Number(c.current).toFixed(2)+"%",{bold:true,size:20}));
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
// (3.4.1) 아시아 주요 ETF (한국 상장) — us_etfs 동일 trend2Rows/TR2. 데이터 없으면 자동 생략.
function renderAsiaEtfs(){ const e=data.markets&&data.markets.asia_etfs; if(!e||typeof e!=="object")return;
  const groups=[["asia","① 아시아 통합·대표 (여러 국가 묶음)"],["china","② 중국·홍콩 (본토·대형주·기술·플랫폼·홍콩)"],["japan","③ 일본 (대형주·반도체·환헤지)"],["taiwan","④ 대만 (전체시장·반도체)"],["india","⑤ 인도 (대표지수·소비)"],["vietnam","⑥ 베트남 (신흥시장)"],["sea","⑦ 동남아 (미국 상장 · 인도네시아·필리핀·말레이시아·태국·싱가포르)"]];  // (v3.50) 국가병합+sea
  if(!groups.some(function(g){return Array.isArray(e[g[0]])&&e[g[0]].length;}))return;
  children.push(h("3.4.1 아시아 주요 ETF (한국 상장 + 미국 상장 · 국가·테마별)",3));
  children.push(p("한국거래소에 상장된 아시아 국가·테마 대표 ETF 의 현재가(원화 종가)와 1일~1년 수익률, 1년 추세를 정리한다. 수익률은 일봉 종가 기준 가격수익률(분배금 제외)이며, 합성·환헤지(H) ETF는 기초시장과 괴리가 있을 수 있고 신규 상장 ETF는 상장 후 기간만 표시한다(장기 수익률 '-'). '1일' 컬럼은 직전 거래일 등락률, 현재가 아래 ▲/▼ 는 최근 거래일 등락이다. 달러($) 표기 행은 미국거래소 상장 ETF(달러 종가·티커 표기)로, 같은 나라의 국내 상장분과 한 그룹에서 교차 확인한다.",{italics:true,color:"64748B"}));
  groups.forEach(function(g){ var k=g[0],label=g[1]; var arr=e[k]; if(!Array.isArray(arr)||!arr.length)return;
    children.push(p(label,{bold:true,color:"1E40AF",before:120,size:21}));
    var items=arr.map(function(x){ var code=String(x.code||x.symbol||x.ticker||"-"); var nameLine=(x.name||code)+"  ["+code+"]";
      return {desc:[new TextRun({text:nameLine,bold:true,size:18,color:"1D4ED8"}),new TextRun({text:(x.desc?("  — "+x.desc):""),size:15,color:"64748B"})],
        m:x,current:x.current,curPrefix:(x.ccy==="USD"?"$":"₩"),trend:String(x.trend||"-"),chart:"charts/spark_aetf_"+code+".png"}; });  // (v3.50) 미국상장=$
    children.push(makeTable(TR2,trend2Rows(items))); });
  if(e.comment)children.push(p("추세 평가: "+e.comment,{bold:true,color:"0F766E"}));
  if(e.asof)children.push(p("기준: "+e.asof,{size:16,color:"94A3B8"}));
  children.push(p("")); }
// (v3.7.x) 3.5.1 주요 유럽 ETF — 국내상장(.KS)+미국상장 유럽 익스포저. 3.5 유럽 증시(지수표) 직후 서브섹션(아시아 3.4.1과 동형). 데이터(markets.europe_etfs) 없으면 자동 생략.
function renderEuropeEtfs(){ const e=data.markets&&data.markets.europe_etfs; if(!e)return;
  const items=Array.isArray(e)?e:(Array.isArray(e.items)?e.items:[]); if(!items.length)return;
  children.push(h("3.5.1 주요 유럽 ETF (지역·국가·섹터·테마)",3));
  children.push(p("유럽 광역·독일·프랑스·영국·유럽 은행/금융·방산·명품·탄소배출권 등 유럽 익스포저 ETF 의 현재가와 1일~1년 수익률·1년 추세를 정리한다. 국내 상장분(.KS)과 미국 상장분을 함께 보아 유럽 자금흐름을 교차 확인한다. 수익률은 주봉 종가 기준 가격수익률(분배금 제외)이며, 신규 상장 ETF 는 6개월·1년 값이 빌 수 있다. 태그 [국내]는 원화(₩)·환헤지, [미국]은 달러($) 기준.",{italics:true,color:"64748B"}));
  const its=items.map(function(x){ var sym=String(x.symbol||x.ticker||"-"); var tag=x.region?("["+x.region+"·"+sym+"]"):("["+sym+"]");
    return {desc:[new TextRun({text:(x.name||sym),bold:true,size:18,color:"1D4ED8"}),new TextRun({text:"  "+tag+(x.desc?("  — "+x.desc):""),size:15,color:"64748B"})],
      m:x,current:x.current,curPrefix:(x.region==="국내"?"₩":"$"),trend:String(x.trend||"-"),chart:"charts/spark_etf_"+sym+".png"}; });
  children.push(makeTable(TR2,trend2Rows(its)));
  if(e.comment)children.push(p("추세 평가: "+e.comment,{bold:true,color:"0F766E"}));
  if(e.asof)children.push(p("기준: "+e.asof,{size:16,color:"94A3B8"}));
  children.push(p("")); }
// (v3.50) 3.6 북미&중남미 / 3.7 호주&중동 — 미국상장 국가 ETF 추세표 (3.5.1 유럽과 동형, 데이터 없으면 자동 생략)
function renderRegionEtfs(key,title,introTxt){ const e=data.markets&&data.markets[key]; if(!e)return;
  const items=Array.isArray(e)?e:(Array.isArray(e.items)?e.items:[]); if(!items.length)return;
  children.push(h(title,2));
  children.push(p(introTxt,{italics:true,color:"64748B"}));
  const its=items.map(function(x){ var sym=String(x.symbol||x.ticker||"-");
    return {desc:[new TextRun({text:(x.name||sym)+"  ["+sym+"]",bold:true,size:18,color:"1D4ED8"}),new TextRun({text:(x.desc?("  — "+x.desc):""),size:15,color:"64748B"})],
      m:x,current:x.current,curPrefix:"$",trend:String(x.trend||"-"),chart:"charts/spark_etf_"+sym+".png"}; });
  children.push(makeTable(TR2,trend2Rows(its)));
  if(e.comment)children.push(p("추세 평가: "+e.comment,{bold:true,color:"0F766E"}));
  if(e.asof)children.push(p("기준: "+e.asof,{size:16,color:"94A3B8"}));
  children.push(p("")); }
function renderAmericasEtfs(){ renderRegionEtfs("americas_etfs","3.6 북미&중남미 증시 (미국 상장 국가 ETF)",
  "멕시코(니어쇼어링)·브라질(원자재·내수)·캐나다(에너지·금융) 등 북미·중남미 국가 대표 ETF(미국 상장, 달러 기준)의 현재가와 1일~1년 수익률·1년 추세를 정리한다. 수익률은 주봉 종가 기준 가격수익률(분배금 제외)."); }
function renderAumeEtfs(){ renderRegionEtfs("aume_etfs","3.7 호주&중동 증시 (미국 상장 국가 ETF)",
  "호주(자원·에너지)와 사우디아라비아·UAE·카타르 등 중동 주요 자본시장 대표 ETF(미국 상장, 달러 기준)의 현재가와 1일~1년 수익률·1년 추세를 정리한다. 수익률은 주봉 종가 기준 가격수익률(분배금 제외)."); }
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
// (v3.46) 4.4 비철금속 — 배터리·우라늄·전략광물 3개 테마 그룹 × 추세표(현재가/1일/1주/1개월/3개월/6개월/1년/추세(1Y)/추세평가). 구 4.5 전략광물·배터리 금속 대체.
function renderNonFerrous(){ const nf=data.commodities&&data.commodities.nonferrous; if(!nf)return;
  children.push(h("4.4 비철금속 (배터리·우라늄·전략광물 밸류체인)",2));
  (nf.groups||[]).forEach((g,gi)=>{
    children.push(h("4.4."+(gi+1)+" "+String(g.title||""),3));  // (req8) 소분류 번호 4.4.1~4.4.3
    if(g.desc)children.push(p(String(g.desc)));
    if(g.core)children.push(p("▸ 핵심 모니터링 원자재: "+String(g.core),{bold:true,size:20,color:"0F766E"}));
    if(g.core_desc)children.push(p(String(g.core_desc),{size:19,color:"334155"}));
    const its=(g.rows||[]).map(r=>{ const desc=[new TextRun({text:String(r.name||"-"),bold:true,size:20})]; if(r.note)desc.push(new TextRun({text:"  — "+r.note,size:16,color:"64748B"}));
      return {desc:desc,m:r,current:r.current,curSuffix:r.curSuffix,chart:r.spark?("charts/spark_"+r.spark+".png"):null,trend:r.trend}; });
    children.push(makeTable(TR2,trend2Rows(its))); children.push(p("")); });
  if(nf.comment)children.push(p("종합: "+String(nf.comment),{bold:true,color:"0F766E"}));
  children.push(p("범례: 추세(1Y)=최근 1년 주봉 스파크라인(초록=상승·빨강=하락). 탄산리튬은 GFEX 碳酸锂 主连 선물(EastMoney) 기준.",{italics:true,color:"94A3B8",size:16}));
  children.push(p("")); }

const children = []; let __cut31=-1;
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
["1. 글로벌 Top News 10","2. 글로벌 주요 이벤트 캘린더","3. 글로벌 증시 단·중·장기 추세 (매크로 지표 포함)","4. 원자재 (에너지·금속·희토류·농산물)","5. 주요 환율 (+달러인덱스)","6. 암호화폐","7. 한국 주요 증권사","8. 글로벌 IB (UBS·GS·JPM·MS·BlackRock)","9. 종합 분석","10. 자산별 견해","11. 추천 포트폴리오","12. 액션 아이템","13. 주의 사항 및 출처","[부록A] 워런 버핏 · 버크셔 13F","[부록B] 최신 AI Trends","[부록C] AI 반도체 밸류체인 (글로벌 개별종목)","[부록D] AI 반도체 밸류체인 관계도 (해자 지도)"].forEach(t=>children.push(p(t,{size:22,after:40})));

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
  const ew=[1200,900,2500,900,2560,1300];
  const evs1=data.news.events_calendar.filter(notBigtechEvent);
  const er=[new TableRow({children:["날짜","지역","이벤트","중요도","예상 영향","출처"].map((c,j)=>cell(c,{width:ew[j],header:true,align:AlignmentType.CENTER}))}),
    ...evs1.map((e,k)=>{ const alt=(k+1)%2===0;
      const srcRuns=(e.source||e.source_url)?[linkRun(e.source||"링크",e.source_url,{size:18})]:[cellRun("-",{size:18})];
      return new TableRow({children:[cell(e.date??"-",{width:ew[0],alt,align:AlignmentType.CENTER}),
        cell(e.region??"-",{width:ew[1],alt,align:AlignmentType.CENTER}),
        cell(e.event??"-",{width:ew[2],alt,bold:true}),
        cell(e.importance??"-",{width:ew[3],alt,align:AlignmentType.CENTER,color:String(e.importance||"").includes("★★★")?"DC2626":undefined}),
        cell(e.expected_impact??"-",{width:ew[4],alt}),
        cell("",{width:ew[5],alt,runs:srcRuns})]}); })];
  children.push(makeTable(ew,er));
} else children.push(p("(1개월 이벤트 없음)"));
children.push(p(""));
children.push(h("2.2 중장기 1개월~1년 (★★★만)",2));
if (data.news && Array.isArray(data.news.events_calendar_longterm) && data.news.events_calendar_longterm.length) {
  const lw=[1300,1000,2700,2760,1600];
  const evs2=data.news.events_calendar_longterm.filter(function(e){return e&&e.event;}).filter(notBigtechEvent);
  const lr=[new TableRow({children:["날짜","지역","이벤트","예상 영향","출처"].map((c,j)=>cell(c,{width:lw[j],header:true,align:AlignmentType.CENTER}))}),
    ...evs2.map((e,k)=>{ const alt=(k+1)%2===0;
      const srcRuns=(e.source||e.source_url)?[linkRun(e.source||"링크",e.source_url,{size:18})]:[cellRun("-",{size:18})];
      return new TableRow({children:[cell(e.date??"-",{width:lw[0],alt,align:AlignmentType.CENTER}),
        cell(e.region??"-",{width:lw[1],alt,align:AlignmentType.CENTER}),
        cell(e.event??"-",{width:lw[2],alt,bold:true}),
        cell(e.expected_impact??"-",{width:lw[3],alt}),
        cell("",{width:lw[4],alt,runs:srcRuns})]}); })];
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
function imgCellSpark(relPath,width,alt,iw,ih){ iw=iw||84; ih=ih||28; try{var _mxpx=Math.floor(((width||1200)-150)/1440*96); if(_mxpx>=24&&iw>_mxpx){ih=Math.max(12,Math.round(ih*_mxpx/iw));iw=_mxpx;}}catch(e){} let fp=null; if(!relPath)return cell("-",{width:width,alt:alt,align:AlignmentType.CENTER});
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
// (v3.46) 4.3 농산물 — 그룹(핵심곡물·기후충격·비용종합) + 농업ETF + 비료/농기계 대장주. 각 소그룹은 trend2 추세표(현재가/1일/1주/1개월/3개월/6개월/1년/추세1Y/추세평가).
const AGRI_LAB={corn:"옥수수",soybean:"대두",wheat:"소맥(밀)",sugar:"설탕",coffee:"커피",orange:"오렌지주스",
  crb:"CRB 상품지수 (프록시 ^TRCCRB)",bdi:"BDI 운임 (프록시 BDRY ETF)",
  dba:"DBA · Invesco DB Agriculture",de:"디어 (DE)",ntr:"뉴트리엔 (NTR)"};
function renderAgriculture(){ const a=data.commodities&&data.commodities.agriculture; if(!a)return;
  children.push(h("4.3 농산물",2));
  simpleTable([2500,3200,5460],["그룹","포함 항목","모니터링 목적"],[
    ["Core Macro (핵심 곡물)","옥수수·대두·소맥","글로벌 식품 인플레이션 및 사료 가치 사슬 전가 흐름 파악"],
    ["Climate Shock (기후 충격)","설탕·커피·오렌지주스","공급망 교란으로 인한 기술적 CPI 노이즈 체크"],
    ["Macro Cost (비용·종합)","CRB 상품지수·BDI 운임 (프록시)","원자재 종합 압력 및 실질 수입 물가 선행 흐름 파악"],
  ],{left:[1,2]});
  children.push(p(""));
  function agriTbl(keys){ const items=[]; for(const k of keys){ const v=a[k]; if(!v||typeof v!=="object")continue;
    items.push({desc:[new TextRun({text:AGRI_LAB[k]||k.toUpperCase(),bold:true,size:20})],m:v,current:v.current,chart:"charts/spark_"+k+".png"}); }
    if(items.length) children.push(makeTable(TR2,trend2Rows(items))); }
  children.push(h("4.3.1 핵심 곡물 (Core Macro)",3));
  children.push(p("옥수수·대두·소맥 — 글로벌 식품 인플레이션 및 사료 가치 사슬 전가 흐름을 파악한다.",{italics:true,color:"64748B"}));
  agriTbl(['corn','soybean','wheat']);
  children.push(h("4.3.2 기후 충격 (Climate Shock)",3));
  children.push(p("설탕·커피·오렌지주스 — 이상기후·공급망 교란이 만드는 기술적 CPI 노이즈를 체크한다.",{italics:true,color:"64748B"}));
  agriTbl(['sugar','coffee','orange']);
  children.push(h("4.3.3 비용·종합 (Macro Cost)",3));
  children.push(p("CRB 상품지수·BDI 운임 — 원자재 종합 압력과 실질 수입 물가의 선행 흐름을 파악한다.",{italics:true,color:"64748B"}));
  children.push(p("※ 프록시(대리지표) 안내 — 보고 싶은 원지표(CRB 식품 지수·BDI 원지수)는 무료 실시간 데이터가 없어, 방향이 거의 같이 움직이는 아래 대체 지표로 근사한다. 완전히 같은 값이 아니라 '추세를 대신 보여주는 근사치'다.",{italics:true,color:"64748B",size:18}));
  children.push(p("▸ CRB 식품 지수 → ^TRCCRB(로이터/CoreCommodity CRB 상품지수): '식품만' 뽑은 하위지수는 유료라, 식품·에너지·금속을 아우르는 전체 CRB 상품지수로 근사한다. 식품 단독은 아니지만 원자재 전반의 물가 압력 방향은 함께 움직인다.",{color:"475569",size:18}));
  children.push(p("▸ BDI 운임 → BDRY(건화물선 운임 선물 ETF): 발틱운임지수(BDI) 원지수는 발틱거래소 유료 데이터라, 같은 건화물선 운임 선물에 투자하는 ETF로 대체한다. 등락 방향은 거의 함께 가지만, 지수 레벨(수천 포인트)이 아니라 ETF 가격($12 수준)이므로 절대 수치가 아닌 등락률·추세로만 읽는다.",{color:"475569",size:18}));
  agriTbl(['crb','bdi']);
  children.push(h("4.3.4 농업 ETF (DBA)",3));
  agriTbl(['dba']);
  children.push(reportBullet("글로벌 농업·상품 ETF (Invesco DB Agriculture Fund · DBA): 개별 농산물 가격을 하나씩 확인하기 번거로울 때, 주요 농산물 선물 바스켓의 전체적인 자금 유입·유출 흐름을 한 눈에 보여주는 유용한 지표다."));
  children.push(h("4.3.5 비료·농기계 글로벌 대장주 (DE·NTR)",3));
  agriTbl(['de','ntr']);
  children.push(reportBullet("비료·농기계 글로벌 대장주 (디어 DE, 뉴트리엔 NTR): 곡물 가격이 상승하면 농가 소득이 증가하고, 이는 곧 트랙터(농기계)와 비료 수요 증가로 이어진다. 농산물 랠리가 주식 시장의 실적으로 어떻게 연결되는지 확인하는 핵심 척도다."));
  const c=data.commodities.agri_comment; if(c){ children.push(p("추세 평가: "+c,{bold:true,color:"0F766E"})); }
  children.push(p(""));
}
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

// (2026-06-29) 3.1.6 = Earnings Insight (FactSet): 블로그 최신글 + 주간 리포트 첫장 요약 (DB: nmr_factset.json)
function fsLink(text,url){ if(!url||!HAS_LINK) return p(text,{size:14,color:"475569"});
  return new Paragraph({spacing:{after:60},children:[new TextRun({text:text+"  ",size:14,color:"475569"}),
    new ExternalHyperlink({link:url,children:[new TextRun({text:url,color:"1155CC",size:12,underline:{type:"single"}})]})]}); }
function renderFactSet(){ const m=data.markets||{}; const fs=m.factset; if(!fs||(!fs.blog&&!fs.report))return;
  children.push(h("3.1.6 Earnings Insight (FactSet)",3));
  children.push(p("업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지",{size:15,italics:true,color:"94A3B8"}));
  children.push(p("FactSet Earnings Insight 의 최신 블로그 포스트와 주간 리포트를 요약한다. 원문 그래프·표는 출처 링크에서 확인(저작권상 본 보고서에는 사실 요약·수치만 수록).",{italics:true,color:"64748B"}));
  children.push(fsLink("출처(토픽 페이지) · FactSet Insight — Earnings", (fs.topic_url||"https://insight.factset.com/topic/earnings")));
  const b=fs.blog||{};
  if(b.title){
    children.push(p("■ "+(b.title_ko||b.title),{bold:true,color:"1E40AF",before:120,size:20}));
    if(b.title_ko) children.push(p(b.title,{italics:true,color:"64748B",size:14}));
    children.push(fsLink("블로그 포스트 · "+(b.date||"")+(b.author?(" · "+b.author):""), b.url));
    (b.points||b.summary||[]).forEach(s=>children.push(p("• "+s,{size:16,color:"334155"})));
  }
  const r=fs.report||{};
  if(r.title){
    children.push(p("■ "+(r.title||"Earnings Insight report"),{bold:true,color:"1E40AF",before:160,size:20}));
    children.push(fsLink("리포트 · "+(r.date||"")+(r.author?(" · "+r.author):""), r.url));
    if(Array.isArray(r.full_summary)&&r.full_summary.length){
      r.full_summary.forEach(sec=>{ if(!sec)return;
        children.push(p("· "+(sec.section||""),{bold:true,color:"1E3A8A",size:17,before:70}));
        (sec.points||[]).forEach(pt=>children.push(p("   - "+pt,{size:15,color:"334155"})));
      });
    } else {
      (r.key_metrics||[]).forEach(s=>children.push(p("• "+s,{size:16,color:"334155"})));
    }
    if(r.chart){ const _fc=imagePara(r.chart,580,335); if(_fc)children.push(_fc); }
    if(r.next_date) children.push(p("▶ 다음 리포트 발행 예정: "+r.next_date,{bold:true,color:"1E40AF",size:16,before:40}));
  }
  // (req4) 투자자 입장에서 중요도 — Earnings Insight 지표별 가이드
  children.push(p("▣ 투자자 입장에서 중요도 (Earnings Insight 핵심 지표)",{bold:true,color:"1E40AF",before:180,size:19}));
  [
    ["① Earnings Revisions ★★★★★","실적 전망 상향 여부 — 애널리스트가 미래 EPS(주당순이익) 전망을 상향/하향 조정한 내용 (예: 삼성전자 올해 EPS 전망 10% 상향)"],
    ["② Earnings Growth ★★★★★","이익 증가 속도 — 순이익·EPS 증가율 (예: 전년 대비 EPS +25%)"],
    ["③ Forward Estimates & Valuation ★★★★★","현재 주가가 비싼지 싼지 — 미래 예상 실적 기반 밸류에이션 (대표: Forward P/E 선행 PER·EV/EBITDA·PEG)"],
    ["④ Targets & Ratings ★★★★","시장 전문가 의견 — 목표주가·투자등급 (예: Target $250 / Buy·Overweight·Hold·Underperform·Sell)"],
    ["⑤ Revenue Growth ★★★★","매출 성장 — 매출액 증가율 (예: 전년 대비 매출 +15%)"],
    ["⑥ Net Profit Margin ★★★★","수익 효율성 — 순이익률 = 순이익÷매출×100 (예: 매출 100억·순이익 15억 → 15%)"],
    ["⑦ Earnings Guidance ★★★","회사 공식 전망 — 회사가 직접 제시하는 미래 실적 전망 (예: 2026년 매출 10조원 예상)"]
  ].forEach(x=>{ children.push(p(x[0],{bold:true,size:16,color:"334155",before:50})); children.push(p("   "+x[1],{size:14,color:"475569"})); });
  children.push(p("※ 주식 투자 관점에서는 특히 Earnings Revisions(실적 추정치 상향)와 Forward P/E(선행 PER)를 가장 먼저 보는 경우가 많습니다. 이는 향후 6~12개월 주가 방향과 연관성이 큰 지표로 평가됩니다.",{italics:true,bold:true,color:"1E3A8A",size:15,before:90}));
  if(fs.source_note) children.push(p(fs.source_note,{size:13,italics:true,color:"94A3B8"}));
  children.push(p(""));
}
function renderMacroIndicators(){
  const M=data.markets||{}; const x=M.macro; if(!x)return;
  children.push(h("3.1 주요지표 (매크로 대시보드)",2));
  children.push(p("증시 방향을 좌우하는 금리·물가·고용·심리 지표를 의미·발표주기·시장영향과 함께 정리한다.",{italics:true,color:"64748B"}));
  children.push(p("※ UPDATE 원칙: 모든 지표는 매일 최신값을 조사·반영하는 것이 대원칙. 단, 발표주기가 매일이 아닌 모든 지표는 '업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지'로 명시하고, 데이터를 별도 DB(파일)에 저장해 매 실행 변동 여부만 조사하며, 변동이 없으면 DB에 저장된 값을 그대로 사용합니다.",{size:15,italics:true,color:"94A3B8"}));

  // ── ① 매크로 (정책·경기) ── 3.1.1~3.1.5
  children.push(gh("① 매크로 (정책·경기)"));

  // 3.1.1 금리·통화정책 (REQ2 순서: 美10년물 → 장단기차 → HY → 기준금리 → FOMC회의 → 점도표)
  const r=x.rates||{};
  children.push(h("3.1.1 금리·통화정책 (가장 직접적 영향)",3));
  // [1] 美 국채금리 (10Y·2Y, 매일 실측)
  if(r.us10y||r.us2y){ const w=[1700,1100,680,680,680,680,680,680,1150,1810];
    children.push(p("■ 美 국채금리 (10년물·2년물)",{bold:true,color:"1E40AF",size:22,before:60}));
    const rows=[hdrRow(["지표","현재가","1일","1주","1개월","3개월","6개월","1년","추세(1Y)","추세 평가"],w)];
    const trow=(label,o,sparkPath)=>{ if(!o)return; rows.push(new TableRow({children:[cell(label,{width:w[0],bold:true}),
      cell("",{width:w[1],align:AlignmentType.RIGHT,runs:curCellRuns(o.current,o,{suffix:"%"})}),
      cell(fmtPct(day1pct(o)),{width:w[2],align:AlignmentType.RIGHT,color:pctColor(day1pct(o))}),
      cell(fmtPct(o["1w_pct"]),{width:w[3],align:AlignmentType.RIGHT,color:pctColor(o["1w_pct"])}),cell(fmtPct(o["1mo_pct"]),{width:w[4],align:AlignmentType.RIGHT,color:pctColor(o["1mo_pct"])}),
      cell(fmtPct(o["3mo_pct"]),{width:w[5],align:AlignmentType.RIGHT,color:pctColor(o["3mo_pct"])}),cell(fmtPct(o["6mo_pct"]),{width:w[6],align:AlignmentType.RIGHT,color:pctColor(o["6mo_pct"])}),
      cell(fmtPct(o["1y_pct"]),{width:w[7],align:AlignmentType.RIGHT,color:pctColor(o["1y_pct"])}),imgCellSpark((o.spark)||sparkPath,w[8],false,150,40),cell(o.trend||"-",{width:w[9],size:16})]})); };
    trow("美 10년물 국채금리",r.us10y,"charts/spark_us10y.png"); trow("美 2년물 국채금리",r.us2y,"charts/spark_us2y.png");
    children.push(makeTable(w,rows));
    children.push(p("의미: 10년물=장기 기준금리 역할 · 2년물=정책금리 기대 민감 · 시장영향: 금리↑ → 기술·성장주 부담·채권↓",{size:16,color:"64748B"}));
  }
  // [2] 미국 장단기 금리차 (10Y-2Y, 매일 실측)
  if(r.yield_curve){ const yc=r.yield_curve;
    children.push(p("■ "+(yc.label||"미국 장단기 금리차(수익률곡선)(10Y-2Y)"),{bold:true,size:22,color:"1E40AF",before:140}));
    children.push(p((yc.spread>=0?"+":"")+yc.spread+"%p → "+yc.status+"  ("+(yc.note||"")+")",{bold:true,size:22,color:"1E40AF"}));
    children.push(p("의미: "+(yc.meaning||"")+" · 시장영향: "+(yc.impact||""),{size:16,color:"64748B"}));
    const cc=imagePara(yc.chart,648,176); if(cc)children.push(cc); }
  // [3] 하이일드(HY) 스프레드 (매일)
  renderHY();
  // [4] FOMC 기준금리 + 6개국 정책금리 (변동 시 갱신·실측)
{ const _cl=r.fomc_change_log; if(Array.isArray(_cl)&&_cl.length){ children.push(p("■ 정책금리 변동 이력 (직전 대비):",{bold:true,size:15,color:"DC2626"})); _cl.forEach(t=>children.push(p("• "+t,{size:14,color:"DC2626"}))); } }
    if(r.fed_funds){ const f=r.fed_funds;
    children.push(p("■ FOMC 기준금리(현재): "+f.current+"%   ("+f.decision+" / "+f.bias+")",{bold:true,size:23,color:"1E40AF",before:140}));
    children.push(p("의미: "+f.meaning+" · 발표: "+f.freq+" · 시장영향: "+f.impact,{size:17,color:"64748B"}));
    children.push(p("업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지",{size:15,italics:true,color:"94A3B8"})); }
  if(Array.isArray(r.policy_rates)){
    const w=[2100,1600,1700,4680]; const rows=[hdrRow(["국가","현재 정책금리","기준일","비고"],w)];
    r.policy_rates.forEach((c,i)=>rows.push(new TableRow({children:[cell(c.country,{width:w[0],alt:i%2===0,bold:true}),
      cell(c.rate!=null?c.rate+"%":"-",{width:w[1],alt:i%2===0,align:AlignmentType.CENTER}),cell(c.asof||"-",{width:w[2],alt:i%2===0,align:AlignmentType.CENTER}),cell(c.note||"",{width:w[3],alt:i%2===0,size:16})]})));
    children.push(makeTable(w,rows));
    const pc=imagePara(r.policy_rates_chart,648,243); if(pc){children.push(pc);} }
  // [5] FOMC 회의 일정·정책방향 (신규 회의 시 갱신)
  if(Array.isArray(r.fomc_meetings)){
    children.push(p("■ FOMC 회의 일정·정책방향 (최근 1년 · 최신순)",{bold:true,color:"1E40AF",before:140,size:22}));
    const w=[2200,2300,5580]; const rows=[hdrRow(["회의일","정책방향","결정·코멘트"],w)];
    r.fomc_meetings.slice().sort((a,b)=>String(b&&b.date||"").localeCompare(String(a&&a.date||""))).forEach((mt,i)=>rows.push(new TableRow({children:[
      cell(mt.date,{width:w[0],alt:i%2===0,align:AlignmentType.CENTER,bold:true}),
      cell(mt.stance||mt.expectation||"",{width:w[1],alt:i%2===0,align:AlignmentType.CENTER,bold:true,color:markStance(mt.stance||mt.expectation)}),  // (req2) expectation 폴백 — undefined 방지
      cell(mt.note||"",{width:w[2],alt:i%2===0})]})));
    children.push(makeTable(w,rows));
    children.push(p("의미: 연준 정책방향(매파/비둘기파) · 발표: 회의 후 즉시",{size:16,color:"64748B"}));
    children.push(p("업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지",{size:15,italics:true,color:"94A3B8"}));
    if(r.fomc_market_impact)children.push(p("시장영향: "+r.fomc_market_impact,{size:17,bold:true,color:"334155"})); }
  // [6] FOMC 점도표
  renderFomcDotplot();
  children.push(p(""));

  // 3.1.2 물가 — 추세1Y 제거, 통합 그래프 하나
  const inf=x.inflation||{};
  children.push(h("3.1.2 물가·인플레이션 (금리 방향 결정)",3));
  children.push(p("업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지, BEI는 실시간",{size:15,italics:true,color:"94A3B8"}));
{ const _cl=inf.change_log; if(Array.isArray(_cl)&&_cl.length){ children.push(p("■ 물가 변동 이력 (직전 대비):",{bold:true,size:15,color:"DC2626"})); _cl.forEach(t=>children.push(p("• "+t,{size:14,color:"DC2626"}))); } }
    { const w=[860,1060,1020,820,1040,1860,1660,1560];
    const fy=(v)=> (v===null||v===undefined||v==="")?"-":(typeof v==="number"?((v>=0?"+":"")+v+"%"):String(v));
    const rows=[hdrRow(["지표","최신값 YoY","최신값 MoM","기준월","발표날짜","의미","시장영향","예상영향"],w)];
    (inf.rows||[]).forEach((o,i)=>{ const a=i%2===1; rows.push(new TableRow({children:[
      cell(o.name||"-",{width:w[0],alt:a,bold:true}),
      cell(fy(o.yoy),{width:w[1],alt:a,align:AlignmentType.CENTER}),
      cell(fy(o.mom),{width:w[2],alt:a,align:AlignmentType.CENTER}),
      cell(o.asof||"-",{width:w[3],alt:a,align:AlignmentType.CENTER,size:15}),
      cell(o.release||o.release_date||"-",{width:w[4],alt:a,align:AlignmentType.CENTER,size:15}),
      cell(o.meaning||"-",{width:w[5],alt:a,size:14}),
      cell(o.impact||"-",{width:w[6],alt:a,size:14}),
      cell(o.interp||"-",{width:w[7],alt:a,size:14})]})); });
    children.push(makeTable(w,rows)); }
  { const ic=imagePara(inf.chart||'charts/macro_inflation.png',660,259); if(ic){ children.push(ic); } }
  { const bc=imagePara("charts/macro_infl_exp.png",648,176); if(bc){ children.push(p("■ 기대인플레이션 (10년 BEI) — 실시간 시장지표",{bold:true,color:"1E40AF",before:100,size:19})); children.push(bc); } }
  children.push(p(""));

  // 3.1.3 고용 — 추세1Y 제거, 통합 그래프 하나
  if(x._db_unverified&&(((x._db_unverified.rows_backfilled||[]).length)||((x._db_unverified.series_unverified||[]).length))){ const u=x._db_unverified; children.push(p("⚠ 변경 미확인: 당일 미수집 셀 "+(u.rows_backfilled||[]).length+"개"+((u.series_unverified||[]).length?(" · 시계열 "+u.series_unverified.length+"종"):"")+"는 DB 직전값 사용(다음 실행 재조사).",{size:14,color:"DC2626"})); }
  const emp=x.employment||{};
  children.push(h("3.1.3 고용·경기 (금리 간접 영향)",3));
  children.push(p("업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지",{size:15,italics:true,color:"94A3B8"}));
{ const _cl=emp.change_log; if(Array.isArray(_cl)&&_cl.length){ children.push(p("■ 고용 변동 이력 (직전 대비):",{bold:true,size:15,color:"DC2626"})); _cl.forEach(t=>children.push(p("• "+t,{size:14,color:"DC2626"}))); } }
    { const w=[1700,1080,940,1040,2020,1880,1480]; const rows=[hdrRow(["지표","최신 수치","기준","발표일자","의미","시장영향","예상영향"],w)];
    (emp.rows||[]).forEach((o,i)=>{ const a=i%2===1; rows.push(new TableRow({children:[
      cell(o.name,{width:w[0],alt:a,bold:true}), cell(o.value!=null?String(o.value):"-",{width:w[1],alt:a,align:AlignmentType.CENTER,bold:true}),
      cell(o.asof||"-",{width:w[2],alt:a,align:AlignmentType.CENTER}), cell(o.release||o.release_date||"-",{width:w[3],alt:a,align:AlignmentType.CENTER,size:15}),
      cell((o.meaning||"-")+(o.freq?(" · "+o.freq):""),{width:w[4],alt:a,size:15}), cell(o.impact||"-",{width:w[5],alt:a,size:15}), cell(o.interp||"-",{width:w[6],alt:a,size:15})]})); });
    children.push(makeTable(w,rows)); }
    { const ec=imagePara(emp.chart||'charts/macro_employment.png',660,556); if(ec){ children.push(ec); children.push(p("고용·경기 7개 지표 (① 초기 실업수당 청구건수=주간 조기신호, ② NFP·③ 실업률 > ④ 소매판매 > ⑤ ISM제조 > ⑥ ISM서비스 > ⑦ GDP). 청구건수만 주간, 나머지 월별(GDP만 분기).",{size:15,color:"94A3B8"})); } }
  children.push(p(""));

  renderOecdCli();   // 3.1.4 OECD 경기선행지수(CLI) — 방향 신호, 통합 차트 + 설명(DB: db/oecd_cli.json)
  renderKoreaLeading();   // 3.1.5 경기선행지수 순환변동치 — 국내 확인 신호

  // ── ② 기업 실적 ── 3.1.6~3.1.8
  children.push(gh("② 기업 실적"));
  renderFactSet();   // 3.1.6 Earnings Insight (FactSet) — 블로그 최신글 + Earnings Insight 리포트 요약(DB: nmr_factset.json)
  renderM7Outlook();   // 3.1.7 미국 빅테크(M7) 실적 전망 — 가이던스·추정치 변화 시장 신호 (매일)
  renderCapex();   // 3.1.8 AI 빅테크 자본지출(CAPEX)

  // ── ③ 반도체·한국 연결고리 ── 3.1.9~3.1.11
  children.push(gh("③ 반도체·한국 연결고리"));
  renderHBM();   // 3.1.9 반도체 주가 체크용 메모리+HBM 지표
  renderCustoms();   // 3.1.10 관세청 수출 잠정치 — 그룹막대 2종(전체·반도체)
  renderSemiCycle();   // 3.1.11 반도체 사이클→코스피 점검판 (DB: db/semi_cycle.json)

  // ── ④ 수급·심리 (선행신호) ── 3.1.12~3.1.13
  children.push(gh("④ 수급·심리 (선행신호)"));
  // 3.1.12 심리 — 6개월 추가
  const s=x.sentiment||{};
  children.push(h("3.1.12 심리·자금흐름 보조지표",3));
  { const w=[1400,1050,700,700,700,700,700,700,1230,2000]; const rows=[hdrRow(["지표","현재가","1일","1주","1개월","3개월","6개월","1년","추세(1Y)","추세 평가"],w)];
    (s.rows||[]).forEach((o,i)=>{ const a=i%2===1; rows.push(new TableRow({children:[
      cell(o.name,{width:w[0],alt:a,bold:true}), cell("",{width:w[1],alt:a,align:AlignmentType.RIGHT,runs:curCellRuns(o.current,o,{})}),
      cell(fmtPct(day1pct(o)),{width:w[2],alt:a,align:AlignmentType.RIGHT,color:pctColor(day1pct(o))}),
      cell(fmtPct(o['1w_pct']),{width:w[3],alt:a,align:AlignmentType.RIGHT,color:pctColor(o['1w_pct'])}), cell(fmtPct(o['1mo_pct']),{width:w[4],alt:a,align:AlignmentType.RIGHT,color:pctColor(o['1mo_pct'])}),
      cell(fmtPct(o['3mo_pct']),{width:w[5],alt:a,align:AlignmentType.RIGHT,color:pctColor(o['3mo_pct'])}), cell(fmtPct(o['6mo_pct']),{width:w[6],alt:a,align:AlignmentType.RIGHT,color:pctColor(o['6mo_pct'])}),
      cell(fmtPct(o['1y_pct']),{width:w[7],alt:a,align:AlignmentType.RIGHT,color:pctColor(o['1y_pct'])}), imgCellSpark(o.spark,w[8],a,150,40), cell(o.trend||"-",{width:w[9],alt:a,size:16})]})); });
    children.push(makeTable(w,rows)); }
  { const w=[2000,2900,5180]; const rows=[hdrRow(["지표","의미","시장 영향"],w)];
    (s.rows||[]).forEach((o,i)=>rows.push(new TableRow({children:[cell(o.name,{width:w[0],alt:i%2===1,bold:true}),
      cell(o.meaning||"-",{width:w[1],alt:i%2===1,size:17}),cell(o.use||o.impact||"-",{width:w[2],alt:i%2===1,size:17})]})));
    children.push(makeTable(w,rows)); }
  children.push(p(""));
  renderDerivPositioning();   // 3.1.13 파생시장 포지셔닝→현물 선행신호 (스냅샷·z매트릭스·활성신호·해석)
  renderKrLiquidity();        // 3.1.14 국내 유동성·레버리지 점검판 (판정+차트4종, 서버 1일 3회 수집)
}

// (v3.44) 3.1.10 관세청 수출 주요품목별 10일 단위 잠정치 통계 — DB: db/customs.json, 변경 시에만 재수집·차트 재생성
function renderCustoms(){ const m=data.markets||{}; const cs=m.customs;
  if(!cs||!cs.series||!Array.isArray(cs.months)||!cs.months.length) return;
  children.push(h("3.1.10 관세청 수출 주요품목별 10일 단위 잠정치 통계",3));
  children.push(p("업데이트:매 실행 변동 여부만 체크, 변동없으면 기존 자료 유지",{size:15,italics:true,color:"94A3B8"}));
  const _svCS=((data.markets||{}).server_notes||{}).customs; if(_svCS) children.push(p(_svCS,{size:15,italics:true,color:"7C3AED"}));
  const lat=cs.latest||{}, pm=lat.pm||{}, p10=lat.p10||{}, p20=lat.p20||{};
  const ym=lat.yyyymm?(lat.yyyymm.slice(0,4)+"-"+lat.yyyymm.slice(4,6)):"";
  const fmt=v=>(v==null?"-":Number(v).toLocaleString("en-US"));
  simpleTable([2600,2400,2400,2400],["구분("+ym+")","1~10일","1~20일","1~말일"],
    [["전체 수출액",fmt(p10.total),fmt(p20.total),fmt(pm.total)],
     ["반도체",fmt(p10.semiconductor),fmt(p20.semiconductor),fmt(pm.semiconductor)]],{left:[0]});
  children.push(p("단위: 천 달러 · 누계(1~10 / 1~20 / 1~말일) · 잠정치 · 출처: "+(cs.source||"관세청 data.go.kr(15157908)"),{size:15,color:"94A3B8"}));
  { const im=imagePara(cs.chart_total||"charts/수출_전체_24개월.png",700,285);
    if(im){ children.push(im); children.push(p("전체 수출액 최근 24개월 — 월별 1~10/1~20/1~말일 누계(천 달러)",{size:15,color:"94A3B8"})); } }
  { const im=imagePara(cs.chart_semi||"charts/수출_반도체_24개월.png",700,285);
    if(im){ children.push(im); children.push(p("반도체 수출액 최근 24개월 — 월별 1~10/1~20/1~말일 누계(천 달러)",{size:15,color:"94A3B8"})); } }
  children.push(p("10일 단위 잠정치: 1~10일분은 11일, 1~20일분은 21일, 1~말일분은 익월 1일 공표. 전월까지는 정정·취하를 반영해 현행화(당월은 잠정치).",{italics:true,color:"64748B",size:17}));
  children.push(p(""));
}

// (v3.46.0) 3.1.7 미국 빅테크(M7) 실적 전망 — 가이던스·애널리스트 추정치 변화 시장 신호.
// 매일 실측(DB 아님): 시세·목표주가·투자의견·리비전은 매 실행 갱신, 가이던스·연간 추정치는 실적 때 갱신.
// 데이터(markets.m7_outlook) 없으면 내장 스냅샷으로 항상 렌더(비차단). 라이브는 merge 가 nmr_m7.json→markets.m7_outlook 로 주입.
// (v3.47.0) 3.1.13 파생시장 포지셔닝 → 현물 선행신호 — 파생·수급 지표 z-score 스냅샷.
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
  children.push(h("3.1.13 파생시장 포지셔닝 기반 현물 선행신호 분석",3));
  children.push(p("선물 베이시스·순포지션/수급·풋콜비율·IV 스큐·딜러 감마(GEX)를 롤링 z-score(60거래일)로 표준화한 현재 스냅샷. |z|≥1.5는 통계적으로 이례적인 신호.",{size:15,italics:true,color:"94A3B8"}));
  if(dp.asof)children.push(p("기준일 — "+dp.asof,{size:14,color:"64748B"}));
  children.push(p("※ 기준일 안내 — 미국 COT는 CFTC 공표 구조상 최신분(화요일 포지션 기준·금요일 공표)으로 1주 내외 지연이 정상이며, 일중 타이밍이 아닌 주간 포지셔닝(구조적 쏠림) 지표다. 선물 베이시스·KOSPI200 현물/수급·미국 옵션(PCR·IV·GEX)은 당일~T+1 데이터로 단기 신호를 담당한다.",{size:13,italics:true,color:"94A3B8"}));
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
  children.push(p("※ z 공란 안내 — KOSPI200 풋콜비율·IV 스큐·딜러 감마(GEX)는 KRX 지수옵션 일별통계(drv/opt_bydd_trd, IV·OI 전 행사가)로 롤링 60거래일 백필 완료(2026-07-17, deriv_signals/backfill_kr_opt.py)되어 z-스코어가 산출된다. 미국(SPX·NDX) 옵션 지표는 과거 체인의 무료 소스가 없어(KIS·네이버 포함 재검토 결과 불가) 2026-07-11 수집 개시분부터 자체 누적 중 — 60거래일이 쌓이는 2026년 10월경부터 z 자동 산출(그때까지 현재값 + 'z making' 표시). 한국 외국인·기관 수급 z 도 주간 이력 누적 후 순차 산출. N/A = 해당 지수에서 조사 불가 항목(VKOSPI 는 한국 전용 — 미국은 VIX).",{size:14,italics:true,color:"94A3B8"}));
  // (2026-07-17) '쉬운 의미' 열 — 지표 라벨별 한 줄 해설(초심자용). export 라벨과 접두 매칭.
  const DPM={
    "선물 베이시스":"선물가격−현물가격 차이. 플러스가 크면 '더 오른다'는 베팅이 몰린 것(위험선호), 마이너스면 하락 베팅 우세.",
    "레버리지":"공격적 투기자금(美 레버리지펀드/韓 외국인)의 선물 순포지션. 플러스=상승 베팅, 마이너스=하락 베팅.",
    "자산운용":"연기금·운용사 등 큰손 장기자금(韓은 기관)의 선물 순포지션. 방향이 바뀌면 추세 전환 신호.",
    "선물 OI 변화":"열려 있는 선물 계약 수의 증감. 늘면 새 자금 유입(추세 강화), 줄면 포지션 청산(추세 약화).",
    "풋콜비율":"풋(하락 보험)÷콜(상승 베팅). 지나치게 높으면 공포 과잉 — 역발상 반등 신호로 자주 쓰임.",
    "IV 스큐":"하락 보험(풋)이 상승 베팅(콜)보다 얼마나 비싼가. 클수록 폭락 대비 수요가 큼(공포).",
    "딜러 감마":"옵션 딜러의 헤지 성향. 플러스면 딜러가 변동을 눌러 시장 안정, 마이너스면 움직임을 증폭(급변 위험).",
    "VKOSPI":"코스피200 옵션가격으로 계산한 '한국판 공포지수(VIX)'. 높을수록 시장이 큰 변동을 예상."};
  const dpm=(lab)=>{lab=String(lab||"");for(const k in DPM)if(lab.startsWith(k))return DPM[k];return "";};
  const zw=[1720,2600,1680,1680,1680]; const zr=[hdrRow(["지표","쉬운 의미","S&P 500","Nasdaq 100","KOSPI200"],zw)];
  const fz=(c)=>{ const z=(c&&c.z!=null&&!isNaN(c.z))?Number(c.z):null; const sig=(z!=null&&Math.abs(z)>=1.5);
    const hasV=c&&c.v!=null&&!["-","—",""].includes(String(c.v).trim());
    if(!hasV) return {t:"N/A", s:false, c:"94A3B8"};
    return {t:String(c.v)+"  (z "+(z==null?"making":((z>=0?"+":"")+z.toFixed(2)))+")", s:sig, c:sig?(z>=0?"1D4ED8":"B91C1C"):"0F172A"}; };
  dp.rows.forEach((r,i)=>{const a=i%2===1; const cs=(r.cells||[]).map(fz);
    zr.push(new TableRow({children:[cell(r.label||"-",{width:zw[0],alt:a,bold:true,size:14}),
      cell(dpm(r.label),{width:zw[1],alt:a,size:12,color:"475569"})].concat(
      cs.map((x,j)=>cell(x.t,{width:zw[j+2],alt:a,align:AlignmentType.CENTER,size:13,bold:x.s,color:x.c})))}));});
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

// (v3.64) 3.1.14 국내 유동성·레버리지 점검판 — 서버 1일 3회 수집(금융위·다음·ECOS) → fetch_krliq → gen_krliq_charts.
// 데이터 없으면 섹션 비차단 생략(경고만).
function renderKrLiquidity(){ const kl=(data.markets||{}).kr_liquidity;
  if(!kl||!kl.as_of){ console.error("  (경고) markets.kr_liquidity 없음 → 3.1.14 생략"); return; }
  const V=kl.verdict||{};
  const toneC={"강세":"0A7D33","중립":"8A6D00","경계":"B45309","약세":"B91C1C"}[V.tone]||"334155";
  children.push(h("3.1.14 국내 유동성·레버리지 점검판",3));
  children.push(p("목적 — ① 예탁금+거래대금: 대기자금이 실제로 시장에 들어오는지 · ② M2+코스피/코스닥: 거시 유동성과 주가 추세 · ③ 신용융자+변동성+반대매매: 레버리지 과열 · ④ 코스닥 신용: 마진콜 조기경보. 서버가 1일 3회(06:35/14:10/16:10 KST) 자동 수집한 시계열 기반.",{size:14,color:"475569"}));
  if(V.label) children.push(p(`① 자동 판정: ${V.label} (${V.tone}) — 예탁금 5일 ${V.dep_5d_pct>0?"+":""}${V.dep_5d_pct}% · 회전배수 5일 ${V.turn_5d_chg>0?"+":""}${V.turn_5d_chg}p · 기준 ${String(V.as_of).replace(/(\d{4})(\d{2})(\d{2})/,"$2/$3")} (T+2)`,{bold:true,size:16,color:toneC}));
  children.push(p("판정 규칙(2×2): 예탁금 증가×회전배수 상승=유입·가동(강세) / 증가×하락=유입·관망(중립) / 감소×상승=이탈·소진성 회전(경계) / 감소×하락=이탈·위축(약세)",{size:13,italics:true,color:"94A3B8"}));
  const caps=[["charts/krliq_1.png",258,"① 예탁금·거래대금·코스피(상) + 회전배수(하) — 판정은 차트 제목에 자동 표기"],
              ["charts/krliq_2.png",150,"② M2 YoY vs 코스피·코스닥 YoY (월별 10년 · M2 약 2개월 지연 · ECOS)"],
              ["charts/krliq_3.png",275,"③ 신용융자·코스피·VKOSPI(상) + 미수금 기반 반대매매금액·비중(하)"],
              ["charts/krliq_4.png",275,"④ 코스닥 신용잔고·지수·비중(상) + 잔고 일간 증감(하) — 마진콜 근사"]];
  let shown=0;
  for(const [fp,hh,cap] of caps){ const img=imagePara(fp,660,hh);
    if(img){ children.push(img); children.push(p(cap,{size:13,color:"94A3B8",align:AlignmentType.CENTER})); shown++; }
    else console.error("  (경고) "+fp+" 없음 → 3.1.14 차트 생략"); }
  const nn=v=>(v==null?"—":v);
  children.push(p(`최신(T+2 ${String(kl.as_of).replace(/(\d{4})(\d{2})(\d{2})/,"$2/$3")}): 예탁금 ${nn(kl.deposit_t)}조 · 신용융자 ${nn(kl.crd_t)}조(코스닥 ${nn(kl.crd_kosdaq_t)}조, 비중 ${nn(kl.kosdaq_share)}%) · 반대매매 ${nn(kl.opp_amt_e)}억(미수금 대비 ${nn(kl.opp_ratio)}%) · 코스닥 신용 5일 증감 ${nn(kl.kosdaq_chg5_e)}억 · M2 YoY ${nn(kl.m2_yoy)}% vs KOSPI ${nn(kl.kospi_yoy)}% / KOSDAQ ${nn(kl.kosdaq_yoy)}%`,{size:15,color:"334155"}));
  children.push(p("유의 — 반대매매 통계는 위탁매매 미수금(D+2 미납) 기반만 공표(금투협 원천, T+2). 신용융자 담보부족(마진콜) 반대매매는 공표 통계가 없어 ④ 코스닥 신용잔고 급감으로 간접 추정(상환·강제청산 구분 불가). 반대매매 급증은 선행지표가 아닌 후행 확인 지표이며 역사적으로 항복(단기 바닥) 국면과 동행하는 경우가 많음. 데이터: 금융위 공공데이터(금투협 원천) · 다음금융(T+0) · 한국은행 ECOS. 리서치용·투자권유 아님.",{size:13,italics:true,color:"94A3B8"}));
  children.push(p("")); }

const M7_OUTLOOK_DEFAULT = { as_of: "2026-07-03 종가", rows: [
  {name:"Alphabet",ticker:"GOOGL",price:"359.91",chg52:"+103.6%",consensus:"강력 매수",consensus_detail:"2SB/69B/11H/1S",target:"432.3",upside:"+20.1%",revision:"상향",revision_detail:"353→422→416",guidance:"클라우드 +63%로 capex 정당화",signal:"긍정"},
  {name:"Amazon",ticker:"AMZN",price:"242.67",chg52:"+8.6%",consensus:"강력 매수",consensus_detail:"0SB/84B/9H/1S",target:"312.9",upside:"+28.9%",revision:"상향",revision_detail:"298→315→330",guidance:"AWS +28%(3년 최고)로 정당화",signal:"긍정"},
  {name:"NVIDIA",ticker:"NVDA",price:"194.83",chg52:"+23.1%",consensus:"강력 매수",consensus_detail:"2SB/58B/16H/3S",target:"301.6",upside:"+54.8%",revision:"상향",revision_detail:"277→318",guidance:"가이던스 상회·Blackwell 초과수요",signal:"긍정"},
  {name:"Apple",ticker:"AAPL",price:"308.63",chg52:"+47.0%",consensus:"매수",consensus_detail:"1SB/69B/34H/7S",target:"315.1",upside:"+2.1%",revision:"완만 상향",revision_detail:"301→327→338",guidance:"가이던스 유지·capex 논쟁 밖",signal:"중립"},
  {name:"Microsoft",ticker:"MSFT",price:"390.49",chg52:"-21.5%",consensus:"매수(약화)",consensus_detail:"0SB/66B/16H/0S",target:"561.1",upside:"+43.7%",revision:"하향",revision_detail:"590→537→400*",guidance:"capex ~$190B>컨센·FCF 감소",signal:"경계"},
  {name:"Meta",ticker:"META",price:"582.90",chg52:"-18.9%",consensus:"매수(약화)",consensus_detail:"2SB/50B/11H/2S",target:"828.2",upside:"+42.1%",revision:"하향",revision_detail:"845→768",guidance:"capex 상향·2027 $200B설",signal:"경계"},
  {name:"Tesla",ticker:"TSLA",price:"393.45",chg52:"+33.9%",consensus:"보유",consensus_detail:"0SB/32B/34H/15S",target:"423.4",upside:"+7.6%",revision:"정체·하향",revision_detail:"440→437→430",guidance:"인도 +25%나 마진 불확실",signal:"위험"}
]};
function renderM7Outlook(){ const m=data.markets||{};
  const src=(m.m7_outlook&&Array.isArray(m.m7_outlook.rows)&&m.m7_outlook.rows.length)?m.m7_outlook:M7_OUTLOOK_DEFAULT;
  const rows0=src.rows||[]; if(!rows0.length) return;
  children.push(h("3.1.7 미국 빅테크(M7) 실적 전망 (가이던스·애널리스트 추정치 변화)",3));
  children.push(p("업데이트:매일",{size:15,italics:true,color:"94A3B8"}));
  children.push(p("이익 추정치·목표주가의 방향(상향/하향)과 가이던스 변화를 섹터·시장의 선행 신호로 읽는다. 가이던스 하향·추정치 조정 = 하락의 직접 신호.",{size:16,color:"475569"}));
  const w=[1050,1150,1350,1300,1560,1960,1040];
  const revC=r=>{const t=String(r||"");return t.includes("상향")?positiveColor:(t.includes("하향")?negativeColor:mixedColor);};
  const sigC=s=>{const t=String(s||"");return t.includes("긍정")?positiveColor:(t.includes("위험")?negativeColor:(t.includes("경계")?mixedColor:"64748B"));};
  const rows=[hdrRow(["기업","현재가·52주","컨센서스","평균목표주가·여력","목표주가 리비전","최근 가이던스","신호"],w)];
  rows0.forEach((o,i)=>{ const a=i%2===1; rows.push(new TableRow({children:[
    cell("",{width:w[0],alt:a,align:AlignmentType.LEFT,runs:[cellRun(o.name||"-",{bold:true,size:18}),new TextRun({text:o.ticker||"",size:14,color:"64748B",break:1})]}),
    cell("",{width:w[1],alt:a,align:AlignmentType.CENTER,runs:[cellRun(o.price!=null?String(o.price):"-",{bold:true,size:19}),new TextRun({text:o.chg52||"",size:15,color:markSign(o.chg52),break:1})]}),
    cell("",{width:w[2],alt:a,align:AlignmentType.LEFT,runs:[cellRun(o.consensus||"-",{bold:true,size:16}),new TextRun({text:o.consensus_detail||"",size:13,color:"64748B",break:1})]}),
    cell("",{width:w[3],alt:a,align:AlignmentType.CENTER,runs:[cellRun(o.target!=null?String(o.target):"-",{bold:true,size:19}),new TextRun({text:(o.upside||"")+" 여력",size:15,color:markSign(o.upside),break:1})]}),
    cell("",{width:w[4],alt:a,align:AlignmentType.LEFT,runs:[cellRun(o.revision||"-",{bold:true,size:16,color:revC(o.revision)}),new TextRun({text:o.revision_detail||"",size:13,color:"64748B",break:1})]}),
    cell(o.guidance||"-",{width:w[5],alt:a,size:16}),
    cell(o.signal||"-",{width:w[6],alt:a,align:AlignmentType.CENTER,bold:true,color:sigC(o.signal)})]})); });
  children.push(makeTable(w,rows));
  children.push(p("신호 판정: 추정치·목표주가 상향=긍정 / 실적 호조에도 목표주가 하향·디레이팅=경계 / 이익 모멘텀·의견 악화=위험 / 안정=중립.",{size:15,color:"94A3B8"}));
  children.push(p("핵심: 2026년 M7 이익 추정치는 상향(S&P500 EPS 성장 기대 14%→18%, IT 섹터 Q2 EPS +8.7%)이나, 조정은 추정치가 아니라 AI capex 수익화 의문에 따른 밸류에이션·목표주가 디레이팅에서 발생. 구글·아마존·엔비디아=긍정, MS·메타=경계, 테슬라=위험, 애플=중립.",{size:16,color:"475569"}));
  children.push(p("출처: 회사 실적발표·Refinitiv/LSEG I/B/E/S·Bloomberg·FactSet·증권사 리포트 · 데이터 기준 "+(src.as_of||"직전 미국 종가")+" · 정보 제공 목적(투자 자문 아님).",{size:15,color:"94A3B8"}));
  children.push(p(""));
}

if (data.markets) {
  renderMacroIndicators();
  if(process.env.NMR_ONLY_31)__cut31=children.length;
  if(!process.env.NMR_ONLY_31) renderMarketBlock("3.2 한국 증시",data.markets.korea,{kospi:"코스피",kosdaq:"코스닥"});
  renderKoreaExtras();
  renderMarketBlockC("3.3 미국 증시",{sp500:(data.markets.us_markets||{}).sp500,nasdaq:(data.markets.us_markets||{}).nasdaq,dow:(data.markets.us_markets||{}).dow},{sp500:"S&P 500",nasdaq:"나스닥",dow:"다우"},data.markets.us_prev);
  children.push(p("※ 현재치는 매 실행 시 최신값으로 갱신되며, 직전 보고서 대비 값이 변동된 항목은 빨간색으로 강조됩니다.",{size:16,italics:true,color:"94A3B8"}));
  // (VIX 설명은 3.1.12 주요지표 심리지표로 이동)
  renderUSExtras();
  renderMarketBlockC("3.4 아시아 증시",data.markets.asia_markets,{nikkei:"닛케이 225",shanghai:"상하이종합",hsi:"홍콩 항셍",taiwan:"대만 가권",sensex:"인도 센섹스",vietnam:"베트남 (VNM)"});
  renderAsiaEtfs();
  renderMarketBlockC("3.5 유럽 증시",data.markets.europe_markets,{stoxx50:"유로 스톡스 50",dax:"독일 DAX",ftse:"영국 FTSE 100"});
  renderEuropeEtfs();  // 3.5.1 주요 유럽 ETF (국내상장+미국상장) — 아시아 3.4.1과 동형
  renderAmericasEtfs();  // (v3.50) 3.6 북미&중남미 (미국상장 국가 ETF)
  renderAumeEtfs();      // (v3.50) 3.7 호주&중동 (미국상장 국가 ETF)
}
children.push(new Paragraph({children:[new PageBreak()]}));
children.push(h("4. 원자재 종합 - 에너지·금속·희토류·농산물",1));
if (data.commodities) {
  (function(){ var e=data.commodities.energy||{};   // (사용자요청 v3.47) 4.1 에너지 = WTI·천연가스 + 국내 에너지 ETF 2종 통합 추세표(Brent 제외·두바이유 생략)
    children.push(h("4.1 에너지",2));
    children.push(p("전통 유종·천연가스와 국내 상장 에너지 ETF(전통 화석연료 · AI 전력망 인프라)를 한 표에서 본다. $ 표기는 국제 선물(USD), 원 표기는 국내 상장 ETF(KRW).",{italics:true,color:"64748B",size:16}));
    var EN_ORDER=["wti","natgas","kodex_energy","kodex_aipower"];
    var EN_NAME={wti:"WTI 원유",natgas:"천연가스",kodex_energy:"KODEX 미국S&P500에너지(합성)",kodex_aipower:"KODEX 미국AI전력핵심인프라"};
    var EN_DESC={
      wti:"서부텍사스산 원유. NYMEX에서 거래되는 WTI(Western Texas Intermediate) 선물 최근월물 가격으로, 세계 3대 유종 중 하나이며 국제 유가를 선도하는 지표 (계약단위 1,000 배럴)",
      natgas:"NYMEX에서 거래되는 천연가스 선물 최근월물 가격. 지하에서 자연적으로 발생하는 가연성 가스 (계약단위 10,000 MMBtu)",
      kodex_energy:"전통 에너지(화석연료) 기업 · S&P500 에너지 섹터 합성 추종 ETF (218420)",
      kodex_aipower:"넥스트 에너지(전력망/인프라) · 미국 AI 전력 핵심 인프라 ETF (487230)"};
    var eits=[];
    EN_ORDER.forEach(function(k){ var v=e[k]; if(!v||typeof v!=="object")return; var kr=(k==="kodex_energy"||k==="kodex_aipower");
      eits.push({desc:[new TextRun({text:EN_NAME[k],bold:true,size:20}),new TextRun({text:EN_DESC[k],size:14,color:"64748B",break:1})],
        m:v,current:v.current,curPrefix:kr?"":"$",curSuffix:kr?" 원":"",chart:"charts/spark_"+k+".png"}); });
    if(eits.length){ children.push(makeTable(TR2,trend2Rows(eits)));
      if(data.commodities.energy_comment)children.push(p("추세 평가: "+data.commodities.energy_comment,{bold:true,color:"0F766E"})); }
    children.push(p("")); })();
  renderMarketBlockC("4.2 금속",(function(_mm){var _o={};for(var _k in (_mm||{}))if(_k!=="rare_earth")_o[_k]=_mm[_k];return _o;})(data.commodities.metals),{gold:"금",silver:"은",copper:"구리",platinum:"백금"},null,data.commodities.metals_comment);
  renderAgriculture();
  renderNonFerrous();
  if(data.commodities.commentary){ children.push(h("원자재 종합 코멘트",2)); children.push(p(data.commodities.commentary)); }
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
    for(let i=0;i<mx;i++){ const _gp=g[i]?(g[i].change_pct!=null?g[i].change_pct:(g[i].change_percent!=null?g[i].change_percent:g[i].change_24h)):null; const _lp=l[i]?(l[i].change_pct!=null?l[i].change_pct:(l[i].change_percent!=null?l[i].change_percent:l[i].change_24h)):null; /* (req9 2026-07-17) CryptoAgent 표준키 change_24h 폴백 */ gr.push([String(i+1),g[i]?(g[i].symbol||g[i].name||"-"):"-",g[i]?fmtPct(_gp):"-",l[i]?(l[i].symbol||l[i].name||"-"):"-",l[i]?fmtPct(_lp):"-"]); }
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
  if(data.global_securities.wall_street_consensus){ var _w=data.global_securities.wall_street_consensus;
    var _wsFmt=function(v){ if(v==null)return ""; if(Array.isArray(v))return v.map(function(it){ return (it&&typeof it==="object")?[(it.firm||it.broker||it.name||""),(it.target!=null?it.target:""),(it.as_of?("("+it.as_of+")"):"")].filter(Boolean).join(" "):String(it); }).join(", "); if(typeof v==="object")return Object.keys(v).map(function(a){return a+" "+_wsFmt(v[a]);}).join(", "); return String(v); };
    var _wsLabel={sp500_year_end_2026_targets:"S&P500 2026년말 목표치",note:"비고"};
    var _ws=(_w&&typeof _w==="object")?Object.keys(_w).map(function(k){return (_wsLabel[k]||k)+": "+_wsFmt(_w[k]);}).join("  /  "):String(_w); children.push(h("8.7 월가 컨센서스",2)); children.push(p(_ws)); }
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
// (v3.51) [부록C] AI 반도체 밸류체인 — 글로벌 개별종목 43종(분류 그룹별 추세표). 데이터(markets.appendix_c) 없으면 자동 생략.
function renderAppendixC(){ const e=data.markets&&data.markets.appendix_c; if(!e||!e.rows||typeof e.rows!=="object")return;
  const groups=Array.isArray(e.groups)?e.groups:Object.keys(e.rows);
  const GL="①②③④⑤⑥⑦⑧⑨⑩";
  if(!groups.some(function(g){return Array.isArray(e.rows[g])&&e.rows[g].length;}))return;
  children.push(new Paragraph({children:[new PageBreak()]}));
  children.push(h("[부록C] AI 반도체 밸류체인 (글로벌 개별종목)",1));
  children.push(p("AI 반도체 흐름을 수요(빅테크)→설계(팹리스·가속기)→제조(파운드리·메모리)→소재·장비→후공정→전력 인프라 순으로 잇는 글로벌 개별종목의 현재가와 1일~1년 수익률·1년 추세를 정리한다. 접두 $=미국(달러)·¥=일본(엔)·₩=한국(원) 종가 기준, 수익률은 일봉 종가 기준 가격수익률(배당 제외).",{italics:true,color:"64748B"}));
  let tot=0; const ys=[];
  groups.forEach(function(g,gi){ const arr=e.rows[g]; if(!Array.isArray(arr)||!arr.length)return;
    tot+=arr.length; arr.forEach(function(x){ if(x&&x["1y_pct"]!=null)ys.push(Number(x["1y_pct"])); });
    children.push(p((GL[gi]||"■")+" "+g+" ("+arr.length+"종)",{bold:true,color:"1E40AF",before:120,size:21}));
    const items=arr.map(function(x){ const sym=String(x.code||x.symbol||"-");
      return {desc:[new TextRun({text:(x.name||sym)+"  ["+sym+"]",bold:true,size:18,color:"1D4ED8"}),new TextRun({text:(x.desc?("  — "+x.desc):""),size:15,color:"64748B"})],
        m:x,current:x.current,curPrefix:(x.ccy==="JPY"?"¥":(x.ccy==="KRW"?"₩":"$")),trend:String(x.trend||"-"),chart:"charts/spark_c_"+sym.replace(/\./g,"_")+".png"}; });
    children.push(makeTable(TR2,trend2Rows(items))); });
  if(ys.length){ const a=ys.reduce(function(x,y){return x+y;},0)/ys.length;
    children.push(p("추세 평가: AI 반도체 밸류체인 "+tot+"종(1년 수익률 산출 "+ys.length+"종) 1년 평균 "+(a>=0?"+":"")+a.toFixed(1)+"%. 통화가 서로 달라 수익률은 현지통화 기준이며, 환율 효과는 반영되지 않는다.",{bold:true,color:"0F766E"})); }
  if(e.asof)children.push(p("기준: "+e.asof,{size:16,color:"94A3B8"}));
  children.push(p("")); }
// (v3.52) [부록D] AI 반도체 밸류체인 관계도(해자 지도) — 정적 이미지 3장. 원본=repo assets/appd_valuechain_{1..3}.png
// (assets/gen_appd_valuechain.py 로 종목 구성 변경 시에만 재생성). charts/ 미존재 시 repo에서 무결성(IEND) 검증·git show 폴백 후 복사. 없으면 자동 생략(비차단).
function renderAppendixD(){ try{
  const cp=require('child_process');
  function pngOk(b){ return b&&b.length>1000&&b[0]===0x89&&b.slice(-8).toString('latin1').indexOf('IEND')>=0; }
  function loadOne(i){
    const rel='charts/appd_valuechain_'+i+'.png';
    try{ if(fs.existsSync(rel)){ const b0=fs.readFileSync(rel); if(pngOk(b0))return {rel:rel,buf:b0}; } }catch(e){}
    let src=''; try{ src=cp.execSync("find /sessions -maxdepth 7 -path '*namoobi-market-report/assets/appd_valuechain_"+i+".png' 2>/dev/null | head -1").toString().trim(); }catch(e){}
    if(!src)return null;
    let b=null; try{ b=fs.readFileSync(src); }catch(e){}
    if(!pngOk(b)){ try{ const repo=src.replace(/\/assets\/appd_valuechain_[0-9]\.png$/,''); b=cp.execSync('git -C "'+repo+'" show HEAD:assets/appd_valuechain_'+i+'.png',{maxBuffer:16*1024*1024}); }catch(e){} }
    if(!pngOk(b))return null;
    try{ if(!fs.existsSync('charts'))fs.mkdirSync('charts'); fs.writeFileSync(rel,b); }catch(e){ return null; }
    return {rel:rel,buf:b};
  }
  const imgs=[1,2,3].map(loadOne);
  if(!imgs.some(Boolean))return;
  children.push(new Paragraph({children:[new PageBreak()]}));
  children.push(h("[부록D] AI 반도체 밸류체인 관계도 (해자 지도)",1));
  children.push(p("[부록C] 개별종목이 '왜 중요한지'를 한 장의 흐름으로 정리한 관계도. 돈은 위(빅테크 CAPEX)에서 아래로 흐르고, 칩은 아래에서 위로 올라간다. 파란 배지=독점·준독점(대체재 사실상 없음), 황색 배지=과점·복점·양강. 시세와 무관한 구조 설명용 정적 이미지(종목 구성 변경 시 assets/gen_appd_valuechain.py 로 재생성).",{italics:true,color:"64748B"}));
  imgs.forEach(function(o,k){ if(!o)return;
    const W=o.buf.readUInt32BE(16), H=o.buf.readUInt32BE(20);
    const img=imagePara(o.rel,700,Math.round(700*H/Math.max(W,1)));
    if(img){ if(k>0)children.push(new Paragraph({children:[new PageBreak()]})); children.push(img); } });
  children.push(p("핵심: ASML(EUV 유일) → TSMC(선단공정) → NVIDIA(CUDA 락인) → SK하이닉스(HBM) 로 이어지는 병목 사슬이 밸류체인 해자의 축이며, 전력 인프라 단은 '칩보다 전기가 부족하다'는 새 병목에 대한 노출이다.",{bold:true,color:"0F766E"}));
}catch(e){} }
renderBerkshire();
renderAITrends();
renderAppendixC();  // (v3.51) [부록C] AI 반도체 밸류체인
renderAppendixD();  // (v3.52) [부록D] AI 반도체 밸류체인 관계도(해자 지도)
if(__cut31>=0)children.length=__cut31;
const doc=new Document({ ...(embedFontData?{fonts:[{name:FONT,data:embedFontData}]}:{}),
  styles:{ default:{document:{run:{font:FONT,size:22}}},
  paragraphStyles:[
    {id:"Heading1",name:"Heading 1",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:36,bold:true,font:FONT,color:"1E3A8A"},paragraph:{spacing:{before:360,after:200},outlineLevel:0}},
    {id:"Heading2",name:"Heading 2",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:28,bold:true,font:FONT,color:"1E40AF"},paragraph:{spacing:{before:240,after:140},outlineLevel:1}},
    {id:"Heading3",name:"Heading 3",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:24,bold:true,font:FONT,color:"334155"},paragraph:{spacing:{before:180,after:100},outlineLevel:2}}]},
  numbering:{config:[{reference:"bullets",levels:[{level:0,format:LevelFormat.BULLET,text:"•",alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:720,hanging:360}}}}]}]},
  sections:[{ properties:{page:{size:{width:12240,height:15840},margin:{top:1080,right:540,bottom:1080,left:540}}},
    headers:{default:new Header({children:[new Paragraph({alignment:AlignmentType.RIGHT,children:[new TextRun({text:`글로벌 금융시장 종합 시황 보고서 | ${reportDate}`,size:18,color:"64748B"})]})]})},
    footers:{default:new Footer({children:[new Paragraph({alignment:AlignmentType.CENTER,children:[new TextRun({text:"Page ",size:18,color:"64748B"}),new TextRun({children:[PageNumber.CURRENT],size:18,color:"64748B"}),new TextRun({text:" / ",size:18,color:"64748B"}),new TextRun({children:[PageNumber.TOTAL_PAGES],size:18,color:"64748B"}),new TextRun({text:"  |  v3.6.26",size:18,color:"64748B"})]})]})},
    children }] });
Packer.toBuffer(doc).then(buffer=>{ fs.mkdirSync(path.dirname(outPath),{recursive:true}); fs.writeFileSync(outPath,buffer);
  console.log("OK "+(buffer.length/1024).toFixed(1)+"KB tbl "+tableCount);
}).catch(e=>{ console.error("FAIL "+e.message); process.exit(1); });
// EOF — namoobi-market-report v3.6.26
