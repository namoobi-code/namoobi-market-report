#!/usr/bin/env python3
# fetch_semi.py (v3.7) — 한국 테마/반도체 종목·ETF 시계열 sandbox 수집 (Chrome 불필요, stdlib only).
# KoreaSemiThemeAgent 의 '느린 38종목 시계열 fetch' 대체(스레드 병렬). 선정·AUM·노트·테마 방향/코멘트는
# 여전히 KoreaSemiThemeAgent 가 nmr_semi.json 으로 제공(아래와 '정확히 같은 이름'). merge.py 가 이름 join.
# AUM 상위 멤버십 변동 시 에이전트가 플래그→이 목록 갱신.
# 산출: nmr_kr_series.json {themes:{}, stocks:{}, etfs:{}}  (각 [[YYYY-MM-DD, close], ...])
# 사용: python3 fetch_semi.py [WORK_DIR]
import json, urllib.request, datetime, time, sys, os
from concurrent.futures import ThreadPoolExecutor
if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
    os.chdir(sys.argv[1])
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
CUR_MONTH = datetime.date.today().strftime("%Y-%m")

def chart(ticker, rng, interval):
    for host in ("query1", "query2"):
        try:
            u = f"https://{host}.finance.yahoo.com/v8/finance/chart/{ticker}?range={rng}&interval={interval}"
            j = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=25).read().decode('utf-8', 'replace'))
            res = j.get("chart", {}).get("result")
            if res: return res[0]
        except Exception:
            time.sleep(0.5)
    return None

def series(ticker, rng, interval, monthly=False):
    res = chart(ticker, rng, interval)
    if not res: return None
    ts = res.get("timestamp"); q = res.get("indicators", {}).get("quote", [{}])[0]; cl = q.get("close")
    if not ts or not cl: return None
    out = []
    for t, c in zip(ts, cl):
        if c is None: continue
        out.append([datetime.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"), round(float(c), 2)])
    if monthly and out and out[-1][0].startswith(CUR_MONTH):
        out = out[:-1]
    return out

# (v3.21) theme -> (대표ETF 티커, 표시명). 전력기기/우주 티커 정정:
#   전력기기 458730 = TIGER 미국배당다우존스(미국배당), 우주 481190 = SOL 미국테크TOP10(미국테크) 였음 → 테마와 불일치라 교체.
themes_etf = {
    "반도체/AI": ("091160.KS", "KODEX 반도체"),
    "전력기기": ("491820.KS", "HANARO 전력설비투자"),
    "조선": ("466920.KS", "SOL 조선TOP3플러스"),
    "방산": ("449450.KS", "PLUS K방산"),
    "원자력": ("442320.KS", "RISE 글로벌원자력"),
    "증권": ("102970.KS", "KODEX 증권"),
    "로봇": ("445290.KS", "KODEX K-로봇액티브"),
    "우주": ("421320.KS", "PLUS 우주항공&UAM"),
    "건설": ("117700.KS", "KODEX 건설"),
    "건설기계": ("102960.KS", "KODEX 기계장비"),
    "항공": ("228800.KS", "TIGER 여행레저"),
    "정유": ("117460.KS", "KODEX 에너지화학"),
    "K푸드": ("438900.KS", "HANARO Fn K-푸드"),
    "K화장품": ("228790.KS", "TIGER 화장품"),
}
stocks = {
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "한미반도체": "042700.KS", "삼성전기": "009150.KS",
    "DB하이텍": "000990.KS", "리노공업": "058470.KQ", "이오테크닉스": "039030.KQ", "HPSP": "403870.KQ",
    "주성엔지니어링": "036930.KQ", "원익IPS": "240810.KQ",
    "LG이노텍": "011070.KS", "대덕전자": "353200.KS", "심텍": "222800.KQ",
    "이수페타시스": "007660.KS", "ISC": "095340.KQ", "SK스퀘어": "402340.KS",
}
etfs_ordered = [
    ("TIGER Fn반도체TOP10", "396500.KS"), ("KODEX 반도체", "091160.KS"), ("KODEX Fn시스템반도체", "395160.KS"),
    ("TIGER 반도체", "091230.KS"), ("TIGER 미국필라델피아반도체나스닥", "381180.KS"), ("ACE AI반도체포커스", "469150.KS"),
    ("TIGER 글로벌AI액티브", "442580.KS"), ("TIGER 반도체TOP10레버리지", "462330.KS"), ("KODEX 미국반도체MV", "390390.KS"),
    ("KODEX 미국AI테크TOP10", "487230.KS"), ("ACE 글로벌반도체TOP4 Plus", "446770.KS"), ("TIGER 미국AI반도체(PHLX)", "497570.KS"),
    ("ACE 엔비디아밸류체인액티브", "483320.KS"), ("KBSTAR AI&로봇", "469070.KS"), ("BNK 온디바이스AI", "487750.KS"),
    ("SOL 미국AI소프트웨어", "480040.KS"), ("TIGER 미국필라델피아반도체레버리지(합성)", "428510.KS"), ("KOSEF 글로벌AI반도체", "473490.KS"),
    ("KIWOOM 코리아테크TOP10", "469790.KS"), ("SOL 반도체후공정", "395150.KS"),
]

tasks = ([("themes", th, tk, "10y", "1mo", True) for th, (tk, _nm) in themes_etf.items()] +
         [("stocks", nm, tk, "1y", "1wk", False) for nm, tk in stocks.items()] +
         [("etfs", nm, tk, "1y", "1wk", False) for nm, tk in etfs_ordered])

def _daum_wk(tk):
    # (fix v3.48) Yahoo 가 한국상장 ETF/테마 이력을 안 줄 때 finance.daum.net 일봉 → 주봉 다운샘플
    code = tk.split(".")[0]
    try:
        u = "https://finance.daum.net/api/charts/A%s/days?limit=520&adjusted=true" % code
        req = urllib.request.Request(u, headers={"Referer": "https://finance.daum.net/quotes/A%s" % code,
                                                 "User-Agent": H["User-Agent"], "X-Requested-With": "XMLHttpRequest"})
        d = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "replace")).get("data", [])
        rows = []
        for p in d:
            tp = p.get("tradePrice")
            if not tp: continue
            rows.append([str(p.get("date"))[:10], round(float(tp), 2)])
        rows.sort()
        wk = rows[::5]
        if wk and wk[-1] is not rows[-1]: wk.append(rows[-1])
        return wk
    except Exception:
        return []

