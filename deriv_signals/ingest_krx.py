# -*- coding: utf-8 -*-
"""
KOSPI200 파생상품 수집 — 공공데이터포털(data.go.kr) '금융위원회_파생상품시세정보'.
  - 선물(getStockFuturesPriceInfo): 최근월(최다 OI) → 베이시스(clpr vs sptPrc), 미결제(opnint)
  - 옵션(getOptionsPriceInfo): 최다 OI 만기 → PCR(OI/vol), IV 스큐(iptVlty, 머니니스 기반)
API 키: config.DATA_GO_KR_KEY (환경변수 또는 secrets.env). 없으면 호출부에서 skip.
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


def ingest_krx_index(con, begin, end):
    """KOSPI200 실제 지수(금융위 지수시세정보) → prices_daily.spot_close 로 교체(ETF 대용 대신)."""
    rows = _call("getStockMarketIndex",
                 {"beginBasDt": begin, "endBasDt": end, "likeIdxNm": "코스피200", "n": 9999}, base=BASE_IDX)
    recs = []
    for it in rows:
        if (it.get("idxNm") or "").strip() != "코스피200":
            continue
        d = it.get("basDt")
        try:
            c = float(it.get("clpr"))
        except Exception:
            continue
        if d and c > 0:
            recs.append((KID, _ymd(d), c, None, None))
    if not recs:
        return 0  # 지수 조회 실패 시 기존(ETF) 유지
    con.execute("DELETE FROM prices_daily WHERE id=?", (KID,))  # ETF 대용 제거 → 실제 지수로 교체
    con.executemany("INSERT OR REPLACE INTO prices_daily(id,date,spot_close,future_close,vix_close) VALUES(?,?,?,?,?)", recs)
    con.commit(); log(con, "ingest_krx_index", len(recs))
    return len(recs)


def ingest_krx_futures(con, begin, end):
    """코스피200 선물 최근월(최다 OI) 일별 → basis_bp, oi. begin/end=YYYYMMDD."""
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
        spot_recs.append((KID, _ymd(d), spt, None, None))   # sptPrc = 실제 KOSPI200 지수(현물)
        n += 1
    if spot_recs:
        con.execute("DELETE FROM prices_daily WHERE id=?", (KID,))   # ETF 대용 제거 → 실제 지수로 교체
        con.executemany("INSERT OR REPLACE INTO prices_daily(id,date,spot_close,future_close,vix_close) VALUES(?,?,?,?,?)", spot_recs)
    con.commit(); log(con, "ingest_krx_futures", n)
    return n


def ingest_krx_options_day(con, basdt):
    """하루치 옵션 → 최다 OI 만기 → PCR(OI/vol) + IV스큐(머니니스). basdt=YYYYMMDD."""
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
    exp = max(exp_oi, key=exp_oi.get)              # 최다 OI 만기(프론트)
    C, P = byexp[exp]["C"], byexp[exp]["P"]
    coi = sum(x[2] for x in C); poi = sum(x[2] for x in P)
    cvol = sum(x[3] for x in C); pvol = sum(x[3] for x in P)
    pcr_oi = poi / coi if coi else None
    pcr_vol = pvol / cvol if cvol else None
    # 근월 만기 스케일 왜곡 제거(합리 범위 밖이면 무효)
    if pcr_oi is not None and not (0.2 <= pcr_oi <= 8):
        pcr_oi = None
    if pcr_vol is not None and not (0.05 <= pcr_vol <= 15):
        pcr_vol = None
    # IV 스큐: 최다 OI 콜 스트라이크를 ATM으로, 0.95×ATM 풋 IV − 1.05×ATM 콜 IV
    skew = None
    Cv = [(K, iv) for K, iv, oi, _ in C if iv > 0]
    Pv = [(K, iv) for K, iv, oi, _ in P if iv > 0]
    if Cv and Pv and C:
        katm = max(C, key=lambda x: x[2])[0]
        if katm:
            pput = min(Pv, key=lambda x: abs(x[0] - 0.95 * katm))[1]
            pcall = min(Cv, key=lambda x: abs(x[0] - 1.05 * katm))[1]
            skew = pput - pcall
    # 딜러 감마(GEX): 옵션체인 자체 ATM(katm) 기준
    gex = None
    if C and P:
        katm2 = max(C, key=lambda x: x[2])[0]
        try:
            ed = _dt.date(int(exp[:4]), int(exp[4:6]), 12)   # ~2nd Thu 근사
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


def ingest_krx(con, begin, end, opt_days=90):
    if not DATA_GO_KR_KEY:
        print("  DATA_GO_KR_KEY 없음 → KOSPI200 파생 skip"); return 0
    f = ingest_krx_futures(con, begin, end)   # 선물 sptPrc를 KOSPI200 실제 지수(현물)로 저장
    o = ingest_krx_options(con, _trading_dates(con, opt_days))
    return f + o


if __name__ == "__main__":
    from db import init_db, connect, publish_db
    from datetime import datetime, timedelta
    init_db(); con = connect()
    end = datetime.utcnow().strftime("%Y%m%d")
    begin = (datetime.utcnow() - timedelta(days=420)).strftime("%Y%m%d")
    print("KRX futures rows:", ingest_krx_futures(con, begin, end))
    con.close(); publish_db()
