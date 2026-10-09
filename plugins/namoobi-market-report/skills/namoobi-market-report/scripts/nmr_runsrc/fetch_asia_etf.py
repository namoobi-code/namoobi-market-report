#!/usr/bin/env python3
# fetch_asia_etf.py — 3.4.1 아시아 주요 ETF (한국 상장) 시세·추세 수집
# sandbox·stdlib·스레드 병렬, Yahoo <code>.KS 일봉 2년. merge.py ret() 동일 산출.
# 야후에 ETF 이력이 없는 종목은 PROXY(기초지수)로 수익률·추세·스파크라인을 대체하고 현재가는 ETF 실값 유지.
# 출력: nmr_asia_etf.json (그룹별 rows) + nmr_asia_etf_series.json (스파크라인 {code:[[date,close]..]})
import urllib.request, urllib.parse, json, datetime as dt, concurrent.futures as cf, sys, os
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"}
OUT = sys.argv[1] if len(sys.argv) > 1 else "."

# code: (group, name, desc)  — 그룹 순서: asia/china/japan/taiwan/india/vietnam
ASIA_ETF = {
 "277540": ("asia",  "ACE 아시아TOP50S&P",          "한국·대만·홍콩·싱가포르 아시아 핵심 대형주 통합 대표(S&P Asia 50)"),
 "192090": ("china", "TIGER 차이나CSI300",           "중국 본토 대형주 300(상하이·선전 A주)"),
 "099140": ("china", "KODEX 차이나H",                "본토 기업의 홍콩 상장주(H주·HSCEI)"),
 "371160": ("china", "TIGER 차이나항셍테크",          "중국 빅테크(항셍테크)"),
 "414780": ("china", "TIGER 차이나과창판STAR50(합성)", "중국 기술·혁신주(과창판 STAR50)"),
 "256750": ("china", "KODEX 차이나심천ChiNext(합성)",  "중국 성장주·창업판(선전 ChiNext)"),
 "0053L0": ("china", "TIGER 차이나휴머노이드로봇",     "중국 휴머노이드 로봇 순수 테마(유비테크·회천기술 등, 2025-05 상장)"),  # (2026-07-17 추가)
 "0162L0": ("china", "KODEX 차이나AI반도체TOP10",      "중국 AI 반도체 밸류체인 TOP10(하이곤·캠브리콘 등, 2026-02-26 상장)"),  # (2026-07-17 추가)
 "0164G0": ("china", "RISE 차이나AI반도체TOP4Plus",    "중국 AI칩·파운드리·광모듈·장비 15종(SMIC·나우라·이노라이트 등, 2026-03-10 상장)"),  # (2026-07-17 추가)
 "241180": ("japan", "TIGER 일본니케이225",           "일본 대형주(닛케이225·가격가중)"),
 "101280": ("japan", "KODEX 일본TOPIX100",           "일본 시총가중 대표(TOPIX100)—밸류업 수혜 금융·내수"),
 "465660": ("japan", "TIGER 일본반도체FACTSET",       "일본 반도체 소부장(소재·부품·장비)"),
 "253990": ("taiwan","TIGER 대만TAIEX파생(H)",        "대만 전체시장 대표(가권지수·환헤지)"),
 "453950": ("taiwan","TIGER TSMC밸류체인FACTSET",     "대만 반도체 핵심 밸류체인(TSMC·파운드리·팹리스)"),
 "453870": ("india", "TIGER 인도니프티50",            "인도 대형 금융·IT·소비주(Nifty50)"),
 "479730": ("india", "TIGER 인도빌리언컨슈머",         "인도 핵심 소비재 B2C 20종(자동차·럭셔리·생필품)"),
 "245710": ("vietnam","ACE 베트남VN30(합성)",         "베트남 호치민 성장 신흥시장(VN30)"),
 # (v3.50) 미국거래소 상장 아시아 국가·테마 ETF 15종 — 같은 나라 그룹에 병합(국내상장 뒤), 달러 종가($). key=미국 티커.
 "MCHI": ("china", "중국 본토/대형주",  "중국 대형·중형주를 넓게 담는 대표 코어 ETF (iShares MSCI China)"),
 "FXI":  ("china", "중국 대형주",      "정책·국유 대형주·본토 대형 흐름을 보기 좋음 (iShares China Large-Cap)"),
 "KWEB": ("china", "중국 인터넷/플랫폼", "중국 기술·플랫폼 성장에 직접 베팅하는 테마 ETF (KraneShares CSI China Internet)"),
 "EWH":  ("china", "홍콩",           "중국 본토보다 금융·부동산·중국 경유 노출 성격 (iShares MSCI Hong Kong)"),
 "KOID": ("china", "글로벌 휴머노이드 로봇", "미·중·일 휴머노이드·피지컬AI 밸류체인 (KraneShares KOID, 2025-06 상장)"),  # (2026-07-17 추가)
 "EWJ":  ("japan", "일본",           "일본 주식시장 전체를 넓게 담는 가장 무난한 코어 (iShares MSCI Japan)"),
 "DXJ":  ("japan", "일본(환헤지 성격)",  "엔화 약세 환경에서 환율 리스크를 줄여보는 선택지 (WisdomTree Japan Hedged Equity)"),
 "EWT":  ("taiwan","대만",           "AI 반도체 밸류체인에 직접 연결되는 핵심 아시아 노출 (iShares MSCI Taiwan)"),
 "INDA": ("india", "인도",           "소비·인프라·제조업 이전이 겹치는 장기 성장 핵심 (iShares MSCI India)"),
 "VNM":  ("vietnam","베트남",         "베트남 시장에 가장 오래된 대표 노출 ETF 중 하나 (VanEck Vietnam)"),
 "VNAM": ("vietnam","베트남",         "MSCI Vietnam 계열로 베트남을 더 타깃하게 담는 선택지 (Global X MSCI Vietnam)"),
 "EIDO": ("sea",   "인도네시아",        "인구 규모·자원·내수·니켈 테마까지 같이 볼 수 있음 (iShares MSCI Indonesia)"),
 "EPHE": ("sea",   "필리핀",          "젊은 인구와 도시화 기반의 동남아 소비 성장 노출 (iShares MSCI Philippines)"),
 "EWM":  ("sea",   "말레이시아",        "반도체 후방 공급망과 제조업 베이스가 강점 (iShares MSCI Malaysia)"),
 "THD":  ("sea",   "태국",           "관광·소비·리오프닝 성격이 강한 동남아 위성 포지션 (iShares MSCI Thailand)"),
 "EWS":  ("sea",   "싱가포르",         "성장성보다는 금융·물류·안정성 중심의 허브 노출 (iShares MSCI Singapore)"),
}
GROUP_ORDER = ["asia", "china", "japan", "taiwan", "india", "vietnam", "sea"]  # (v3.50) sea=동남아(미국상장)
# 야후 ETF 캔들 이력 미제공 → 기초지수로 수익률·추세·스파크라인 대체(현재가는 ETF 실값 유지)
PROXY = {"253990": ("^TWII", "기초지수 TAIEX(대만 가권지수) 기준")}

