# -*- coding: utf-8 -*-
"""
krx_market_snapshot.py — 【req1: 웹서치 대체】 KRX OPEN API 공식 국내 시장데이터 스냅샷.

시황 리포트의 국내 파트에서 그동안 웹서치/스크래핑으로 채우던 값을 KRX 공식값으로 대체한다.
  · 지수    : 코스피 / 코스닥 / 코스피 200            (idx/kospi_dd_trd, idx/kosdaq_dd_trd)
  · 변동성  : VKOSPI(코스피200 변동성지수)            (idx/drvprod_dd_trd)
  · 섹터    : 코스피200 업종지수 등락률 상·하위        (idx/kospi_dd_trd)
  · 금리    : 국고채 종가수익률(3/5/10/30년)          (bon/kts_bydd_trd)
  · 상품    : KRX 금현물                              (gen/gold_bydd_trd)
  · 수급보조: ETF 거래대금 상위                        (etp/etf_bydd_trd)

출력: nmr_krx_market.json  (기본 ./nmr_krx_market.json — Phase1 산출물과 동일 규약)
휴장일/키부재/네트워크 오류 시에도 예외를 던지지 않고 빈 값으로 종료(완전 비차단).

주의: 글로벌 지표(S&P500·나스닥·WTI·달러·미국채)는 KRX 범위 밖 → 기존 소스 유지.
      gen/gold·oil 은 '국내가격'이라 글로벌 원자재의 대체가 아니라 보조지표다.
"""
import json
import os
import sys

from krx_openapi import API_KEY, call, num, business_days

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.getcwd(), "nmr_krx_market.json")


def _latest_dates(k=6):
    return business_days(12)[:k]


def _first(rows, key, value):
    for r in rows:
        if (r.get(key) or "").strip() == value:
            return r
    return None


def build():
    out = {"source": "KRX OPEN API (openapi.krx.co.kr)", "asof": None,
           "indices": [], "vkospi": None, "sector_top": [], "sector_bottom": [],
           "rates": [], "gold": None, "etf_top": []}
    if not API_KEY:
        out["error"] = "KRX_API_KEY 없음 → skip"
        return out

    d = None
    idx = []
    for cand in _latest_dates():
        idx = call("idx", "kospi_dd_trd", cand)
        if idx:
            d = cand
            break
    if not d:
        out["error"] = "최근 영업일 데이터 없음"
        return out
    out["asof"] = f"{d[:4]}-{d[4:6]}-{d[6:8]}"

    # 지수: 코스피 / 코스피 200
    for nm in ("코스피", "코스피 200"):
        r = _first(idx, "IDX_NM", nm)
        if r:
            out["indices"].append({"name": nm, "close": num(r.get("CLSPRC_IDX")),
                                   "chg_pct": num(r.get("FLUC_RT")),
                                   "value": num(r.get("ACC_TRDVAL"))})
    ksq = call("idx", "kosdaq_dd_trd", d)
    r = _first(ksq, "IDX_NM", "코스닥")
    if r:
        out["indices"].append({"name": "코스닥", "close": num(r.get("CLSPRC_IDX")),
                               "chg_pct": num(r.get("FLUC_RT")),
                               "value": num(r.get("ACC_TRDVAL"))})

    # VKOSPI + 섹터(코스피200 업종)
    dv = call("idx", "drvprod_dd_trd", d)
    r = _first(dv, "IDX_NM", "코스피 200 변동성지수")
    if r:
        out["vkospi"] = {"close": num(r.get("CLSPRC_IDX")), "chg_pct": num(r.get("FLUC_RT"))}

    sect = []
    for r in idx:
        nm = (r.get("IDX_NM") or "").strip()
        if not nm.startswith("코스피 200 ") or "비중상한" in nm or "TOP" in nm or "지수" == nm[-2:]:
            continue
        c = num(r.get("FLUC_RT"))
        if c is not None:
            sect.append({"name": nm.replace("코스피 200 ", ""), "chg_pct": c})
    sect.sort(key=lambda x: -x["chg_pct"])
    out["sector_top"], out["sector_bottom"] = sect[:3], sect[-3:][::-1]

    # 국고채 수익률
    for r in call("bon", "kts_bydd_trd", d):
        nm = (r.get("ISU_NM") or "")
        yd = num(r.get("CLSPRC_YD"))
        if yd is not None:
            out["rates"].append({"name": nm, "yield": yd,
                                 "chg": num(r.get("CMPPREVDD_PRC"))})

    # KRX 금현물
    for r in call("gen", "gold_bydd_trd", d):
        if "1" in (r.get("ISU_NM") or "") or not out["gold"]:
            out["gold"] = {"name": (r.get("ISU_NM") or "").strip(),
                           "close": num(r.get("TDD_CLSPRC")), "chg_pct": num(r.get("FLUC_RT"))}
            break

    # ETF 거래대금 상위(국내 수급 보조)
    etf = []
    for r in call("etp", "etf_bydd_trd", d):
        v = num(r.get("ACC_TRDVAL"))
        if v:
            etf.append({"name": (r.get("ISU_NM") or "").strip(), "value": v,
                        "chg_pct": num(r.get("FLUC_RT")), "nav": num(r.get("NAV")),
                        "close": num(r.get("TDD_CLSPRC"))})
    etf.sort(key=lambda x: -x["value"])
    for e in etf[:5]:
        if e["nav"] and e["close"]:
            e["disparity_pct"] = round((e["close"] / e["nav"] - 1) * 100, 2)   # 괴리율
    out["etf_top"] = etf[:5]
    return out


if __name__ == "__main__":
    try:
        data = build()
    except Exception as e:
        data = {"error": repr(e)[:120]}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("krx_market_snapshot: wrote", OUT, "| asof:", data.get("asof"), "| err:", data.get("error"))
