#!/usr/bin/env python3
# fetch_appc.py — [부록C] AI 반도체 밸류체인 46종 (미국 31·일본 4·한국 11) — v3.51 신설, v3.52.1 ORCL·이수페타시스·AMKR 추가
# sandbox·stdlib·스레드 병렬(Phase 1 bash tool-call). 야후 일봉 2y → nmr_appc.json(그룹별 rows)+nmr_appc_series.json(1Y 스파크).
# 멤버십 변경 시 ROWS 갱신. 추정 금지 — 이력 없으면 '-'(비차단).
import urllib.request, urllib.parse, json, datetime as dt, concurrent.futures as cf, os, sys
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"}
OUT=sys.argv[1] if len(sys.argv)>1 else "."
# (그룹, yahoo심볼, 이름, 설명)
ROWS=[
 ("빅테크 수요처","GOOGL","Alphabet","TPU·클라우드 AI 수요처"),
 ("빅테크 수요처","MSFT","Microsoft","AI 소프트웨어·클라우드 핵심"),
 ("빅테크 수요처","AMZN","Amazon","AWS 기반 AI 인프라 핵심"),
 ("빅테크 수요처","META","Meta Platforms","AI 추천·광고·데이터센터 투자 핵심"),
 ("빅테크 수요처","ORCL","Oracle","OCI AI CAPEX를 대표하는 대형 엔터프라이즈·클라우드 수요처"),
 ("팹리스/가속기","NVDA","NVIDIA","AI 가속기 절대 강자"),
 ("팹리스/가속기","AMD","Advanced Micro Devices","엔비디아 대안 GPU 및 데이터센터 축"),
 ("팹리스/가속기","AVGO","Broadcom","AI 네트워크와 맞춤형 ASIC 핵심"),
 ("팹리스/가속기","MRVL","Marvell Technology","데이터센터 커넥티비티·커스텀 실리콘 강자"),
 ("팹리스/가속기","ARM","Arm Holdings","온디바이스 AI 설계 표준의 핵심"),
 ("팹리스/가속기","ANET","Arista Networks","AI 클러스터 스위칭·고속 네트워킹 핵심"),
 ("팹리스/가속기","CRDO","Credo Technology","AI 인터커넥트용 SerDes·리타이머 강자"),
 ("팹리스/가속기","ALAB","Astera Labs","PCIe·CXL 리타이머 — CRDO와 짝을 이루는 AI 인터커넥트 핵심"),
 ("파운드리/제조","TSM","Taiwan Semiconductor (TSMC)","AI칩 생산의 핵심 파운드리"),
 ("파운드리/제조","005930.KS","삼성전자 (Samsung Electronics)","메모리·파운드리 동시 보유 종합 반도체 기업"),
 ("파운드리/제조","INTC","Intel","파운드리 재도전과 턴어라운드 기대"),
 ("메모리","MU","Micron Technology","AI 메모리 HBM·DRAM 직접 수혜주"),
 ("메모리","000660.KS","SK하이닉스 (SK hynix)","HBM 최강 수혜주"),
 ("소재/부품","4063.T","신에츠화학 (Shin-Etsu Chemical)","초고순도 웨이퍼와 포토레지스트의 글로벌 최상위 소재 기업"),
 ("소재/부품","3436.T","섬코 (SUMCO)","실리콘 웨이퍼 글로벌 양강 — 신에츠와 짝을 이루는 소재 핵심"),
 ("전공정 장비","ASML","ASML Holding","EUV 노광장비의 핵심 병목 기업"),
 ("전공정 장비","AMAT","Applied Materials","반도체 장비 전반을 넓게 커버하는 대표주"),
 ("전공정 장비","LRCX","Lam Research","식각·증착 장비의 핵심 플레이어"),
 ("전공정 장비","KLAC","KLA Corporation","공정 검사·계측 장비의 대표주"),
 ("전공정 장비","8035.T","도쿄일렉트론 (Tokyo Electron)","전공정 장비의 글로벌 핵심 기업"),
 ("전공정 장비","SNPS","Synopsys","AI 칩 설계의 핵심 EDA 기업"),
 ("전공정 장비","CDNS","Cadence Design Systems","AI 칩 설계·검증 EDA 핵심 기업"),
 ("후공정/패키징","6857.T","어드반테스트 (Advantest)","AI 가속기·HBM 테스터 글로벌 양강 — 후공정 테스트 장비 핵심"),
 ("후공정/패키징","6146.T","디스코 (Disco)","HBM 적층 필수 그라인더·다이서 사실상 독점"),
 ("후공정/패키징","042700.KS","한미반도체","HBM 본딩 장비 대표주"),
 ("후공정/패키징","095340.KQ","ISC","테스트 소켓 핵심 기업"),
 ("후공정/패키징","058470.KQ","리노공업","고마진 테스트 소켓 강자"),
 ("후공정/패키징","353200.KS","대덕전자","서버·패키징 기판 강자"),
 ("후공정/패키징","007660.KS","이수페타시스","AI 서버 고다층 MLB의 직접 수혜주"),
 ("후공정/패키징","AMKR","Amkor Technology","글로벌 OSAT 대표주"),
 ("데이터센터 전력·인프라","VRT","Vertiv Holdings","데이터센터 전력·냉각·UPS의 핵심 전용 수혜주"),
 ("데이터센터 전력·인프라","ETN","Eaton","배전·전력관리의 글로벌 대표주"),
 ("데이터센터 전력·인프라","GEV","GE Vernova","발전·가스터빈·전력 인프라의 핵심 수혜주"),
 ("데이터센터 전력·인프라","CEG","Constellation Energy","원자력 기반 무탄소 전력 공급의 대표주"),
 ("데이터센터 전력·인프라","PWR","Quanta Services","송전망·전력망 구축의 핵심"),
 ("데이터센터 전력·인프라","NVT","nVent Electric","전력관리·열관리에서 강한 헤지형 전력기기주"),
 ("데이터센터 전력·인프라","VST","Vistra","전력공급/발전 측면의 직접 수혜"),
 ("데이터센터 전력·인프라","010120.KS","LS ELECTRIC","배전반·스마트그리드·전력기기의 국내 핵심"),
 ("데이터센터 전력·인프라","298040.KS","효성중공업","변압기·GIS·ESS로 고압 전력 안정화 핵심"),
 ("데이터센터 전력·인프라","267260.KS","HD현대일렉트릭","변압기 중심의 전력기기 대표 수혜주"),
 ("데이터센터 전력·인프라","034020.KS","두산에너빌리티","발전설비·원전·가스터빈의 대표주"),
]
def yfetch(sym):
    u=f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range=2y&interval=1d"
    d=json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=20))
    r=d["chart"]["result"][0]; ts=r.get("timestamp"); pts=[]
    if ts:
        cl=r["indicators"]["quote"][0]["close"]
        pts=[[dt.datetime.utcfromtimestamp(t).date().isoformat(),round(float(c),2)] for t,c in zip(ts,cl) if c is not None]
    return pts
