#!/usr/bin/env node
/* build_appendix_ef.js — [부록E·F] 피지컬 AI 밸류체인 예제 docx 빌더 (v3.72)
 *   build_report.js 와 동일한 스타일(폰트 임베드·표 폭·색)로 부록 2종만 렌더하는 검토용 샘플.
 *   입력: nmr_appe.json / charts/spark_e_*.png / charts/appf_physical_ai_{1..3}.png
 *   사용: node build_appendix_ef.js <workdir> [out.docx]
 */
const fs=require('fs'), path=require('path');
const docx=require('docx');
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, Header, Footer,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType, ShadingType, PageNumber, PageBreak, ImageRun } = docx;
const WORK=path.resolve(process.argv[2]||'.');
const OUT=process.argv[3]||path.join(WORK,'부록EF_피지컬AI_밸류체인_예제.docx');
process.chdir(WORK);
const E=JSON.parse(fs.readFileSync('nmr_appe.json','utf-8'));
const reportDate=new Date().toISOString().slice(0,10);

const fontCandidates=[process.env.NMR_FONT||'', path.join(WORK,'fonts','nmr_kr.ttf'),
  '/sessions/kind-affectionate-cori/mnt/claudeCowork/namoobi-market-report/plugins/namoobi-market-report/skills/namoobi-market-report/scripts/fonts/nmr_kr.ttf'].filter(Boolean);
let embedFontData=null; for(const fp of fontCandidates){ try{ if(fs.existsSync(fp)){ embedFontData=fs.readFileSync(fp); break; } }catch(e){} }
const FONT=embedFontData?"NanumBarunGothic":"맑은 고딕";

const border={style:BorderStyle.SINGLE,size:4,color:"9CA3AF"};
const borders={top:border,bottom:border,left:border,right:border};
const headerShading={fill:"1E40AF",type:ShadingType.CLEAR,color:"auto"};
const altShading={fill:"EFF6FF",type:ShadingType.CLEAR,color:"auto"};
const negativeColor="DC2626", positiveColor="059669";
const CONTENT_W=11160;
const children=[];
function fmtNum(v){ if(v===null||v===undefined||v==="")return "-"; const n=Number(v); if(isNaN(n))return String(v);
  if(Math.abs(n)>=1000)return n.toLocaleString(undefined,{maximumFractionDigits:2}); return n.toFixed(2); }
function fmtPct(v){ if(v===null||v===undefined||v==="")return "-"; const n=Number(v); if(isNaN(n))return String(v); return (n>=0?"+":"")+n.toFixed(2)+"%"; }
function pctColor(v){ if(v===null||v===undefined||v==="")return undefined; const n=Number(v); if(isNaN(n))return undefined; return n>=0?positiveColor:negativeColor; }
function fmtChgAbs(v){ if(v===null||v===undefined||v==="")return null; const n=Number(v); if(isNaN(n))return null; const a=Math.abs(n);
  return a>=1000?a.toLocaleString(undefined,{maximumFractionDigits:2}):(a>=1?a.toFixed(2):a.toFixed(3)); }
function day1pct(m){ if(!m)return null; if(m.prev_pct!==undefined&&m.prev_pct!==null)return m.prev_pct;
  return (m["1d_pct"]!==undefined&&m["1d_pct"]!==null&&m["1d_pct"]!=="")?m["1d_pct"]:null; }
function cellRun(text,opts={}){ return new TextRun({text:String(text),bold:opts.bold||opts.header,size:opts.size??20,color:opts.header?"FFFFFF":opts.color}); }
function cell(text,opts={}){ return new TableCell({ borders, width:{size:opts.width,type:WidthType.DXA},
  shading:opts.header?headerShading:(opts.alt?altShading:undefined), margins:{top:80,bottom:80,left:120,right:120},
  children:[new Paragraph({alignment:opts.align??AlignmentType.LEFT, children:opts.runs||[cellRun(text,opts)]})] }); }
