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
}
stocks = {
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "한미반도체": "042700.KS", "삼성전기": "009150.KS",
    "DB하이텍": "000990.KS", "리노공업": "058470.KQ", "이오테크닉스": "039030.KQ", "HPSP": "403870.KQ",
    "주성엔지니어링": "036930.KQ", "원익IPS": "240810.KQ",
}
etfs_ordered = [
    ("TIGER Fn반도체TOP10", "396500.KS"), ("KODEX 반도체", "091160.KS"), ("KODEX Fn시스템반도체", "395160.KS"),
    ("TIGER 반도체", "091230.KS"), ("TIGER 미국필라델피아반도체나스닥", "381180.KS"), ("ACE AI반도체포커스", "469150.KS"),
    ("TIGER 글로벌AI액티브", "442580.KS"), ("TIGER 반도체TOP10레버리지", "462330.KS"), ("KODEX 미국반도체MV", "390390.KS"),
    ("KODEX 미국AI테크TOP10", "487230.KS"), ("KODEX 미국반도체레버리지(합성)", "446770.KS"), ("TIGER 미국AI반도체(PHLX)", "497570.KS"),
    ("ACE 엔비디아밸류체인액티브", "483320.KS"), ("KBSTAR AI&로봇", "469070.KS"), ("BNK 온디바이스AI", "487750.KS"),
    ("SOL 미국AI소프트웨어", "480040.KS"), ("TIGER 미국필라델피아반도체레버리지(합성)", "428510.KS"), ("KOSEF 글로벌AI반도체", "473490.KS"),
    ("RISE 반도체", "469790.KS"), ("SOL 반도체후공정", "395150.KS"),
]

tasks = ([("themes", th, tk, "10y", "1mo", True) for th, (tk, _nm) in themes_etf.items()] +
         [("stocks", nm, tk, "1y", "1wk", False) for nm, tk in stocks.items()] +
         [("etfs", nm, tk, "1y", "1wk", False) for nm, tk in etfs_ordered])

def fetch_one(t):
    bucket, key, tk, rng, iv, mo = t
    try: return bucket, key, series(tk, rng, iv, monthly=mo) or []
    except Exception: return bucket, key, []

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
    prev_pct = round((pts[-2] / pts[-3] - 1) * 100, 2) if (len(pts) >= 3 and pts[-3]) else None  # (req5) 직전장 등락률
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

json.dump(kr_series, open("nmr_kr_series.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"WROTE nmr_kr_series.json — themes {len(kr_series['themes'])} stocks {len(kr_series['stocks'])} etfs {len(kr_series['etfs'])} | ok {ok} miss {miss} | daily {sum(len(v) for v in daily.values())}")