def fetch_series(ysym):
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ysym)}?range=2y&interval=1d"
    d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=15))
    r = d["chart"]["result"][0]; meta = r.get("meta", {})
    ts = r.get("timestamp"); pts = []
    if ts:
        cl = r["indicators"]["quote"][0]["close"]
        pts = [[dt.datetime.utcfromtimestamp(t).date().isoformat(), round(float(c),2)] for t,c in zip(ts,cl) if c is not None]
    ft = meta.get("firstTradeDate")
    first = dt.datetime.utcfromtimestamp(ft).date().isoformat() if ft else None
    return pts, meta, first

def ret(series):
    pts = [(dt.date.fromisoformat(str(x[0])[:10]), float(x[1])) for x in series if x[1] is not None]
    if len(pts) < 2: return {}
    pts.sort(); cur = pts[-1][1]; last = pts[-1][0]
    out = {"current": round(cur, 2)}
    for k, days in [("1w_pct",7),("1mo_pct",30),("3mo_pct",91),("6mo_pct",182),("1y_pct",365)]:
        tgt = last - dt.timedelta(days=days); cand = [p for p in pts if p[0] <= tgt]
        out[k] = round((cur/cand[-1][1]-1)*100, 1) if cand and cand[-1][1] else None
    if len(pts) >= 2 and pts[-2][1]:
        out["1d_pct"]=round((pts[-1][1]/pts[-2][1]-1)*100,2); out["chg"]=round(cur-pts[-2][1],2); out["prev_close"]=round(pts[-2][1],2)
    if len(pts) >= 3 and pts[-3][1]:
        out["prev_pct"]=round((pts[-2][1]/pts[-3][1]-1)*100,2)
    return out

def koTrend(r):
    y=r.get("1y_pct"); m3=r.get("3mo_pct"); m1=r.get("1mo_pct")
    if y is not None:
        s="강세" if y>0 else "약세"; t=f"1년 {y:+.0f}%"
        if m3 is not None: t+=f", 3개월 {m3:+.0f}%"+(" 가속" if (m3 or 0)>0 and y>0 else (" 조정" if (m3 or 0)<0 else ""))
        return t+f" ({s})"
    if m3 is not None: return f"3개월 {m3:+.0f}% "+("상승" if m3>=0 else "조정")+" (상장 후)"
    if m1 is not None: return f"1개월 {m1:+.0f}% "+("반등" if m1>=0 else "조정")+" (상장 후)"
    return "상장 초기"

def daum_series(code):
    # (fix v3.48) Yahoo 가 한국상장 ETF 이력을 안 줄 때 finance.daum.net 일봉으로 대체
    try:
        u = "https://finance.daum.net/api/charts/A%s/days?limit=520&adjusted=true" % code
        req = urllib.request.Request(u, headers={"Referer": "https://finance.daum.net/quotes/A%s" % code,
                                                 "User-Agent": UA["User-Agent"], "X-Requested-With": "XMLHttpRequest"})
        d = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "replace")).get("data", [])
        out = []
        for p in d:
            tp = p.get("tradePrice")
            if not tp: continue
            out.append([str(p.get("date"))[:10], round(float(tp), 2)])
        out.sort()
        return out
    except Exception:
        return []

