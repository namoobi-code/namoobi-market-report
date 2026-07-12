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
    s3=jget("ta_stage3"); s2=jget("ta_stage2")
except Exception as e:
    print(f"서버 접속 실패: {type(e).__name__}: {e}", file=sys.stderr); sys.exit(1)

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
print(("STALE" if stale else "OK"), td)
print(json.dumps(names, ensure_ascii=False))
