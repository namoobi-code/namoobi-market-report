# -*- coding: utf-8 -*-
"""
ingest_krx_open.py — 【1차 소스, 무로그인】 KRX OPEN API 기반 KOSPI200 수집.

수집 항목
  · 현물   : idx/kospi_dd_trd      → IDX_NM '코스피 200' 의 CLSPRC_IDX (공식 지수)
  · 베이시스: drv/fut_bydd_trd     → 최근월물(코스피200/미니코스피 선물 중 만기 최근·OI 최대)
                                     basis_bp = (선물종가/SPOT_PRC - 1) × 10,000
  · 미결제 : drv/fut_bydd_trd      → 코스피200+미니 선물 ACC_OPNINT_QTY 합계
  · VKOSPI : idx/drvprod_dd_trd    → '코스피 200 변동성지수' CLSPRC_IDX  ★신규

옵션 PCR/IV스큐/GEX 를 여기서 산출하지 않는 이유:
  KRX 공식 옵션체인이라도 행사가 사다리가 현물을 커버하지 못하는 구간이 있어
  (예: 2026-07-02 현물 1,219.62 vs 최근월 행사가 상단 997.5) PCR 이 100 을 넘는 등
  값이 붕괴한다. → 변동성/공포 축은 KRX 가 공식 산출한 VKOSPI 로 대체하고,
  괴리율·공식 IV·공식 PCR 은 2차 레이어(ingest_krx_web.py, 로그인 세션 필요)에서 보강한다.
"""
import re
from db import log
from krx_openapi import API_KEY, call_range, num, ymd, business_days

KID = "KOSPI200"
_EXP = re.compile(r"\b(\d{6})\b")          # ISU_NM 내 만기 YYYYMM
FUT_PRODS = ("코스피200 선물", "미니코스피200 선물", "코스피200 F", "미니코스피 F")


def _is_kospi_fut(row):
    p = (row.get("PROD_NM") or "") + " " + (row.get("ISU_NM") or "")
    if "코스닥" in p or "섹터" in p or "KRX300" in p or "변동성" in p:
        return False
    return ("코스피200" in p) or ("미니코스피" in p)


def _parse_fut_day(rows):
    """하루치 선물 → (basis_bp, total_oi, spot). 스프레드(SP)·야간 제외."""
    cand, total_oi, spot = [], 0.0, None
    for r in rows:
        if not _is_kospi_fut(r):
            continue
        if (r.get("MKT_NM") or "") != "정규":
            continue
        isu = r.get("ISU_NM") or ""
        if " SP " in isu or isu.strip().split()[1:2] == ["SP"]:
            continue                                    # 스프레드 종목 제외
        clsp = num(r.get("TDD_CLSPRC"))
        sp = num(r.get("SPOT_PRC"))
        oi = num(r.get("ACC_OPNINT_QTY")) or 0.0
        if sp and sp > 0:
            spot = sp
        if not clsp or clsp <= 0 or not sp or sp <= 0 or oi <= 0:
            continue
        m = _EXP.search(isu)
        if not m:
            continue
        total_oi += oi
        cand.append((m.group(1), oi, (clsp / sp - 1.0) * 1e4))
    if not cand:
        return None, None, spot
    near = min(c[0] for c in cand)                       # 최근월
    front = [c for c in cand if c[0] == near]
    basis = max(front, key=lambda c: c[1])[2]            # 최근월 중 OI 최대 종목
    return basis, total_oi, spot


def ingest_krx_open(con, back_days=420):
    if not API_KEY:
        print("  KRX OPEN API 키 없음 → 1차 소스 skip (폴백 사용)")
        return 0
    dates = business_days(back_days)
    print(f"  KRX OPEN API 조회: {len(dates)} 영업일(캐시 우선)…")

    idx = call_range("idx", "kospi_dd_trd", dates)
    fut = call_range("drv", "fut_bydd_trd", dates)
    vix = call_range("idx", "drvprod_dd_trd", dates)

    spot_recs, deriv_recs = [], []
    for d in sorted(set(idx) | set(fut) | set(vix)):
        # 현물(공식 코스피200 지수)
        s = None
        for r in idx.get(d, []):
            if (r.get("IDX_NM") or "").strip() == "코스피 200":
                s = num(r.get("CLSPRC_IDX"))
                break
        basis, oi, fspot = _parse_fut_day(fut.get(d, []))
        if s is None:
            s = fspot                                    # 지수 결측 시 선물의 SPOT_PRC 로 보완
        # VKOSPI
        vk = None
        for r in vix.get(d, []):
            if (r.get("IDX_NM") or "").strip() == "코스피 200 변동성지수":
                vk = num(r.get("CLSPRC_IDX"))
                break
        if s:
            spot_recs.append((KID, ymd(d), s, None, None))
        if basis is not None or oi or vk is not None:
            deriv_recs.append((KID, ymd(d), basis, oi or None, vk))

    if spot_recs:
        con.execute("DELETE FROM prices_daily WHERE id=?", (KID,))     # ETF 대용 제거 → 공식 지수
        con.executemany(
            "INSERT OR REPLACE INTO prices_daily(id,date,spot_close,future_close,vix_close) VALUES(?,?,?,?,?)",
            spot_recs)
    for rec in deriv_recs:
        con.execute("""INSERT INTO kr_derivatives_daily(id,date,basis_bp,oi,vkospi) VALUES(?,?,?,?,?)
                       ON CONFLICT(id,date) DO UPDATE SET
                         basis_bp=COALESCE(excluded.basis_bp, kr_derivatives_daily.basis_bp),
                         oi      =COALESCE(excluded.oi,       kr_derivatives_daily.oi),
                         vkospi  =COALESCE(excluded.vkospi,   kr_derivatives_daily.vkospi)""", rec)
    con.commit()
    log(con, "ingest_krx_open", len(deriv_recs), f"spot={len(spot_recs)}")
    nb = sum(1 for r in deriv_recs if r[2] is not None)
    nv = sum(1 for r in deriv_recs if r[4] is not None)
    print(f"  KRX OPEN API ✓ 현물 {len(spot_recs)}일 · 베이시스 {nb}일 · VKOSPI {nv}일")
    return len(deriv_recs)


if __name__ == "__main__":
    from db import init_db, connect, publish_db
    init_db()
    con = connect()
    ingest_krx_open(con, 420)
    con.close()
    publish_db()