def work(item):
    code,(grp,name,desc)=item
    is_us = code.isalpha()              # (v3.50→2026-07-17 fix) 한국 신종목코드는 영숫자 혼합(0053L0 등)이라 isdigit 판별이 깨짐 — 미국 티커=전부 알파벳
    try:
        pts, meta, first = fetch_series(code if is_us else code+".KS")
        cur = meta.get("regularMarketPrice")
        proxy = PROXY.get(code)
        if proxy and len(pts) < 2:
            psym, pnote = proxy
            ppts, _, _ = fetch_series(psym)
            r = ret(ppts)
            if cur is not None: r["current"] = round(float(cur), 2)   # ETF 실 현재가 유지
            r.pop("chg", None); r.pop("prev_close", None)             # 지수 절대변동은 ₩가격과 무의미 → 제거
            series = ppts
            desc = desc + " · 수익률·추세=" + pnote + "(야후 ETF 이력 미제공)"
        else:
            if len(pts) < 2 and not is_us:         # (fix v3.48) Yahoo ETF 이력 미제공 → Daum 일봉 폴백(국내 전용)
                dpts = daum_series(code)
                if len(dpts) >= 2:
                    pts = dpts
                    desc = desc + " · 추세=Daum 일봉(야후 ETF 이력 미제공)"
            r = ret(pts); series = pts
        r.update({"code":code,"symbol":code,"name":name,"desc":desc,"weight":None,"listed":first,
                  "ccy":("USD" if is_us else "KRW"),
                  "yahoo_name":meta.get("longName") or meta.get("shortName") or ""})
        r["trend"]=koTrend(r)
        return code,grp,r,series,None
    except Exception as e:
        return code,grp,None,None,str(e)[:120]

groups={g:[] for g in GROUP_ORDER}; series={}; rows_flat=[]
with cf.ThreadPoolExecutor(max_workers=10) as ex:
    for code,grp,r,pts,err in ex.map(work, ASIA_ETF.items()):
        if err or r is None: print(f"ERR {code}: {err}"); continue
        groups[grp].append(r)
        if pts: series[code]=pts
        rows_flat.append(r)
order={c:i for i,c in enumerate(ASIA_ETF)}
for g in groups: groups[g].sort(key=lambda r: order[r["code"]])
# (v3.50) 한국상장/미국상장 분리 평균
kr=[r for r in rows_flat if r.get("ccy")!="USD"]; us=[r for r in rows_flat if r.get("ccy")=="USD"]
def _avg(rs):
    ys=[r["1y_pct"] for r in rs if r.get("1y_pct") is not None]
    return round(sum(ys)/len(ys),1) if ys else None
avg=_avg(rows_flat); kavg=_avg(kr); uavg=_avg(us)
comment=(f"아시아 국가·테마 ETF {len(rows_flat)}종 — 한국 상장 {len(kr)}종 1년 평균 {kavg:+.1f}%, 미국 상장($) {len(us)}종 1년 평균 {uavg:+.1f}%. "
         f"합성·환헤지(H)·신규 상장 ETF는 기초시장과 괴리가 있을 수 있고, 달러 기준 수익률은 원화 환산과 다르게 반영되며, 야후 이력 미제공 종목은 기초지수로 수익률을 대체한다."
         if (kavg is not None and uavg is not None) else f"아시아 국가·테마 ETF {len(rows_flat)}종.")
asof=dt.date.today().isoformat(); out={"asof":asof,"comment":comment}; out.update(groups)
os.makedirs(OUT,exist_ok=True)
json.dump(out, open(os.path.join(OUT,"nmr_asia_etf.json"),"w"), ensure_ascii=False, indent=1)
json.dump(series, open(os.path.join(OUT,"nmr_asia_etf_series.json"),"w"), ensure_ascii=False)
def pc(v): return "   -  " if v is None else f"{v:+6.1f}"
print(f"{'code':6s} {'name':28s} {'현재가':>9s} {'1일':>7s} {'1주':>7s} {'1개월':>7s} {'3개월':>7s} {'6개월':>7s} {'1년':>7s}")
for g in GROUP_ORDER:
    for r in groups[g]:
        print(f"{r['code']:6s} {r['name'][:28]:28s} {(r.get('current') or 0):>9,.0f} {pc(r.get('prev_pct'))} {pc(r.get('1w_pct'))} {pc(r.get('1mo_pct'))} {pc(r.get('3mo_pct'))} {pc(r.get('6mo_pct'))} {pc(r.get('1y_pct'))}")
print(f"\n총 {len(rows_flat)}종 · 1년평균 {avg}% · series {len(series)}개 · asof {asof}")
