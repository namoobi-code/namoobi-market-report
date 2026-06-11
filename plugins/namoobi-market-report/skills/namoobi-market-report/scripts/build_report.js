#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const argv = process.argv.slice(2);
const validateOnly = argv[0] === '--validate';
const args = validateOnly ? argv.slice(1) : argv;
if (args.length < 1) { console.error("Usage: node genreport.js [--validate] <input.json> [out.docx]"); process.exit(1); }
const inputPath = args[0];
let data;
try { data = JSON.parse(fs.readFileSync(inputPath, 'utf-8')); }
catch (e) { console.error(`JSON parse fail: ${inputPath}\n${e.message}`); process.exit(1); }

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
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType, ShadingType, PageNumber, PageBreak, ExternalHyperlink } = docx;
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
function pctColor(v){ if(v===null||v===undefined||v==="")return undefined; const n=Number(v); if(isNaN(n))return undefined; return n>=0?positiveColor:negativeColor; }
function fmtNum(v){ if(v===null||v===undefined||v==="")return "-"; const n=Number(v); if(isNaN(n))return String(v); if(Math.abs(n)>=1000)return n.toLocaleString(undefined,{maximumFractionDigits:2}); return n.toFixed(2); }
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

const children = [];
children.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{before:2400,after:240},children:[new TextRun({text:"글로벌 금융시장 종합 시황 보고서",bold:true,size:48,color:"1E3A8A"})]}));
children.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:240},children:[new TextRun({text:"Global Financial Markets Comprehensive Report",italics:true,size:28,color:"475569"})]}));
children.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:1200},children:[new TextRun({text:"Top News · 이벤트 캘린더 · 단·중·장기 추세 · 매크로 · 원자재·희토류 · 환율 · 코인 · 5대 증권사 · 포트폴리오",size:20,color:"64748B"})]}));
children.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:120},children:[new TextRun({text:`기준일: ${reportDate}`,size:26,bold:true})]}));
children.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:120},children:[new TextRun({text:"작성: Claude AI Research — v3.4.2",size:22,color:"64748B"})]}));
children.push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{before:360,after:0},
  border:{top:{style:BorderStyle.SINGLE,size:4,color:"F59E0B"},bottom:{style:BorderStyle.SINGLE,size:4,color:"F59E0B"}},
  children:[new TextRun({text:"⚠ 본 보고서는 AI(Claude)가 공개 데이터를 자동 수집·생성한 참고 자료입니다. 투자 자문이 아니며, 자동 생성 특성상 오류·환각이 포함될 수 있으니 중요한 의사결정 전 반드시 원문 출처를 확인하십시오.",size:18,italics:true,color:"B45309"})]}));

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
["1. 글로벌 Top News 10","2. 글로벌 주요 이벤트 캘린더","3. 글로벌 증시 단·중·장기 추세 (매크로 지표 포함)","4. 원자재 (에너지·금속·희토류·농산물)","5. 주요 환율 (+달러인덱스)","6. 암호화폐","7. 한국 5대 증권사","8. 글로벌 IB (UBS·GS·JPM·MS·BlackRock)","9. 종합 분석","10. 자산별 견해","11. 추천 포트폴리오","12. 액션 아이템","13. 주의 사항 및 출처"].forEach(t=>children.push(p(t,{size:22,after:40})));

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
      cell(n.impact??"-",{width:nw[3],alt}),cell("",{width:nw[4],alt,runs:srcRuns})]})); });
  children.push(makeTable(nw,rows));
} else children.push(p("(뉴스 데이터 없음)"));