def ret(series):
    pts=[(dt.date.fromisoformat(str(x[0])[:10]),float(x[1])) for x in series if x[1] is not None]
    if len(pts)<2: return {}
    pts.sort(); cur=pts[-1][1]; last=pts[-1][0]
    out={"current":round(cur,2)}
    for k,days in [("1w_pct",7),("1mo_pct",30),("3mo_pct",91),("6mo_pct",182),("1y_pct",365)]:
        tgt=last-dt.timedelta(days=days); cand=[p for p in pts if p[0]<=tgt]
        out[k]=round((cur/cand[-1][1]-1)*100,1) if cand and cand[-1][1] else None
    if len(pts)>=2 and pts[-2][1]:
        out["1d_pct"]=round((pts[-1][1]/pts[-2][1]-1)*100,2); out["chg"]=round(cur-pts[-2][1],2)
    if len(pts)>=3 and pts[-3][1]:
        out["prev_pct"]=round((pts[-2][1]/pts[-3][1]-1)*100,2)
    return out
def koTrend(r):
    y=r.get("1y_pct"); m3=r.get("3mo_pct"); m1=r.get("1mo_pct")
    if y is not None:
        s="강세" if y>0 else "약세"; t=f"1년 {y:+.0f}%"
        if m3 is not None: t+=f", 3개월 {m3:+.0f}%"+(" 가속" if (m3 or 0)>0 and y>0 else (" 조정" if (m3 or 0)<0 else ""))
        return t+f" ({s})"
    if m3 is not None: return f"3개월 {m3:+.0f}% "+("상승" if m3>=0 else "조정")+" (상장 후)"
    return "이력 부족"
def ccy(sym): return "JPY" if sym.endswith(".T") else ("KRW" if sym.endswith((".KS",".KQ")) else "USD")
def work(row):
    grp,sym,name,desc=row
    try:
        pts=yfetch(sym); r=ret(pts)
        r.update({"code":sym,"symbol":sym,"name":name,"desc":desc,"group":grp,"ccy":ccy(sym),"trend":koTrend(r)})
        ser=[p for p in pts if dt.date.fromisoformat(p[0])>=dt.date.today()-dt.timedelta(days=366)]
        return sym,grp,r,ser,None
    except Exception as e: return sym,grp,None,None,str(e)[:120]
GROUPS=[]
for g,_,_,_ in ROWS:
    if g not in GROUPS: GROUPS.append(g)
out={"groups":GROUPS,"rows":{g:[] for g in GROUPS},"asof":dt.date.today().isoformat()}
series={}; errs=[]
order={r[1]:i for i,r in enumerate(ROWS)}
with cf.ThreadPoolExecutor(max_workers=12) as ex:
    for sym,grp,r,ser,err in ex.map(work,ROWS):
        if err or r is None: errs.append(f"{sym}:{err}"); continue
        out["rows"][grp].append(r)
        if ser: series[sym]=ser
for g in out["rows"]: out["rows"][g].sort(key=lambda r:order[r["code"]])
json.dump(out,open(os.path.join(OUT,"nmr_appc.json"),"w"),ensure_ascii=False,indent=1)
json.dump(series,open(os.path.join(OUT,"nmr_appc_series.json"),"w"),ensure_ascii=False)
n=sum(len(v) for v in out["rows"].values())
def pc(v): return "   -  " if v is None else f"{v:+6.1f}"
for g in GROUPS:
    print(f"◆ {g}")
    for r in out["rows"][g]:
        print(f"  {r['code']:10s} {r['name'][:20]:20s} {(r.get('current') or 0):>11,.2f} {pc(r.get('prev_pct'))} {pc(r.get('1w_pct'))} {pc(r.get('1mo_pct'))} {pc(r.get('3mo_pct'))} {pc(r.get('6mo_pct'))} {pc(r.get('1y_pct'))}")
print(f"총 {n}/39 · series {len(series)} · errs {errs}")
