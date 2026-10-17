#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""backfill_kr_opt.py — 3.1.13 KOSPI200 옵션지표(PCR·IV스큐·GEX) 과거 백필.

근거: KRX OPEN API `drv/opt_bydd_trd`(지수옵션 일별매매정보)가 임의 과거일의
전 행사가 체인(IMP_VOLT 내재변동성 + ACC_OPNINT_QTY 미결제)을 반환함을 실측 확인(2026-07-17).
만기 지난 시리즈도 해당 일자 기준으로 조회되므로 KIS(활성물만·이력 미제공)와 달리 완전 백필이 가능하다.
(검토 결론: KIS 기간별시세=만기경과 시리즈 조회 불가, 네이버=옵션 체인 이력 미제공 → KRX만 가능.
 미국 SPX·NDX는 무료 과거 체인 소스가 없어 백필 불가 — 2026-07-11 수집분부터 자체 누적.)

방법론 = 라이브(KIS T+0, kis_api.option_chain)와 동일:
  · 근월물(만기 미도래 최근월; 만기 당일은 차월물로 롤) 전 체인 PCR(OI)
  · PCR(vol)은 양측 100계약 sanity
  · 25델타 스큐 = 25d 풋IV − 25d 콜IV (BS delta, KRX IV%→소수, |스큐|>30 폐기)
  · GEX = Σ(콜 +γ·OI − 풋 γ·OI)·250,000·S²/100 (억원), γ=BS(S=현물), r=0.03
현물 S = idx/kospi_dd_trd '코스피 200' 종가(T+1 확정). id='KOSPI200'.
이미 값이 있는 날짜(예: KIS T+0 기록분)는 COALESCE 로 보존한다.

Usage: backfill_kr_opt.py <deriv_signals.db> [--chunk N] [--target 70]
  chunk 일수만큼 처리 후 종료(샌드박스 45초 벽 회피) — 반복 호출로 target 거래일까지 누적.
  "DONE" 출력 = target 달성, "MORE" = 재호출 필요.
백필 후 반드시: db.connect() 로컬 재시딩 → analyze.run_analysis(con) → db.publish_db()
  (analyze.py 는 직접 실행해도 아무 것도 하지 않는다 — run_analysis 명시 호출 필요.)