children.push(new Paragraph({children:[new PageBreak()]}));
children.push(h("2. 글로벌 주요 이벤트 캘린더",1));
children.push(h("2.1 향후 1개월 (전체 중요도)",2));
if (data.news && Array.isArray(data.news.events_calendar) && data.news.events_calendar.length) {
  const ew=[1300,1100,2800,1100,3060];
  const er=[["날짜","지역","이벤트","중요도","예상 영향"],...data.news.events_calendar.map(e=>[e.date??"-",e.region??"-",e.event??"-",e.importance??"-",e.expected_impact??"-"])].map((r,i)=>new TableRow({children:r.map((c,j)=>cell(c,{width:ew[j],header:i===0,alt:i>0&&i%2===0,align:(j===0||j===1||j===3)?AlignmentType.CENTER:AlignmentType.LEFT,bold:j===2&&i>0,color:(j===3&&i>0&&String(c).includes("★★★"))?"DC2626":undefined}))}));
  children.push(makeTable(ew,er));
} else children.push(p("(1개월 이벤트 없음)"));
children.push(p(""));
children.push(h("2.2 중장기 1개월~1년 (★★★만)",2));
if (data.news && Array.isArray(data.news.events_calendar_longterm) && data.news.events_calendar_longterm.length) {
  const lw=[1500,1200,3000,3660];
  const lr=[["날짜","지역","이벤트","예상 영향"],...data.news.events_calendar_longterm.map(e=>[e.date??"-",e.region??"-",e.event??"-",e.expected_impact??"-"])].map((r,i)=>new TableRow({children:r.map((c,j)=>cell(c,{width:lw[j],header:i===0,alt:i>0&&i%2===0,align:(j===0||j===1)?AlignmentType.CENTER:AlignmentType.LEFT,bold:j===2&&i>0}))}));
  children.push(makeTable(lw,lr));
  children.push(p("※ 중장기는 ★★★만 수록. 미확정은 (예정) 표기.",{italics:true,color:"94A3B8",size:18}));
} else children.push(p("(중장기 이벤트 없음)"));

children.push(new Paragraph({children:[new PageBreak()]}));
children.push(h("3. 글로벌 증시 단·중·장기 추세",1));
children.push(p("각 시장의 1주/1개월/3개월/6개월/1년 변화율로 추세·모멘텀을 평가한다.",{italics:true,color:"64748B"}));
const tw=[1700,1300,1100,1100,1100,1100,1100,1700];
function trendRow(name,m,i){ return new TableRow({children:[
  cell(name,{width:1700,alt:i%2===1,bold:true}),
  cell(fmtNum(m&&m.current),{width:1300,alt:i%2===1,align:AlignmentType.RIGHT}),
  cell(fmtPct(m&&m['1w_pct']),{width:1100,alt:i%2===1,align:AlignmentType.RIGHT,color:pctColor(m&&m['1w_pct'])}),
  cell(fmtPct(m&&m['1mo_pct']),{width:1100,alt:i%2===1,align:AlignmentType.RIGHT,color:pctColor(m&&m['1mo_pct'])}),
  cell(fmtPct(m&&m['3mo_pct']),{width:1100,alt:i%2===1,align:AlignmentType.RIGHT,color:pctColor(m&&m['3mo_pct'])}),
  cell(fmtPct(m&&m['6mo_pct']),{width:1100,alt:i%2===1,align:AlignmentType.RIGHT,color:pctColor(m&&m['6mo_pct'])}),
  cell(fmtPct(m&&m['1y_pct']),{width:1100,alt:i%2===1,align:AlignmentType.RIGHT,color:pctColor(m&&m['1y_pct'])}),
  cell((m&&m.trend)||"-",{width:1700,alt:i%2===1})]}); }
function trendHeaderRow(){ return new TableRow({children:["지수","현재치","1주","1개월","3개월","6개월","1년","추세 평가"].map((x,i)=>cell(x,{width:tw[i],header:true,align:AlignmentType.CENTER}))}); }
function renderMarketBlock(title,obj,labels){ if(!obj)return; children.push(h(title,2)); const rows=[trendHeaderRow()]; let i=0;
  for(const [k,v] of Object.entries(obj)){ rows.push(trendRow((labels&&labels[k])||k.toUpperCase(),v,i)); i++; } children.push(makeTable(tw,rows)); children.push(p("")); }