def fetch_one(t):
    bucket, key, tk, rng, iv, mo = t
    try:
        sv = series(tk, rng, iv, monthly=mo) or []
        if len(sv) < 5:                 # (fix v3.48) Yahoo 부실(한국상장 ETF/테마) → Daum 폴백
            dv = _daum_wk(tk)
            if len(dv) >= 5: sv = dv
        return bucket, key, sv
    except Exception:
        return bucket, key, _daum_wk(tk)

kr_series = {"stocks": {}, "etfs": {}, "themes": {}}
with ThreadPoolExecutor(max_workers=8) as ex:
    for bucket, key, sv in ex.map(fetch_one, tasks):
        kr_series[bucket][key] = sv
ok = sum(1 for b in ("stocks", "etfs", "themes") for v in kr_series[b].values() if v)
miss = sum(1 for b in ("stocks", "etfs", "themes") for v in kr_series[b].values() if not v)

# (v3.21) 전일 대비(1일) 스냅샷 — 월/주봉으로는 1일 변동 산출 불가하므로 일봉 마지막 2개 종가로 계산.
#         테마 현재가는 월봉(현재월 제외)이라 stale → 일봉 현재가로 merge 에서 갱신.
def day_snap(tk):
    res = chart(tk, "1mo", "1d")
    if not res: return None
    q = res.get("indicators", {}).get("quote", [{}])[0]; cl = q.get("close") or []
    pts = [float(c) for c in cl if c is not None]
    if len(pts) < 2 or not pts[-2]: return None
    cur, prev = pts[-1], pts[-2]
    dec = 4 if abs(cur) < 10 else (3 if abs(cur) < 100 else 2)
    prev_pct = round((pts[-2] / pts[-3] - 1) * 100, 2) if (len(pts) >= 3 and pts[-3]) else None  # (req5) 직전장 등락률 → '1일' 칸
    return {"current": round(cur, dec), "chg": round(cur - prev, dec), "1d_pct": round((cur / prev - 1) * 100, 2), "prev_close": round(prev, dec), "prev_pct": prev_pct}
dtasks = ([("themes", th, tk) for th, (tk, _n) in themes_etf.items()] +
          [("stocks", nm, tk) for nm, tk in stocks.items()] +
          [("etfs", nm, tk) for nm, tk in etfs_ordered])
def fetch_day(t):
    b, k, tk = t
    try: return b, k, day_snap(tk)
    except Exception: return b, k, None
daily = {"themes": {}, "stocks": {}, "etfs": {}}
with ThreadPoolExecutor(max_workers=8) as ex:
    for b, k, sv in ex.map(fetch_day, dtasks):
        if sv: daily[b][k] = sv
kr_series["daily"] = daily
kr_series["theme_etf"] = {th: nm for th, (tk, nm) in themes_etf.items()}

