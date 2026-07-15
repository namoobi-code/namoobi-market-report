#!/usr/bin/env python3
"""verdict_*.json + risk_review.json 병합 → ta_verdict.json + 보고서 md. stdlib only.
사용: python3 save_verdict.py <WORK_DIR>
"""
import json, sys, os, glob
from datetime import datetime

WORK=sys.argv[1]
meta=json.load(open(f"{WORK}/meta.json"))
td=meta.get("trade_date","")
verdicts=[]
for p in sorted(glob.glob(f"{WORK}/verdict_*.json")):
    grp=os.path.basename(p).replace("verdict_","").replace(".json","")
    mkt="KR" if grp.startswith("KR") else "US"
    for v in json.load(open(p)):
        v["시장"]=v.get("시장",mkt); verdicts.append(v)
if not verdicts:
    print("verdict 파일 없음", file=sys.stderr); sys.exit(1)
risk={}
if os.path.exists(f"{WORK}/risk_review.json"):
    risk=json.load(open(f"{WORK}/risk_review.json"))
# 기준가 스냅샷 (성과추적용): 번들 기술지표 close
px={}
for g in ("KR1","KR2","US1","US2"):
    try:
        for b in json.load(open(f"{WORK}/grp_{g}.json")):
            key=b.get("종목")
            t=(b.get("기술지표") or {})
            code=b.get("코드") or b.get("티커")
            kr=g.startswith("KR")
            # ⚠️ Yahoo 는 한국 종목에 잘못된 접미사를 줘도 에러 대신 '엉뚱한 종목' 데이터를 반환한다
            #    (006910.KS → 딴 종목 3,475원). 그래서 정확한 심볼을 판정 시점에 못박아 남긴다.
            #    price_date 도 같이 남긴다 — trade_date(KRX 기준일)는 1영업일 지연돼 가격일과 다르다.
            ysym=(code if not kr else
                  code + (".KQ" if str(b.get("시장","")).upper().startswith("KOSDAQ") else ".KS"))
            px[key]={"close":t.get("close"),
                     "prev_close":t.get("prev_close"),
                     "ret_1d":t.get("ret_1d"),
                     "price_date":t.get("price_date"),
                     "atr_pct":t.get("atr_pct"),
                     "code":code, "ysym":ysym,
                     "시장":"KR" if kr else "US",
                     "거래소":b.get("시장")}
    except Exception: pass
approved=[r for r in risk.get("심사대상",[]) if r.get("승인")]
out={"trade_date":td,"as_of":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
     "verdicts":verdicts,"risk_review":risk,"approved":approved,"px_snapshot":px}
json.dump(out, open(f"{WORK}/ta_verdict.json","w"), ensure_ascii=False, indent=1)
# ---- 보고서 md ----
order={"채택":0,"관망":1,"탈락":2}
vs=sorted(verdicts,key=lambda v:(order.get(v.get("판정"),3),-(v.get("확신도") or 0)))
L=[f"# 트레이딩 에이전트 판정 보고서 (기준 거래일 {td})\n",
   f"> 서버 자동 스크리닝(1~3단계) 상위 20종목에 대한 Bull/Bear 토론 + 리스크 심사. 생성 {out['as_of']}. **투자 자문 아님 — 참고용.**\n"]
cnt={k:sum(1 for v in verdicts if v.get("판정")==k) for k in ("채택","관망","탈락")}
L.append(f"**판정 분포**: 채택 {cnt['채택']} · 관망 {cnt['관망']} · 탈락 {cnt['탈락']}\n")
if approved:
    L.append("## 최종 승인 (리스크 심사 통과)\n")
    L.append("| 종목 | 시장 | 확신도 | 비중 가이드 | 손절선 | 무효화 조건 | 사유 |")
    L.append("|---|---|--:|---|--:|---|---|")
    for r in approved:
        sl=r.get('손절선'); sl=f"{sl:,.0f}" if isinstance(sl,(int,float)) else (sl or '-')
        L.append(f"| {r['종목']} | {r.get('시장','')} | {r.get('확신도','')} | {r.get('비중가이드','')} | {sl} | {r.get('무효화','-')} | {r.get('사유','')} |")
else:
    L.append("## 최종 승인: 없음\n")
rej=[r for r in risk.get("심사대상",[]) if not r.get("승인")]
if rej:
    L.append("\n**리스크 심사 반려**: "+", ".join(f"{r['종목']}({r.get('사유','')})" for r in rej))
if risk.get("총평"): L.append(f"\n**총평**: {risk['총평']}\n")
L.append("\n---\n## 종목별 토론 카드\n")
for v in vs:
    ic={"채택":"🟢","관망":"🟡","탈락":"🔴"}.get(v.get("판정"),"⚪")
    L.append(f"### {ic} {v.get('종목')} [{v.get('시장')}] — {v.get('판정')} (확신도 {v.get('확신도','?')}/10)\n")
    a=v.get("분석가",{})
    for k in ("기본","기술","심리","뉴스"):
        if a.get(k): L.append(f"- **{k}**: {a[k]}")
    if v.get("bull"): L.append(f"\n**Bull**: "+" / ".join(v["bull"]))
    if v.get("bear"): L.append(f"\n**Bear**: {v['bear']}")
    L.append(f"\n**근거**: {v.get('근거','')} | **촉매**: {v.get('촉매','')} | **리스크**: {v.get('리스크','')}\n")
L.append("\n---\n*투자 자문이 아니며 판정은 참고용. 매매 판단과 책임은 사용자에게 있다.*")
rp=f"{WORK}/트레이딩에이전트_판정_{td}.md"
open(rp,"w").write("\n".join(L))
print("saved:", rp)
print("approved:", [r["종목"] for r in approved])
