# -*- coding: utf-8 -*-
"""
KOSPI200 파생 수집 디스패처.

  1차 (무로그인·안정) KRX OPEN API  → ingest_krx_open.py
        공식 코스피200 지수 · 최근월 베이시스 · 미결제약정 · VKOSPI
  2차 (로그인 세션 O)  data.krx     → ingest_krx_web.py
        괴리율 · 공식 IV · 공식 P/C Ratio (쿠키 없으면 조용히 skip)
  폴백(1차 실패 시)    네이버 / data.go.kr(금융위 파생상품시세정보)
        기존 경로 유지 — 리포트가 절대 비지 않도록.
"""
import warnings, urllib.request, urllib.parse, json, time, collections, math, datetime as _dt
import pandas as pd
from config import DATA_GO_KR_KEY
from db import log

warnings.filterwarnings("ignore")
BASE = "https://apis.data.go.kr/1160100/service/GetDerivativeProductInfoService"
BASE_IDX = "https://apis.data.go.kr/1160100/service/GetMarketIndexInfoService"
KID = "KOSPI200"


def _f(x):
    try:
        return None if x is None or (isinstance(x, float) and pd.isna(x)) else float(x)
    except Exception:
        return None


def _bs_gamma(S, K, T, r, sigma):
    if not (sigma > 0 and T > 0 and S > 0 and K > 0):
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    return math.exp(-0.5 * d1 * d1) / (S * sigma * math.sqrt(T) * math.sqrt(2 * math.pi))


def _call(op, params, tries=3, base=BASE):
    p = {"serviceKey": DATA_GO_KR_KEY, "resultType": "json",
         "numOfRows": params.pop("n", 1000), "pageNo": params.pop("p", 1)}
    p.update(params)
    url = f"{base}/{op}?" + urllib.parse.urlencode(p)
    for t in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as r:
                body = json.loads(r.read().decode("utf-8", "ignore"))["response"]["body"]
                it = (body.get("items") or {})
                it = it.get("item") if isinstance(it, dict) else None
                return it if isinstance(it, list) else ([it] if it else [])
        except Exception as e:
            if t == tries - 1:
                print("  data.go.kr err:", repr(e)[:70]); return []
            time.sleep(1.5)


def _ymd(d):  # 20260702 → 2026-07-02
    return f"{d[:4]}-{d[4:6]}-{d[6:]}"


def ingest_krx_futures(con, begin, end):
    """[폴백] 코스피200 선물 최근월(최다 OI) 일별 → basis_bp, oi."""
    rows = _call("getStockFuturesPriceInfo",
                 {"beginBasDt": begin, "endBasDt": end, "likeItmsNm": "코스피200 F", "n": 3000})
    byday = {}
    for it in rows:
        try:
            d = it["basDt"]; oi = float(it.get("opnint") or 0)
            clpr = float(it.get("clpr") or 0); spt = float(it.get("sptPrc") or 0)
            if clpr <= 0 or spt <= 0:
                continue
            if d not in byday or oi > byday[d][0]:
                byday[d] = (oi, (clpr / spt - 1.0) * 1e4, spt)
        except Exception:
            pass
    n = 0
    spot_recs = []
    for d, (oi, basis, spt) in byday.items():
        con.execute("""INSERT INTO kr_derivatives_daily(id,date,basis_bp,oi) VALUES(?,?,?,?)
                       ON CONFLICT(id,date) DO UPDATE SET basis_bp=excluded.basis_bp, oi=excluded.oi""",
                    (KID, _ymd(d), _f(basis), _f(oi)))
        spot_recs.append((KID, _ymd(d), spt, None, None))
        n += 1
    if spot_recs:
        con.execute("DELETE FROM prices_daily WHERE id=?", (KID,))
        con.executemany("INSERT OR REPLACE INTO prices_daily(id,date,spot_close,future_close,vix_close) VALUES(?,?,?,?,?)", spot_recs)
    con.commit(); log(con, "ingest_krx_futures", n)
    return n