# [DB화·시총 매일] 다음금융 quotes 로 시총·상장주식수 매일 수집 → 시총=현재가×주식수(라이브), 주식수 변동 자동 반영
import urllib.request as _ur
def _daum_cap(code6):
    u="https://finance.daum.net/api/quotes/A%s?summary=false"%code6
    rq=_ur.Request(u, headers={"Referer":"https://finance.daum.net/quotes/A%s"%code6,"User-Agent":"Mozilla/5.0","X-Requested-With":"XMLHttpRequest"})
    d=json.loads(_ur.urlopen(rq, timeout=10).read().decode("utf-8"))
    return {"eok": round(d.get("marketCap",0)/1e8), "shares": d.get("listedShareCount"), "price": d.get("tradePrice")}
_caps={}
for _nm,_tk in (list(stocks.items())+etfs_ordered):
    try: _caps[_nm]=_daum_cap(_tk.split(".")[0])
    except Exception: pass
kr_series["caps"]=_caps
print("  [caps] 시총·상장주식수 매일수집:", len(_caps), "종")

# ══════════════════════════════════════════════════════════════════
#  (v3.64) 네이버 보강 — 수급·컨센서스·외인소진율 (KRX OPEN API 는 T+1 이라 못 쓰던 것들)
#
#  Yahoo 는 종가·수익률만 준다. 한국 종목을 볼 때 정작 중요한
#  "오늘 누가 사고 팔았나(외국인/기관/개인)"·"애널리스트 목표주가는 얼마인가"가 빠져 있었다.
#  네이버 /integration 이 종목당 1콜로 당일 값을 전부 준다. (KRX 는 T+1 이라 오늘 수급을 못 준다)
#
#  ⚠️ Yahoo 의 한국 개별종목 '시가' 는 부정확하다 (SK하이닉스 2026-07-13:
#     Yahoo 2,113,000 vs KRX/네이버 2,207,000). 시가·고저가는 네이버 값을 쓴다.
# ══════════════════════════════════════════════════════════════════
def _naver_detail(code6):
    u = "https://m.stock.naver.com/api/stock/%s/integration" % code6
    rq = _ur.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    d = json.loads(_ur.urlopen(rq, timeout=10).read().decode("utf-8"))
    T = {x.get("key"): x.get("value") for x in (d.get("totalInfos") or [])}
    def n(k):
        v = T.get(k)
        if not v: return None
        try: return float(str(v).replace(",", "").replace("%", "").replace("원", "").replace("배", ""))
        except Exception: return None
    out = {}
    for k, kk in (("시가","open"),("고가","high"),("저가","low"),("전일","prev_close"),
                  ("외인소진율","foreign_rate"),("PER","per"),("추정PER","fwd_per"),
                  ("추정EPS","fwd_eps"),("52주 최고","hi52"),("52주 최저","lo52")):
        v = n(k)
        if v is not None: out[kk] = v
    dt = (d.get("dealTrendInfos") or [{}])[0]
    if dt.get("bizdate"):
        out["flows"] = {"date": dt.get("bizdate"),
                        "foreign": dt.get("foreignerPureBuyQuant"),
                        "inst": dt.get("organPureBuyQuant"),
                        "indiv": dt.get("individualPureBuyQuant"),
                        "foreign_hold": dt.get("foreignerHoldRatio")}
    cs = d.get("consensusInfo") or {}
    if cs.get("priceTargetMean"):
        try:
            tgt = float(str(cs["priceTargetMean"]).replace(",", ""))
            out["consensus"] = {"target": tgt, "recomm": cs.get("recommMean"), "asof": cs.get("createDate")}
        except Exception: pass
    return out

_nv = {}
for _nm, _tk in (list(stocks.items()) + etfs_ordered):
    try:
        _d = _naver_detail(_tk.split(".")[0])
        if _d:
            c = (_caps.get(_nm) or {}).get("price")
            if c and (_d.get("consensus") or {}).get("target"):
                _d["consensus"]["upside_pct"] = round((_d["consensus"]["target"] / c - 1) * 100, 1)
            _nv[_nm] = _d
    except Exception:
        pass
kr_series["naver"] = _nv
_fl = sum(1 for v in _nv.values() if v.get("flows"))
_cs = sum(1 for v in _nv.values() if v.get("consensus"))
print("  [naver] 보강 %d종 — 당일수급 %d · 목표주가 %d · 시가·외인소진율 포함" % (len(_nv), _fl, _cs))

json.dump(kr_series, open("nmr_kr_series.json", "w", encoding="utf-8"), ensure_ascii=False)
json.dump(kr_series.get("themes", {}), open("nmr_themeseries1y.json", "w", encoding="utf-8"), ensure_ascii=False)  # [브리지] gen_rest_charts theme_*
print(f"WROTE nmr_kr_series.json — themes {len(kr_series['themes'])} stocks {len(kr_series['stocks'])} etfs {len(kr_series['etfs'])} | ok {ok} miss {miss} | daily {sum(len(v) for v in daily.values())}")