function makeTable(cw,rows){ const t0=cw.reduce((a,b)=>a+b,0)||1; const k=CONTENT_W/t0;
  const cw2=cw.map(x=>Math.max(1,Math.round(x*k))); const total=cw2.reduce((a,b)=>a+b,0);
  return new Table({width:{size:total,type:WidthType.DXA},columnWidths:cw2,rows}); }
function p(text,opts={}){ return new Paragraph({ spacing:{after:opts.after??80,before:opts.before??0}, alignment:opts.align??AlignmentType.LEFT,
  children:[new TextRun({text:String(text),bold:opts.bold,size:opts.size??22,color:opts.color,italics:opts.italics})] }); }
function h(text,level){ const map={1:HeadingLevel.HEADING_1,2:HeadingLevel.HEADING_2,3:HeadingLevel.HEADING_3};
  return new Paragraph({ heading:map[level], spacing:{before:240,after:120}, children:[new TextRun({text,bold:true})] }); }
function imagePara(rel,w,hgt){ try{ if(w>=450){ const k=744/w; w=Math.round(w*k); hgt=Math.round(hgt*k); }
  if(fs.existsSync(rel)) return new Paragraph({alignment:AlignmentType.CENTER,spacing:{before:60,after:120},
    children:[new ImageRun({type:"png",data:fs.readFileSync(rel),transformation:{width:w,height:hgt}})]});
}catch(e){} return null; }
function imgCellSpark(rel,width,alt,w,hgt){ try{ if(rel&&fs.existsSync(rel))
  return new TableCell({borders,width:{size:width,type:WidthType.DXA},shading:alt?altShading:undefined,margins:{top:40,bottom:40,left:60,right:60},
    children:[new Paragraph({alignment:AlignmentType.CENTER,children:[new ImageRun({type:"png",data:fs.readFileSync(rel),transformation:{width:w||150,height:hgt||46}})]})]});
}catch(e){} return cell("-",{width,alt,align:AlignmentType.CENTER}); }
function curCellRuns(cur,m,opts){ opts=opts||{}; m=m||{};
  const curStr=(cur===null||cur===undefined||cur==="")?"-":((opts.prefix||"")+fmtNum(cur));
  const runs=[new TextRun({text:curStr,bold:true,size:20})];
  let pct=m['1d_pct']; pct=(pct===null||pct===undefined||pct==="")?null:Number(pct);
  let chg=m.chg; chg=(chg===null||chg===undefined||chg==="")?null:Number(chg);
  if((pct!==null&&!isNaN(pct))||(chg!==null&&!isNaN(chg))){
    const ref=(pct!==null&&!isNaN(pct))?pct:chg; const col=ref>=0?positiveColor:negativeColor; const arrow=ref>=0?"▲":"▼";
    let t=arrow; const a=(chg!==null&&!isNaN(chg))?fmtChgAbs(chg):null; if(a!==null)t+=" "+a;
    if(pct!==null&&!isNaN(pct))t+=" ("+(pct>=0?"+":"")+pct.toFixed(2)+"%)";
    runs.push(new TextRun({text:t,break:1,size:16,color:col,bold:true})); }
  return runs; }
