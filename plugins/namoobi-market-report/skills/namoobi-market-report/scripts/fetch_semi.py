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

themes_etf = {
    "반도체/AI": "091160.KS", "전력기기": "458730.KS", "조선": "466920.KS", "방산": "449450.KS",
    "원자력": "442320.KS", "증권": "102970.KS", "로봇": "445290.KS", "우주": "481190.KS",
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

tasks = ([("themes", th, tk, "10y", "1mo", True) for th, tk in themes_etf.items()] +
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
ok = sum(1 for b in kr_series.values() for v in b.values() if v)
miss = sum(1 for b in kr_series.values() for v in b.values() if not v)
json.dump(kr_series, open("nmr_kr_series.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"WROTE nmr_kr_series.json — themes {len(kr_series['themes'])} stocks {len(kr_series['stocks'])} etfs {len(kr_series['etfs'])} | ok {ok} miss {miss}")
