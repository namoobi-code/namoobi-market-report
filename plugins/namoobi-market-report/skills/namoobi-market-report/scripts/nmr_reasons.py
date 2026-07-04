#!/usr/bin/env python3
# nmr_reasons.py (req0) — 결측 셀에 정확한 사유/계산값을 채우고, KSVKOSPI 실측을 주입한다. merge 직후 실행.
import json, sys, os, glob
RD = sys.argv[1]
WORK = os.path.dirname(os.path.dirname(os.path.abspath(RD)))
d = json.load(open(RD, encoding="utf-8"))
m = d.get("markets") or {}
mac = m.get("macro") or {}
def empty(v): return v in (None, "", "-")
import re as _re
def _bad_release(v):
    # (req2/req3-fix) release(발표날짜) 칸이 '실제 발표일(날짜)' 도, '정기 발표/실시간' 표준 라벨도 아닌
    #   기관명(BLS·BEA·Census·ISM·FRED 등)만 들어찬 경우를 '교체 대상'으로 판정한다.
    #   기존엔 empty 일 때만 채워서, 기관명이 non-empty 로 들어오면 그대로 표에 찍혀 '발표날짜'가 날짜가 아니게 됐다.
    if empty(v): return True
    sv=str(v)
    if _re.search(r'\d{4}[-.\/]\d', sv): return False   # 연-월(-일) 형태 날짜 포함 → 유효
    if ('정기 발표' in sv) or ('실시간' in sv): return False  # 표준 라벨 → 유효
    return True  # 그 외(기관명만) → 교체
def loadj(name):
    for p in [os.path.join(WORK,name)]+glob.glob("/sessions/*/mnt/outputs/nmr_build/"+name)+glob.glob("/sessions/*/mnt/claudeCowork/_market_report_data/"+name):
        try: return json.load(open(p,encoding="utf-8"))
        except Exception: pass
    return {}
mom = loadj("nmr_mom.json")
MOM_KEY = [("Core CPI","core_cpi"),("Core PCE","core_pce"),("PCE","pce"),("PPI","ppi"),("CPI (헤드","cpi")]
INFL_REL = [("Core CPI","2026-06-10"),("Core PCE","2026-06-26"),("CPI","2026-06-10"),("PCE","2026-06-26"),("PPI","2026-06-11")]  # 물가 실제 발표일(5월 데이터→6월 발표)
infl = (mac.get("inflation") or {})
for r in (infl.get("rows") or []):
    nm = r.get("name") or ""
    bei = ("BEI" in nm or "기대인플레" in nm)
    if bei:
        lvl = (infl.get("infl_exp_10y") or {}).get("current")
        if (lvl is not None) and (empty(r.get("yoy")) or r.get("yoy") is None):
            r["yoy"] = "%.2f%% (수준)" % lvl
        r["mom"] = "수준지표(MoM 미해당)"
        if _bad_release(r.get("release")): r["release"] = "실시간(일별 갱신)"
        if empty(r.get("asof")): r["asof"] = (infl.get("infl_exp_10y") or {}).get("asof") or "실시간"
        continue
    cur = r.get("mom")
    needs = empty(cur) or (isinstance(cur,str) and ("미수집" in cur or "미집계" in cur))
    if needs:
        mk = next((k for lbl,k in MOM_KEY if nm.startswith(lbl) or lbl in nm), None)
        v = (mom.get(mk) or {}).get("mom") if mk else None
        if v is None:  # (req1 근본수정) DB 지수레벨(series_inflidx_*)로 전월비 직접 계산 — "-" 재발방지
            ik = "Core_CPI" if "Core CPI" in nm else ("Core_PCE" if "Core PCE" in nm else ("CPI" if nm.startswith("CPI") else ("PCE" if nm.startswith("PCE") else ("PPI" if "PPI" in nm else None))))
            if ik:
                _ix = loadj("db/series_inflidx_%s.json" % ik)
                _lv = (_ix.get("data") if isinstance(_ix,dict) else _ix) or []
                if isinstance(_lv,list) and len(_lv)>=2:
                    try: v = round((_lv[-1][1]/_lv[-2][1]-1)*100, 2)
                    except Exception: v = None
        if v is not None: r["mom"] = v
    # (req2-fix2) 물가표 발표날짜에 라벨 대신 '실제 발표일' 주입 (고용표와 동일하게 날짜로 표기)
    #   5월 데이터의 표준 미국 발표일정: CPI 06-10(수)·PPI 06-11(목)·PCE 06-26(금). 발표월 이동 시 갱신 대상.
    if _bad_release(r.get("release")):
        r["release"] = next((v for k,v in INFL_REL if k in nm), "정기 발표(BLS/BEA)")
EMP_REL = [("실업수당","정기 발표(매주 목)"),("청구","정기 발표(매주 목)"),("NFP","2026-06-05"),("실업률","2026-06-05"),("소매판매","2026-06-17"),("ISM 제조","2026-06-01"),("ISM 서비","2026-06-03"),("GDP","2026-06-26")]
for r in ((mac.get("employment") or {}).get("rows") or []):
    if _bad_release(r.get("release")):
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
