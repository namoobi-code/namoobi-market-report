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
    for p in ([os.path.join(WORK,name)]+glob.glob("/sessions/*/mnt/outputs/nmr_build/"+name)
             +glob.glob("/sessions/*/mnt/claudeCowork/namoobi-market-report-server/"+name)   # DB 정본(db/*.json)
             +glob.glob("/sessions/*/mnt/claudeCowork/namoobi-market-report-server/data/"+name)):
        try: return json.load(open(p,encoding="utf-8"))
        except Exception: pass
    return {}
mom = loadj("nmr_mom.json")
MOM_KEY = [("Core CPI","core_cpi"),("Core PCE","core_pce"),("PCE","pce"),("PPI","ppi"),("CPI (헤드","cpi")]
# (req3·req4 2026-07-19 근본수정) 발표일 하드코딩 폐지 — fetch_macro 가 FRED release/dates 로 실측한
#   nmr_reldates.json 을 읽어 주입한다(하드코딩 날짜는 다음 달이 되면 반드시 틀어지는 구조였음).
_RELD = loadj("nmr_reldates.json")
def _rel(key):
    v = (_RELD.get(key) or {}) if isinstance(_RELD, dict) else {}
    return v.get("latest")
INFL_REL = [("Core CPI", _rel("cpi")), ("Core PCE", _rel("pce")), ("CPI", _rel("cpi")),
            ("PCE", _rel("pce")), ("PPI", _rel("ppi"))]
INFL_REL = [(k, v) for k, v in INFL_REL if v]  # 실측 없으면 라벨 폴백("정기 발표")
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
    # (req3 2026-07-19) FRED 실측 발표일이 있으면 기존값(옛 DB 잔존 날짜 포함)을 '항상' 실측으로 교체.
    _rv = next((v for k, v in INFL_REL if k in nm), None)
    if _rv:
        r["release"] = _rv
    elif _bad_release(r.get("release")):
        r["release"] = "정기 발표(BLS/BEA)"
# (req4 2026-07-19) 고용 발표일 = FRED 실측 + ISM 값·기준월 주입("-" 근절)
import datetime as _dt
def _biz_day(year, month, n):
    """해당 월의 n번째 영업일(주말 제외 — 미 연방공휴일 미반영 간이계산)."""
    d = _dt.date(year, month, 1); cnt = 0
    while True:
        if d.weekday() < 5:
            cnt += 1
            if cnt == n: return d.isoformat()
        d += _dt.timedelta(days=1)
def _ism_rel(asof, n):
    try:
        y, mth = int(str(asof)[:4]), int(str(asof)[5:7])
        mth += 1
        if mth > 12: y, mth = y + 1, 1
        return _biz_day(y, mth, n)
    except Exception: return None
_emp_series = (mac.get("series") or {}).get("employment") or {}
def _last_pair(key):
    arr = [x for x in (_emp_series.get(key) or []) if isinstance(x, (list, tuple)) and len(x) >= 2 and x[1] is not None]
    return arr[-1] if arr else (None, None)
EMP_REL = [("실업수당", _rel("claims") or "정기 발표(매주 목)"), ("청구", _rel("claims") or "정기 발표(매주 목)"),
           ("NFP", _rel("empsit")), ("실업률", _rel("empsit")), ("소매판매", _rel("retail")), ("GDP", _rel("gdp"))]
EMP_REL = [(k, v) for k, v in EMP_REL if v]
for r in ((mac.get("employment") or {}).get("rows") or []):
    nm = r.get("name") or ""
    # ISM 값·기준월이 비면 series 최신점으로 주입(값은 있는데 행이 비어 "-" 로 새는 문제 근본수정)
    if "ISM" in nm:
        _sk = "ism_mfg" if "제조" in nm else "ism_svc"
        _am, _av = _last_pair(_sk)
        if empty(r.get("value")) and _av is not None: r["value"] = _av
        if empty(r.get("asof")) and _am: r["asof"] = _am
        if _bad_release(r.get("release")) or True:
            _cr = _ism_rel(r.get("asof"), 1 if "제조" in nm else 3)
            if _cr: r["release"] = _cr
        continue
    # GDP 기준을 분기 표기로(예: 2026-01 → 2026 Q1)
    if "GDP" in nm and isinstance(r.get("asof"), str) and len(r["asof"]) >= 7:
        _qm = {"01": "Q1", "04": "Q2", "07": "Q3", "10": "Q4"}.get(r["asof"][5:7])
        if _qm: r["asof"] = r["asof"][:4] + " " + _qm
    _rv = next((v for k, v in EMP_REL if k in nm), None)
    if _rv and ("정기 발표" not in str(_rv)):
        r["release"] = _rv   # FRED 실측 발표일 — 옛 DB 잔존 날짜도 항상 교체
    elif _bad_release(r.get("release")):
        r["release"] = _rv or "정기 발표(BLS/BEA/ISM)"
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
            # (req3 2026-07-05) anchors 는 "가격"(1d=전일 종가)이라 1d_pct 키가 없음 → 일별 series 로 직전장 등락률을 직접 계산해 주입
            ser=[x for x in (vk.get("series") or []) if isinstance(x,(list,tuple)) and len(x)>=2 and x[1] is not None]
            if len(ser)>=3 and ser[-3][1]:
                r["prev_pct"]=round((ser[-2][1]/ser[-3][1]-1)*100,2)  # 직전장(2일 전→1일 전) 등락률 — 빌더 '1일' 칸
            elif r.get("1d_pct") is not None:
                r["prev_pct"]=r["1d_pct"]  # 최후 폴백(빈칸 방지)
            r["trend"]="실시간(investing.com KSVKOSPI 페이지 파싱) 1일~1년 전구간 반영"
        elif all(empty(r.get(k)) for k in ["1w_pct","1mo_pct","3mo_pct","6mo_pct","1y_pct"]):
            r["trend"]="현재값 실시간(CNBC) · 1주~1년 이력 미확보(소스 접근 차단)"
json.dump(d, open(RD,"w",encoding="utf-8"), ensure_ascii=False)
print("[nmr_reasons] req0 사유/계산값 + KSVKOSPI 실측 주입 완료")
# EOF — namoobi-market-report nmr_reasons