const TR2=[1500,950,950,950,950,950,950,1500,1600]; const TR2TOT=TR2.reduce((a,b)=>a+b,0);
function trend2Header(){ return new TableRow({children:["현재가","1일","1주","1개월","3개월","6개월","1년","추세(1Y)","추세 평가"].map((x,i)=>cell(x,{width:TR2[i],header:true,align:AlignmentType.CENTER}))}); }
function trend2Rows(items){ const rows=[trend2Header()];
  items.forEach((it,i)=>{ const alt=i%2===1; const m=it.m||{};
    rows.push(new TableRow({children:[ new TableCell({borders,columnSpan:9,width:{size:TR2TOT,type:WidthType.DXA},
      shading:alt?altShading:undefined,margins:{top:70,bottom:30,left:120,right:120},children:[new Paragraph({children:it.desc})]}) ]}));
    rows.push(new TableRow({children:[
      cell("",{width:TR2[0],alt,align:AlignmentType.RIGHT,runs:curCellRuns(it.current,m,{prefix:it.curPrefix})}),
      cell(fmtPct(day1pct(m)),{width:TR2[1],alt,align:AlignmentType.RIGHT,color:pctColor(day1pct(m))}),
      cell(fmtPct(m['1w_pct']),{width:TR2[2],alt,align:AlignmentType.RIGHT,color:pctColor(m['1w_pct'])}),
      cell(fmtPct(m['1mo_pct']),{width:TR2[3],alt,align:AlignmentType.RIGHT,color:pctColor(m['1mo_pct'])}),
      cell(fmtPct(m['3mo_pct']),{width:TR2[4],alt,align:AlignmentType.RIGHT,color:pctColor(m['3mo_pct'])}),
      cell(fmtPct(m['6mo_pct']),{width:TR2[5],alt,align:AlignmentType.RIGHT,color:pctColor(m['6mo_pct'])}),
      cell(fmtPct(m['1y_pct']),{width:TR2[6],alt,align:AlignmentType.RIGHT,color:pctColor(m['1y_pct'])}),
      imgCellSpark(it.chart,TR2[7],alt,150,46),
      cell(it.trend||"-",{width:TR2[8],alt,size:16}) ]}));
  });
  return rows; }
function simpleTable(w,header,body,opts){ opts=opts||{}; const leftCols=opts.left||[header.length-1];
  const rows=[header,...body].map((r,i)=>new TableRow({children:r.map((c,j)=>cell(c,{width:w[j],header:i===0,alt:i>0&&i%2===0,
    bold:(j===0)&&i>0, align:leftCols.includes(j)?AlignmentType.LEFT:AlignmentType.CENTER}))}));
  children.push(makeTable(w,rows)); }

/* ───────── [부록E] 피지컬 AI 밸류체인 (글로벌 개별종목) ───────── */
const CCY={USD:"$",JPY:"¥",KRW:"₩",TWD:"NT$",CNY:"CN¥",HKD:"HK$",AUD:"A$"};
const GL="①②③④⑤⑥⑦⑧⑨⑩";
children.push(h("[부록E] 피지컬 AI 밸류체인 (글로벌 개별종목)",1));
children.push(p("생성형 AI가 화면 밖으로 걸어 나오는 '피지컬 AI'의 부품 생태계를 6개 단(段)으로 나눠 정리한다. 흐름은 완성체(휴머노이드 메이커)의 양산 계획 → 두뇌(파운데이션 모델·온디바이스 칩) → 신경·감각(센서) → 근육·관절(액추에이터) → 골격·에너지(경량소재·배터리) → 가상훈련장(시뮬레이터·데이터)로 이어진다. 접두 $=미국·¥=일본·₩=한국·NT$=대만·CN¥=중국·HK$=홍콩·A$=호주 종가 기준이며, 수익률은 일봉 종가 기준 가격수익률(배당 제외)이다. 비상장(피겨AI·애지봇·유니트리·1X·샤르파·보스턴다이내믹스·에이로봇 등)은 [부록F] 관계도에만 표기한다.",{italics:true,color:"64748B"}));
children.push(p("■ 시장 규모·구조 핵심 수치",{bold:true,color:"1E40AF",before:160,size:21}));
simpleTable([1750,3450,5960],
  ["항목","수치","내용 · 출처"],
  [["시장 규모","5조 달러 (2050년)","휴머노이드 유닛 10억 개 이상 보급 전망 — 모건스탠리"],
   ["글로벌 수요","209만대(2024) → 1329만대(2029) → 6억4800만대(2050)","딜로이트 및 각 기관 전망치"],
   ["2025년 생산량","중국 87.7% (1만2868대) · 미국 3.1% · 한국 1.2% · 기타 8.0%","국가별 생산 비중 — 골드만삭스"],
   ["출하 점유 1위","애지봇 5168대 · 점유 39% (2025년)","중국계 합산 세계 출하 비중 약 87% — 옴디아"],
   ["원가 구조","액추에이터(관절·근육) 30~60% (평균 40%) · 배터리 5~10%","1대당 액추에이터 25~30개 이상, 카메라 6대 이상 탑재"],
   ["전고체 배터리","16억 달러(2025) → 156.5억 달러(2033)","2026년부터 연평균 31.8% 성장 — 그랜드뷰리서치"],
   ["로봇 시뮬레이터","8.2억 달러(2025) → 30.9억 달러(2035)","연평균 14.2% — 프리시던스리서치"],
   ["기술 이정표","아틀라스 3700Wh·약 4시간 · 로봇 손 자유도 1X 25 / 샤르파 22 (인간 27)","테슬라 옵티머스 부품 1만 개 신규 공급망 구축 중"]],
  {left:[0,2]});