if (data.markets) {
  renderMarketBlock("3.1 한국 증시",data.markets.korea,{kospi:"코스피",kosdaq:"코스닥"});
  renderMarketBlock("3.2 미국 증시",data.markets.us_markets,{sp500:"S&P 500",nasdaq:"나스닥",dow:"다우",vix:"VIX (공포지수)",dxy:"달러지수 DXY",us10y:"美 10년 국채"});
  renderMarketBlock("3.3 아시아 증시",data.markets.asia_markets,{nikkei:"닛케이 225",shanghai:"상하이종합",hsi:"홍콩 항셍",sensex:"인도 센섹스",vietnam:"베트남 (VNM)"});
  renderMarketBlock("3.4 유럽 증시",data.markets.europe_markets,{stoxx50:"유로 스톡스 50",dax:"독일 DAX",ftse:"영국 FTSE 100"});
}
children.push(new Paragraph({children:[new PageBreak()]}));
children.push(h("4. 원자재 종합 - 에너지·금속·희토류·농산물",1));
if (data.commodities) {
  renderMarketBlock("4.1 에너지",data.commodities.energy,{wti:"WTI 원유",brent:"Brent 원유",natgas:"천연가스"});
  renderMarketBlock("4.2 금속·희토류",data.commodities.metals,{gold:"금",silver:"은",copper:"구리",platinum:"백금",rare_earth:"희토류 (REMX)"});
  renderMarketBlock("4.3 농산물",data.commodities.agriculture,{corn:"옥수수",soybean:"대두",wheat:"밀"});
  if(data.commodities.metals&&data.commodities.metals.rare_earth) children.push(p("※ 희토류는 선물 시세가 없어 VanEck REMX ETF 프록시 사용.",{italics:true,color:"94A3B8",size:18}));
  if(data.commodities.commentary){ children.push(h("4.4 원자재 종합 코멘트",2)); children.push(p(data.commodities.commentary)); }
}
children.push(new Paragraph({children:[new PageBreak()]}));
children.push(h("5. 주요 환율 단·중·장기 추세",1));
if (data.markets && data.markets.fx_markets) {
  children.push(p("환율 상승 = 원화 약세. DXY는 6개 주요통화 대비 달러 가치.",{italics:true,color:"64748B"}));
  const fl={usd_krw:"USD/KRW",eur_krw:"EUR/KRW",jpy_krw:"JPY/KRW (100엔)",cny_krw:"CNY/KRW",hkd_krw:"HKD/KRW"};
  const fr=[trendHeaderRow()]; let fi=0;
  for(const [k,v] of Object.entries(data.markets.fx_markets)){ fr.push(trendRow(fl[k]||k.toUpperCase(),v,fi)); fi++; }
  if(data.markets.us_markets&&data.markets.us_markets.dxy) fr.push(trendRow("달러인덱스 (DXY)",data.markets.us_markets.dxy,fi));
  children.push(makeTable(tw,fr));
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
  if (c.fear_greed) { children.push(h("6.2 공포 & 탐욕 지수",2)); const fg=c.fear_greed;
    const band=v=>{const n=Number(v);if(isNaN(n))return null;
      if(n<=24)return{cls:"극단적 공포",color:"991B1B",fill:"FEE2E2"};
      if(n<=45)return{cls:"공포",color:"C2410C",fill:"FFEDD5"};
      if(n<=54)return{cls:"중립",color:"475569",fill:"F1F5F9"};
      if(n<=75)return{cls:"탐욕",color:"15803D",fill:"DCFCE7"};
      return{cls:"극단적 탐욕",color:"166534",fill:"BBF7D0"};};
    const pts=[["현재",fg.current,fg.classification],["1일 전",fg.yesterday,null],["1주 전",fg.last_week,null],
      ["1개월 전",fg.last_month,fg.last_month_cls],["3개월 전",fg.last_3month,fg.last_3month_cls],
      ["6개월 전",fg.last_6month,fg.last_6month_cls],["1년 전",fg.last_year,fg.last_year_cls]];
    const fgw=[1700,1300,2700,3660];
    const fgRows=[new TableRow({children:["시점","지수","분류 (단계)",`현재(${fg.current??"-"}) 대비`].map((x,i)=>cell(x,{width:fgw[i],header:true,align:AlignmentType.CENTER}))})];
    pts.forEach((pt,i)=>{const [label,val,clsGiven]=pt; const b=band(val); const clsText=clsGiven||(b?b.cls:"-");
      let deltaRuns;
      if(i===0){ deltaRuns=[cellRun("기준 (오늘)",{size:20,color:"64748B"})]; }
      else{ const c0=Number(fg.current),pv=Number(val);
        if(isNaN(c0)||isNaN(pv)){ deltaRuns=[cellRun("-",{size:20})]; }
        else{ const d=c0-pv; const txt=d===0?"±0p — 변화 없음":`${d>0?"+":""}${d}p ${d>0?"▲ 공포 완화 (탐욕 쪽으로)":"▼ 공포 심화 (공포 쪽으로)"}`;
          deltaRuns=[cellRun(txt,{size:20,bold:d!==0,color:d>0?positiveColor:d<0?negativeColor:"64748B"})]; } }
      fgRows.push(new TableRow({children:[
        cell(label,{width:fgw[0],align:AlignmentType.CENTER,bold:true}),
        cell(String(val??"-"),{width:fgw[1],align:AlignmentType.CENTER,bold:true,color:b?b.color:undefined}),
        cell(clsText,{width:fgw[2],align:AlignmentType.CENTER,bold:true,color:b?b.color:undefined,fill:b?b.fill:undefined}),
        cell("",{width:fgw[3],align:AlignmentType.CENTER,runs:deltaRuns})]})); });
    children.push(makeTable(fgw,fgRows));
    children.push(p("※ 지수 범위 0~100 (alternative.me 기준): 0~24 극단적 공포 · 25~45 공포 · 46~54 중립 · 55~75 탐욕 · 76~100 극단적 탐욕 — 분류 칸 배경색이 이 5단계를 나타낸다. '현재 대비'는 [현재 지수 − 해당 시점 지수]로, +면 그때보다 탐욕 쪽(공포 완화), −면 공포 쪽(심리 위축)으로 이동했다는 뜻이다. 예: 1개월 전 49(중립) → 현재 12(극단적 공포)면 −37p ▼.",{italics:true,color:"94A3B8",size:18})); }
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
children.push(h("7. 한국 5대 증권사 리서치",1));
const secLabels={shinhan:"신한투자증권",miraeasset:"미래에셋증권",samsung:"삼성증권",korea_inv:"한국투자증권",kiwoom:"키움증권"};
const secVF={shinhan:["asset_allocation_view","자산배분 시각"],miraeasset:["etf_emerging_view","ETF·신흥국 시각"],samsung:["derivatives_view","파생·선물 시각"],korea_inv:["ib_china_view","IB·중국 시각"],kiwoom:["global_etf_view","글로벌 ETF·신흥국 시각"]};
if (data.securities) { let idx=0;
  for(const key of Object.keys(secLabels)){ const sec=data.securities[key]; if(!sec)continue; idx++;
    children.push(h(`7.${idx} ${secLabels[key]}`,2));
    if(sec.strength) children.push(p(`핵심 강점: ${sec.strength}`,{bold:true,color:"1E40AF"}));
    if(Array.isArray(sec.channels)&&sec.channels.length) children.push(p(`주요 채널: ${sec.channels.join(' / ')}`,{italics:true,color:"475569"}));
    if(sec.key_message) children.push(p(`오늘의 메시지: ${sec.key_message}`));
    const vf=secVF[key]; if(vf&&sec[vf[0]]) children.push(p(`${vf[1]}: ${sec[vf[0]]}`,{color:"0F766E"}));
    if(Array.isArray(sec.key_reports)&&sec.key_reports.length){ children.push(p("대표 리포트:",{bold:true,after:40})); sec.key_reports.forEach(r=>children.push(reportBullet(r))); }
    else children.push(p("(리포트 수집 실패 - 사이트 접근 제한)",{italics:true,color:"94A3B8"})); }
  if(Array.isArray(data.securities.common_themes)&&data.securities.common_themes.length){ children.push(h("7.6 5사 공통 핵심 주제",2)); data.securities.common_themes.forEach(t=>children.push(bullet(t))); }
  if(data.securities.investor_type_recommendation){ children.push(h("7.7 투자자 유형별 추천 조합",2)); const rec=data.securities.investor_type_recommendation;
    const rm=[["장기 자산배분형",rec.long_term_allocator],["해외주식 종목 픽킹",rec.overseas_stock_picker],["단기 트레이더",rec.short_term_trader],["ETF·패시브 투자자",rec.etf_passive],["중국 집중 투자자",rec.china_focused]];
    children.push(makeTable([2800,6560],[["유형","추천 조합"],...rm].map((r,i)=>new TableRow({children:r.map((cc,j)=>cell(cc||"-",{width:[2800,6560][j],header:i===0,alt:i>0&&i%2===0,bold:j===0&&i>0}))})))); }
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
    if(sec.key_message) children.push(p(`오늘의 메시지: ${sec.key_message}`));
    const vf=gVF[key]; if(vf&&sec[vf[0]]) children.push(p(`${vf[1]}: ${sec[vf[0]]}`,{color:"0F766E"}));
    if(Array.isArray(sec.key_reports)&&sec.key_reports.length){ children.push(p("대표 발간물:",{bold:true,after:40})); sec.key_reports.forEach(r=>children.push(reportBullet(r))); }
    else children.push(p("(수집 실패 또는 비공개)",{italics:true,color:"94A3B8"})); }
  if(Array.isArray(data.global_securities.common_themes)&&data.global_securities.common_themes.length){ children.push(h("8.6 글로벌 IB 공통 핵심 주제",2)); data.global_securities.common_themes.forEach(t=>children.push(bullet(t))); }
  if(data.global_securities.wall_street_consensus){ children.push(h("8.7 월가 컨센서스",2)); children.push(p(data.global_securities.wall_street_consensus)); }
  children.push(p("※ 해외 IB 원문은 고객 전용 — 공개 Insights·언론 보도 기반 요약입니다.",{italics:true,color:"94A3B8",size:18}));
} else children.push(p("(글로벌 IB 데이터 없음)"));
children.push(new Paragraph({children:[new PageBreak()]}));
children.push(h("9. 종합 분석 - 매크로·테마·리스크",1));
children.push(p("※ 이하 9~12장은 앞 장 데이터에 근거한 AI 의견이며 투자 권유가 아닙니다.",{italics:true,color:"B45309",size:18}));
if (data.analysis) { const a=data.analysis;
  if(a.macro_view){ children.push(h("9.1 매크로 톤",2)); children.push(p(a.macro_view)); }
  if(Array.isArray(a.key_themes)&&a.key_themes.length){ children.push(h("9.2 핵심 테마",2)); const th=[["테마","방향","코멘트"]]; a.key_themes.forEach(t=>th.push([t.theme||"-",t.direction||"-",t.comment||"-"]));
    children.push(makeTable([2400,1400,5560],th.map((r,i)=>new TableRow({children:r.map((cc,j)=>cell(cc,{width:[2400,1400,5560][j],header:i===0,alt:i>0&&i%2===0,bold:(j===0||j===1)&&i>0,align:j===1?AlignmentType.CENTER:AlignmentType.LEFT}))})))); }
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
  data.analysis.action_items.forEach(it=>children.push(bullet(it)));
}
children.push(new Paragraph({children:[new PageBreak()]}));
children.push(h("13. 주의 사항 및 출처",1));
children.push(p("본 보고서는 Claude AI Research가 공개 데이터(Yahoo Finance, CoinGecko, 한국경제, 5대 증권사·글로벌 IB 공개 리서치 등)를 자동 수집·종합해 생성한 참고용 자료입니다.",{italics:true}));
children.push(p("자동 생성(AI) 특성상 오류·환각이 포함될 수 있습니다. 1~8장은 출처 링크로 검증 가능하며, 9~12장은 AI 의견입니다.",{italics:true,color:"B45309"}));
children.push(p("어떤 내용도 매수·매도 권유나 보장 수익을 약속하지 않으며, 투자 판단의 최종 책임은 이용자에게 있습니다.",{italics:true,color:"64748B"}));
children.push(p(""));
const genAt=(data.metadata&&data.metadata.generated_at)?String(data.metadata.generated_at):"-";
children.push(p(`데이터 기준일: ${reportDate}  |  보고서 생성시각: ${genAt}`,{size:18,color:"64748B"}));
children.push(p("주요 출처: Yahoo Finance / CoinGecko / 한국경제 / 신한·미래에셋·삼성·한국투자·키움 / UBS·GS·JPM·MS·BlackRock 공개 채널",{size:18,color:"94A3B8"}));