def ingest_krx_options_day(con, basdt):
    """[폴백] 하루치 옵션 → 최다 OI 만기 → PCR(OI/vol) + IV스큐(머니니스)."""
    rows = _call("getOptionsPriceInfo", {"basDt": basdt, "likeItmsNm": "코스피200", "n": 9999})
    if not rows:
        return False
    exp_oi = collections.defaultdict(float)
    byexp = collections.defaultdict(lambda: {"C": [], "P": []})
    for it in rows:
        try:
            parts = it["itmsNm"].split()          # 코스피200 C 202607 545.0
            cp, exp, K = parts[1], parts[2], float(parts[-1])
            if cp not in ("C", "P"):
                continue
            oi = float(it.get("opnint") or 0); vol = float(it.get("trqu") or 0)
            iv = float(it.get("iptVlty") or 0)
            exp_oi[exp] += oi
            byexp[exp][cp].append((K, iv, oi, vol))
        except Exception:
            pass
    if not exp_oi:
        return False
    exp = max(exp_oi, key=exp_oi.get)
    C, P = byexp[exp]["C"], byexp[exp]["P"]
    coi = sum(x[2] for x in C); poi = sum(x[2] for x in P)
    cvol = sum(x[3] for x in C); pvol = sum(x[3] for x in P)
    pcr_oi = poi / coi if coi else None
    pcr_vol = pvol / cvol if cvol else None
    # 옵션체인 행사가 사다리가 현물을 커버하지 못하면 PCR 이 붕괴 → 합리 범위 밖은 무효 처리
    if pcr_oi is not None and not (0.2 <= pcr_oi <= 8):
        pcr_oi = None
    if pcr_vol is not None and not (0.05 <= pcr_vol <= 15):
        pcr_vol = None
    skew = None
    Cv = [(K, iv) for K, iv, oi, _ in C if iv > 0]
    Pv = [(K, iv) for K, iv, oi, _ in P if iv > 0]
    if Cv and Pv and C:
        katm = max(C, key=lambda x: x[2])[0]
        if katm:
            pput = min(Pv, key=lambda x: abs(x[0] - 0.95 * katm))[1]
            pcall = min(Cv, key=lambda x: abs(x[0] - 1.05 * katm))[1]
            skew = pput - pcall
    gex = None
    if C and P:
        katm2 = max(C, key=lambda x: x[2])[0]
        try:
            ed = _dt.date(int(exp[:4]), int(exp[4:6]), 12)
            bd = _dt.date(int(basdt[:4]), int(basdt[4:6]), int(basdt[6:8]))
            T = max((ed - bd).days, 1) / 365.0
            cg = sum(_bs_gamma(katm2, K, T, 0.03, iv) * oi for K, iv, oi, _ in C if iv > 0)
            pg = sum(_bs_gamma(katm2, K, T, 0.03, iv) * oi for K, iv, oi, _ in P if iv > 0)
            gex = (cg - pg) * katm2 * katm2 * 0.01
        except Exception:
            gex = None
    con.execute("""INSERT INTO kr_derivatives_daily(id,date,pcr_oi,pcr_vol,iv_skew_25d,gex) VALUES(?,?,?,?,?,?)
                   ON CONFLICT(id,date) DO UPDATE SET pcr_oi=excluded.pcr_oi,
                     pcr_vol=excluded.pcr_vol, iv_skew_25d=excluded.iv_skew_25d, gex=excluded.gex""",
                (KID, _ymd(basdt), _f(pcr_oi), _f(pcr_vol), _f(skew), _f(gex)))
    con.commit()
    return True


def _trading_dates(con, days):
    df = pd.read_sql("SELECT DISTINCT date FROM prices_daily WHERE id='KOSPI200' ORDER BY date DESC", con)
    return [d.replace("-", "") for d in df["date"].head(days)]


def ingest_krx_options(con, dates):
    n = 0
    for d in dates:
        if ingest_krx_options_day(con, d):
            n += 1
    log(con, "ingest_krx_options", n)
    return n


def ingest_krx_naver_basis(con, back_days=420):
    """[폴백] 네이버 KOSPI200 선물(FUT)·지수(KPI200) 일별 종가 → basis_bp."""
    import urllib.request as _u, re as _re
    def _dayseries(code, pages):
        out = {}
        for p in range(1, pages + 1):
            try:
                r = _u.urlopen(_u.Request(
                    "https://finance.naver.com/sise/sise_index_day.naver?code=%s&page=%d" % (code, p),
                    headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com"}),
                    timeout=15).read().decode("euc-kr", "replace")
            except Exception:
                break
            hits = _re.findall(r'<td class="date">(\d{4}\.\d{2}\.\d{2})</td>\s*<td class="number_1">([\d,]+\.\d+)</td>', r)
            if not hits:
                break
            for d, v in hits:
                out[d.replace(".", "-")] = float(v.replace(",", ""))
        return out
    pages = max(2, back_days // 6 + 2)
    fut = _dayseries("FUT", pages)
    idx = _dayseries("KPI200", pages)
    n = 0
    for d in sorted(set(fut) & set(idx)):
        if not idx[d]:
            continue
        basis = round((fut[d] - idx[d]) / idx[d] * 10000, 1)
        con.execute("""INSERT INTO kr_derivatives_daily(id,date,basis_bp) VALUES(?,?,?)
                       ON CONFLICT(id,date) DO UPDATE SET basis_bp=excluded.basis_bp""",
                    (KID, d, basis))
        n += 1
    con.commit()
    try:
        log(con, "ingest_krx_naver_basis", n)
    except Exception:
        pass
    print("  KRX(naver) KOSPI200 basis rows:", n)
    return n


def ingest_krx(con, begin, end, opt_days=90):
    """1차(KRX OPEN API) → 2차(data.krx 보강) → 실패 시 폴백."""
    n = 0
    try:
        from ingest_krx_open import ingest_krx_open
        n = ingest_krx_open(con, 420)
    except Exception as e:
        print("  KRX OPEN API 실패:", repr(e)[:90])
        n = 0

    try:
        from ingest_krx_web import ingest_krx_web
        n += ingest_krx_web(con, 420)
    except Exception as e:
        print("  data.krx 2차 보강 skip:", repr(e)[:70])

    if n:
        return n

    print("  → 폴백 경로(네이버 / data.go.kr) 사용")
    n = ingest_krx_naver_basis(con, 420)
    if not DATA_GO_KR_KEY:
        print("  DATA_GO_KR_KEY 없음 → data.go.kr 선물/옵션 skip (네이버 베이시스만 수집)")
        return n
    f = ingest_krx_futures(con, begin, end)
    o = ingest_krx_options(con, _trading_dates(con, opt_days))
    return n + f + o


if __name__ == "__main__":
    from db import init_db, connect, publish_db
    from datetime import datetime, timedelta
    init_db(); con = connect()
    end = datetime.utcnow().strftime("%Y%m%d")
    begin = (datetime.utcnow() - timedelta(days=420)).strftime("%Y%m%d")
    print("KOSPI200 rows:", ingest_krx(con, begin, end))
    con.close(); publish_db()