children.push(p("※ 시장 전망치는 기관 추정으로 실현을 보장하지 않으며, 생산·점유 통계는 발표 기관별 집계 기준이 달라 단순 비교가 어렵다.",{size:16,italics:true,color:"94A3B8"}));

let tot=0; const ys=[];
(E.groups||[]).forEach((g,gi)=>{ const arr=(E.rows||{})[g]; if(!Array.isArray(arr)||!arr.length)return;
  tot+=arr.length; arr.forEach(x=>{ if(x&&x["1y_pct"]!=null)ys.push(Number(x["1y_pct"])); });
  children.push(p((GL[gi]||"■")+" "+g+" ("+arr.length+"종)",{bold:true,color:"1E40AF",before:160,size:21}));
  const items=arr.map(x=>{ const sym=String(x.code||"-");
    return {desc:[new TextRun({text:(x.name||sym)+"  ["+sym+"]",bold:true,size:18,color:"1D4ED8"}),
                  new TextRun({text:(x.desc?("  — "+x.desc):""),size:15,color:"64748B"})],
      m:x, current:x.current, curPrefix:(CCY[x.ccy]||"$"),
      trend:String(x.trend||"-"), chart:"charts/spark_e_"+sym.replace(/\./g,"_")+".png"}; });
  children.push(makeTable(TR2,trend2Rows(items))); });
if(ys.length){ const a=ys.reduce((x,y)=>x+y,0)/ys.length;
  children.push(p("추세 평가: 피지컬 AI 밸류체인 "+tot+"종(1년 수익률 산출 "+ys.length+"종) 1년 평균 "+(a>=0?"+":"")+a.toFixed(1)+"%. 통화가 서로 달라 수익률은 현지통화 기준이며 환율 효과는 반영되지 않는다.",{bold:true,color:"0F766E",before:160})); }
if(E.asof)children.push(p("기준: "+E.asof+" · 구성 근거: 한경비즈니스 2026.08.05-11 커버스토리 '피지컬 AI 핵심 밸류체인' + 모건스탠리 2025 선정 핵심기업",{size:16,color:"94A3B8"}));