"""
import sys, os, re, json, math, glob, time, sqlite3, urllib.request, datetime as dt

DB   = sys.argv[1]
CH   = int(sys.argv[sys.argv.index("--chunk")+1]) if "--chunk" in sys.argv else 12
TGT  = int(sys.argv[sys.argv.index("--target")+1]) if "--target" in sys.argv else 70
def key():
    for p in glob.glob("/sessions/*/mnt/claudeCowork/SECURITY/openapi.krx.co.kr.txt")+["D:/claudeCowork/SECURITY/openapi.krx.co.kr.txt"]:
        try: return open(p).read().strip()
        except Exception: pass
    return os.environ.get("KRX_API_KEY","")
KEY=key(); assert KEY, "KRX key not found"
def krx(ep, bas):
    url=f"https://data-dbg.krx.co.kr/svc/apis/{ep}?basDd={bas}"
    req=urllib.request.Request(url, headers={"AUTH_KEY":KEY,"User-Agent":"Mozilla/5.0"})
    for t in range(3):
        try: return json.loads(urllib.request.urlopen(req,timeout=40).read()).get("OutBlock_1") or []
        except Exception as e:
            if t==2: print("  krx err",ep,bas,repr(e)[:60]); return []
            time.sleep(1.5)
def second_thu(y,m):
    d=dt.date(y,m,1); off=(3-d.weekday())%7  # 첫 목요일
    return d+dt.timedelta(days=off+7)
def ncdf(x): return 0.5*(1.0+math.erf(x/math.sqrt(2.0)))
def greeks(S,K,T,r,sig):
    if not(sig>0 and T>0 and S>0 and K>0): return 0.0,0.0
    d1=(math.log(S/K)+(r+0.5*sig*sig)*T)/(sig*math.sqrt(T))
    gamma=math.exp(-0.5*d1*d1)/(S*sig*math.sqrt(T)*math.sqrt(2*math.pi))
    return d1,gamma
con=sqlite3.connect(DB)
have={r[0] for r in con.execute("SELECT date FROM kr_derivatives_daily WHERE id='KOSPI200' AND (pcr_oi IS NOT NULL OR iv_skew_25d IS NOT NULL)")}
def done_n(): return len(have)
d=dt.date.today()-dt.timedelta(days=1)  # 어제부터 뒤로(당일은 KIS T+0 담당)
proc=0
while proc<CH and done_n()<TGT and d>dt.date.today()-dt.timedelta(days=200):
    ds=d.strftime("%Y%m%d"); iso=d.isoformat()
    if d.weekday()>=5 or iso in have: d-=dt.timedelta(days=1); continue
    rows=krx("drv/opt_bydd_trd", ds)
    k=[r for r in rows if r.get("PROD_NM")=="코스피200 옵션" and "(야간)" not in r.get("ISU_NM","")]
    if not k: print(ds,"휴장/무자료"); d-=dt.timedelta(days=1); proc+=1; continue
    idx=krx("idx/kospi_dd_trd", ds)
    S=None
    for r in idx:
        if r.get("IDX_NM","").strip()=="코스피 200":
            try: S=float(r["CLSPRC_IDX"].replace(",",""))
            except Exception: pass
    chain=[]
    for r in k:
        m=re.match(r"코스피200\s+([CP])\s+(\d{6})\s+([\d,]+\.\d)", r["ISU_NM"])
        if not m: continue
        side,exp,K=m.group(1),m.group(2),float(m.group(3).replace(",",""))
        def f(x):
            try: return float(str(x).replace(",","") or 0)
            except Exception: return 0.0
        chain.append((side,exp,K,f(r["IMP_VOLT"]),f(r["ACC_OPNINT_QTY"]),f(r["ACC_TRDVOL"])))
    exps=sorted({e for _,e,_,_,_,_ in chain})
    exp=None
    for e in exps:
        # 만기 당일(second_thu==d)엔 front-month OI 가 붕괴 → 차월물로 롤
        if second_thu(int(e[:4]),int(e[4:6]))>d: exp=e; break
    if not exp: print(ds,"만기산정 실패"); d-=dt.timedelta(days=1); proc+=1; continue
    ed=second_thu(int(exp[:4]),int(exp[4:6])); T=max((ed-d).days,1)/365.0
    C=[(K,iv,oi,vol) for s,e,K,iv,oi,vol in chain if s=="C" and e==exp]
    P=[(K,iv,oi,vol) for s,e,K,iv,oi,vol in chain if s=="P" and e==exp]
    coi=sum(x[2] for x in C); poi=sum(x[2] for x in P)
    cv=sum(x[3] for x in C); pv=sum(x[3] for x in P)
    pcr_oi=round(poi/coi,3) if coi else None
    if pcr_oi is not None and not (0.2<=pcr_oi<=8): pcr_oi=None
    pcr_vol=round(pv/cv,3) if (cv>=100 and pv>=100) else None
    skew=None; gex=None
    if S:
        cand_c=[]; cand_p=[]; g_sum=0.0
        for arr,side in ((C,"C"),(P,"P")):
            for K,iv,oi,vol in arr:
                if not (0<iv<150): continue
                d1,gm=greeks(S,K,T,0.03,iv/100.0)
                delta=ncdf(d1) if side=="C" else ncdf(d1)-1.0
                if 0.05<=abs(delta)<=0.60:
                    (cand_c if side=="C" else cand_p).append((abs(abs(delta)-0.25),iv))
                if gm and oi: g_sum+=(1 if side=="C" else -1)*gm*oi*250000*(S**2)/100.0
        if cand_c and cand_p:
            skew=round(min(cand_p)[1]-min(cand_c)[1],2)
            if abs(skew)>30: skew=None
        gex=round(g_sum/1e8,1) if g_sum else None
    con.execute("""INSERT INTO kr_derivatives_daily(id,date,pcr_oi,pcr_vol,iv_skew_25d,gex) VALUES(?,?,?,?,?,?)
                   ON CONFLICT(id,date) DO UPDATE SET
                     pcr_oi=COALESCE(kr_derivatives_daily.pcr_oi,excluded.pcr_oi),
                     pcr_vol=COALESCE(kr_derivatives_daily.pcr_vol,excluded.pcr_vol),
                     iv_skew_25d=COALESCE(kr_derivatives_daily.iv_skew_25d,excluded.iv_skew_25d),
                     gex=COALESCE(kr_derivatives_daily.gex,excluded.gex)""",
                ("KOSPI200",iso,pcr_oi,pcr_vol,skew,gex))
    con.commit(); have.add(iso)
    print(iso,"exp",exp,"S",S,"PCR",pcr_oi,"skew",skew,"gex",gex,"| 누적",done_n())
    d-=dt.timedelta(days=1); proc+=1; time.sleep(0.3)
print("DONE" if done_n()>=TGT else "MORE", "| 확보 거래일:", done_n())
