#!/usr/bin/env python3
# nmr_reasons.py (req0) — 결측 셀에 정확한 사유/계산값을 채우고, KSVKOSPI 실측을 주입한다. merge 직후 실행.
import json, sys, os, glob
RD = sys.argv[1]
WORK = os.path.dirname(os.path.dirname(os.path.abspath(RD)))
d = json.load(open(RD, encoding="utf-8"))
m = d.get("markets") or {}
mac = m.get("macro") or {}
def empty(v): return v in (None, "", "-")
def loadj(name):
    for p in [os.path.join(WORK,name)]+glob.glob("/sessions/*/mnt/outputs/nmr_build/"+name)+glob.glob("/sessions/*/mnt/claudeCowork/_market_report_data/"+name):
        try: return json.load(open(p,encoding="utf-8"))
        except Exception: pass
    return {}
mom = loadj("nmr_mom.json")
MOM_KEY = [("Core CPI","core_cpi"),("Core PCE","core_pce"),("PCE","pce"),("PPI","ppi"),("CPI (헤드","cpi")]
infl = (mac.get("inflation") or {})
for r in (infl.get("rows") or []):
    nm = r.get("name") or ""
    bei = ("BEI" in nm or "기대인플레" in nm)
    if bei:
        lvl = (infl.get("infl_exp_10y") or {}).get("current")
        if (lvl is not None) and (empty(r.get("yoy")) or r.get("yoy") is None):
            r["yoy"] = "%.2f%% (수준)" % lvl
        r["mom"] = "수준지표(MoM 미해당)"
        if empty(r.get("release")): r["release"] = "실시간 시장지표"
        if empty(r.get("asof")): r["asof"] = (infl.get("infl_exp_10y") or {}).get("asof") or "실시간"
        continue
    cur = r.get("mom")
    needs = empty(cur) or (isinstance(cur,str) and ("미수집" in cur or "미집계" in cur))
    if needs:
        mk = next((k for lbl,k in MOM_KEY if nm.startswith(lbl) or lbl in nm), None)
        v = (mom.get(mk) or {}).get("mom") if mk else None
        if v is not None: r["mom"] = v
    if empty(r.get("release")): r["release"] = "정기 발표(BLS/BEA)"
EMP_REL = [("NFP","2026-06-05"),("실업률","2026-06-05"),("소매판매","2026-06-17"),("ISM 제조","2026-06-01"),("ISM 서비","2026-06-03"),("GDP","2026-06-26")]
for r in ((mac.get("employment") or {}).get("rows") or []):
    if empty(r.get("release")):
        nm = r.get("name") or ""
        r["release"] = next((v for k,v in EMP_REL if k in nm), "정기 발표(BLS/BEA/ISM)")
# (req3/7) KSVKOSPI 실측 주입(investing.com 파싱값)
vk = loadj("nmr_vkospi_history.json"); vka = (vk.get("anchors") or {})
for r in ((mac.get("sentiment") or {}).get("rows") or []):
    nm = r.get("name") or ""
    if "KSV" in nm or "KOSPI Volatility" in nm:
        if vka:
            if vk.get("current") is not None: r["current"]=vk["current"]
            if vk.get("prev_close") is not None: r["prev_close"]=vk["prev_close"]
            for k in ["1d_pct","1w_pct","1mo_pct","3mo_pct","6mo_pct","1y_pct"]:
                if vka.get(k) is not None: r[k]=vka[k]
            if vka.get("1d_pct") is not None: r["prev_pct"]=vka["1d_pct"]  # 빌더 day1pct 는 prev_pct 사용
            r["trend"]="실시간(investing.com KSVKOSPI 페이지 파싱) 1일~1년 전구간 반영"
        elif all(empty(r.get(k)) for k in ["1w_pct","1mo_pct","3mo_pct","6mo_pct","1y_pct"]):
            r["trend"]="현재값 실시간(CNBC) · 1주~1년 이력 미확보(소스 접근 차단)"
json.dump(d, open(RD,"w",encoding="utf-8"), ensure_ascii=False)
print("[nmr_reasons] req0 사유/계산값 + KSVKOSPI 실측 주입 완료")
# EOF — namoobi-market-report nmr_reasons