/* ───────── [부록F] 관계도(해자 지도) ───────── */
const imgs=[1,2,3].map(i=>{ const rel="charts/appf_physical_ai_"+i+".png"; return fs.existsSync(rel)?rel:null; });
if(imgs.some(Boolean)){
  children.push(new Paragraph({children:[new PageBreak()]}));
  children.push(h("[부록F] 피지컬 AI 밸류체인 관계도 (해자 지도)",1));
  children.push(p("[부록E] 개별종목이 '왜 중요한지'를 한 장의 흐름으로 정리한 관계도. 돈은 위(완성체의 양산 계획)에서 아래로 흐르고, 부품은 아래에서 위로 올라간다. 파란 배지=독점·준독점(대체재 사실상 없음), 황색 배지=과점·양강·선두, 회색 배지=비상장(직접 투자 불가·구조 이해용), ★=상위 단과 중복 표기. 시세와 무관한 구조 설명용 정적 이미지(구성 변경 시 assets/gen_appf_physical_ai.py 로 재생성).",{italics:true,color:"64748B"}));
  imgs.forEach((rel,k)=>{ if(!rel)return; const b=fs.readFileSync(rel);
    const W=b.readUInt32BE(16), H=b.readUInt32BE(20);
    const img=imagePara(rel,700,Math.round(700*H/Math.max(W,1)));
    if(img){ if(k>0)children.push(new Paragraph({children:[new PageBreak()]})); children.push(img); } });
  children.push(p("핵심: 하모닉드라이브·나브테스코(감속기) → 소니·헤사이(센서) → 엔비디아(두뇌 풀스택) → 완성체로 이어지는 사슬에서 병목은 '두뇌'가 아니라 '관절과 손'에 있다. 원가의 40%를 차지하는 액추에이터와 촉각 센서가 최종 승패를 가르며, 한국은 메모리(SK하이닉스)·배터리(LG엔솔·삼성SDI)·센서모듈(LG이노텍)·액추에이터(현대모비스·LG전자)에 걸쳐 있으나 반도체 두뇌와 정밀 감속기·센서에서는 후발이다.",{bold:true,color:"0F766E"}));
  children.push(p("리스크: ① 중국 편중(2025년 생산 87.7%)과 미국의 중국산 로봇 수입 차단(FCC 7/28) 등 정책 변수 ② 테슬라 옵티머스 등 양산 일정 지연 ③ 부품 단가 하락 압력. 본 부록은 산업 구조 이해용 참고자료이며 특정 종목의 매수·매도 권유가 아니다.",{size:18,color:"64748B"}));
}

const doc=new Document({ ...(embedFontData?{fonts:[{name:FONT,data:embedFontData}]}:{}),
  styles:{ default:{document:{run:{font:FONT,size:22}}},
  paragraphStyles:[
    {id:"Heading1",name:"Heading 1",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:36,bold:true,font:FONT,color:"1E3A8A"},paragraph:{spacing:{before:360,after:200},outlineLevel:0}},
    {id:"Heading2",name:"Heading 2",basedOn:"Normal",next:"Normal",quickFormat:true,run:{size:28,bold:true,font:FONT,color:"1E40AF"},paragraph:{spacing:{before:240,after:140},outlineLevel:1}}]},
  numbering:{config:[{reference:"bullets",levels:[{level:0,format:LevelFormat.BULLET,text:"•",alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:720,hanging:360}}}}]}]},
  sections:[{ properties:{page:{size:{width:12240,height:15840},margin:{top:1080,right:540,bottom:1080,left:540}}},
    headers:{default:new Header({children:[new Paragraph({alignment:AlignmentType.RIGHT,children:[new TextRun({text:`피지컬 AI 밸류체인 [부록E·F] 예제 | ${reportDate}`,size:18,color:"64748B"})]})]})},
    footers:{default:new Footer({children:[new Paragraph({alignment:AlignmentType.CENTER,children:[new TextRun({text:"Page ",size:18,color:"64748B"}),new TextRun({children:[PageNumber.CURRENT],size:18,color:"64748B"}),new TextRun({text:" / ",size:18,color:"64748B"}),new TextRun({children:[PageNumber.TOTAL_PAGES],size:18,color:"64748B"})]})]})},
    children }] });
Packer.toBuffer(doc).then(buf=>{ fs.writeFileSync(OUT,buf); console.log("OK "+(buf.length/1024).toFixed(1)+"KB → "+OUT); })
  .catch(e=>{ console.error("FAIL "+e.message); process.exit(1); });
