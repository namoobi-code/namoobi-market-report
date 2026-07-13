#!/usr/bin/env python3
"""서버에서 ta_stage3(토론 번들)·ta_stage2를 내려받아 그룹 파일로 분할. stdlib only.
사용: python3 fetch_bundles.py <WORK_DIR> [server_base]
출력: OK <trade_date> | STALE <trade_date> | 실패 시 exit 1
"""
import json, sys, os, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date

WORK=sys.argv[1]
BASE=sys.argv[2] if len(sys.argv)>2 else "http://141.147.160.13"
os.makedirs(WORK, exist_ok=True)

def jget(name):
    with urllib.request.urlopen(f"{BASE}/api/db/{name}", timeout=20) as r:
        return json.loads(r.read())
try:
    try: flag=jget("ta_flag")
    except Exception: flag=None
    # 서버가 스크리닝 생성 중이면 데이터를 읽지 않는다 (혼합·부분 데이터 사용 방지)
    if flag and flag.get("status")=="running":
        print("RUNNING", flag.get("started","?")); sys.exit(2)
    if flag and flag.get("status")=="failed":
        print("PIPELINE_FAILED", flag.get("failed_at","?"), (flag.get("error") or "")[:120]); sys.exit(4)
    s3=jget("ta_stage3"); s2=jget("ta_stage2")
except SystemExit: raise
except Exception as e:
    print(f"서버 접속 실패: {type(e).__name__}: {e}", file=sys.stderr); sys.exit(1)

# 파일 간 정합: stage2와 stage3의 기준 거래일이 다르면 파이프라인이 중간에 끊긴 것
if s2.get("trade_date")!=s3.get("trade_date"):
    print("INCONSISTENT", s2.get("trade_date"), s3.get("trade_date")); sys.exit(5)

json.dump(s2, open(f"{WORK}/ta_stage2.json","w"), ensure_ascii=False)
groups={"KR1":s3["kr"][:5],"KR2":s3["kr"][5:10],"US1":s3["us"][:5],"US2":s3["us"][5:10]}

# ---- 실시간 시세 대조: 번들(확정 일봉)과 현재가의 괴리를 각 종목에 주입 ----
UA={"User-Agent":"Mozilla/5.0"}
def jget_ua(url,timeout=12):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.loads(r.read())
def _num(x):
    try: return float(str(x).replace(",",""))
    except Exception: return None
def _live_kr(b):
    try:
        d=jget_ua(f"https://m.stock.naver.com/api/stock/{b.get('코드')}/basic")
        return _num(d.get("closePrice")), _num(d.get("fluctuationsRatio"))
    except Exception: return None,None
def _live_us(b):
    try:
        m=jget_ua(f"https://query1.finance.yahoo.com/v8/finance/chart/{b.get('티커')}?range=1d&interval=1d")["chart"]["result"][0]["meta"]
        px=m.get("regularMarketPrice"); pv=m.get("chartPreviousClose")
        return px, round((px/pv-1)*100,2) if px and pv else None
    except Exception: return None,None
alerts=[]
for g,items in groups.items():
    fn=_live_kr if g.startswith("KR") else _live_us
    with ThreadPoolExecutor(max_workers=8) as ex:
        res=list(ex.map(fn,items))
    for b,(px,day) in zip(items,res):
        base=(b.get("기술지표") or {}).get("close")
        if px and base:
            gap=px/base-1
            b["실시간체크"]={"현재가":px,"번들종가":base,"번들대비":round(gap,4),
                            "당일등락률%":day,"조회":datetime.now().strftime("%m-%d %H:%M")}
            if abs(gap)>=0.05:
                b["실시간체크"]["ALERT"]=f"번들 대비 {gap*100:+.1f}% 급변 — 원인 규명 전 채택 금지, 토론·리스크 심사에서 반드시 재평가"
                alerts.append(f"{b.get('종목')} {gap*100:+.1f}%")
        else:
            b["실시간체크"]={"오류":"실시간 시세 조회 실패 — 확정 일봉 기준으로만 판단하고 confidence를 낮출 것"}
for g,items in groups.items():
    json.dump(items, open(f"{WORK}/grp_{g}.json","w"), ensure_ascii=False, indent=1)
json.dump({"trade_date":s3.get("trade_date"),"as_of":s3.get("as_of")},
          open(f"{WORK}/meta.json","w"), ensure_ascii=False)

td=s3.get("trade_date","")
stale=False
try:
    d=datetime.strptime(td,"%Y%m%d").date()
    stale=(date.today()-d).days>5
except Exception: stale=True
names={g:[x.get("종목") for x in items] for g,items in groups.items()}
flag_tok="FLAG_MISSING"
if flag and flag.get("completed"):
    flag_tok=f"FLAG {flag['completed']} ({flag.get('flag_file','')})"
    if flag.get("trade_date") and flag["trade_date"]!=td: flag_tok+=" MISMATCH"
print(("STALE" if stale else "OK"), td, flag_tok)
print(json.dumps(names, ensure_ascii=False))
print(("ALERTS "+json.dumps(alerts,ensure_ascii=False)) if alerts else "NO_ALERT")
