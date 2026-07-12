#!/usr/bin/env python3
"""서버에서 ta_stage3(토론 번들)·ta_stage2를 내려받아 그룹 파일로 분할. stdlib only.
사용: python3 fetch_bundles.py <WORK_DIR> [server_base]
출력: OK <trade_date> | STALE <trade_date> | 실패 시 exit 1
"""
import json, sys, os, urllib.request
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