const doc=new Document({ ...(embedFontData?{fonts:[{name:FONT,data:embedFontData}]}:{}),
  styles:{ default:{document:{run:{font:FONT,size:22}}},
  paragraphStyles:[
    {id:"Heading1",name:"Heading 1",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:36,bold:true,font:FONT,color:"1E3A8A"},paragraph:{spacing:{before:360,after:200},outlineLevel:0}},
    {id:"Heading2",name:"Heading 2",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:28,bold:true,font:FONT,color:"1E40AF"},paragraph:{spacing:{before:240,after:140},outlineLevel:1}},
    {id:"Heading3",name:"Heading 3",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:24,bold:true,font:FONT,color:"334155"},paragraph:{spacing:{before:180,after:100},outlineLevel:2}}]},
  numbering:{config:[{reference:"bullets",levels:[{level:0,format:LevelFormat.BULLET,text:"•",alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:720,hanging:360}}}}]}]},
  sections:[{ properties:{page:{size:{width:12240,height:15840},margin:{top:1080,right:1080,bottom:1080,left:1080}}},
    headers:{default:new Header({children:[new Paragraph({alignment:AlignmentType.RIGHT,children:[new TextRun({text:`글로벌 금융시장 종합 시황 보고서 | ${reportDate}`,size:18,color:"64748B"})]})]})},
    footers:{default:new Footer({children:[new Paragraph({alignment:AlignmentType.CENTER,children:[new TextRun({text:"Page ",size:18,color:"64748B"}),new TextRun({children:[PageNumber.CURRENT],size:18,color:"64748B"}),new TextRun({text:" / ",size:18,color:"64748B"}),new TextRun({children:[PageNumber.TOTAL_PAGES],size:18,color:"64748B"}),new TextRun({text:"  |  v3.4.2",size:18,color:"64748B"})]})]})},
    children }] });
Packer.toBuffer(doc).then(buffer=>{ fs.mkdirSync(path.dirname(outPath),{recursive:true}); fs.writeFileSync(outPath,buffer);
  console.log(`✅ 보고서 생성 완료: ${outPath}`); console.log(`   크기: ${(buffer.length/1024).toFixed(1)} KB / 표 ${tableCount}개`);
}).catch(e=>{ console.error("❌ DOCX 생성 실패: "+e.message); process.exit(1); });
// EOF — namoobi-market-report v3.4.2 (VM-safe compact build; +한글폰트 임베드(미리보기 깨짐 방지), 공포탐욕 5단계 색상·현재대비 변화 설명)
