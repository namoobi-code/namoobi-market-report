# -*- coding: utf-8 -*-
"""
KOSPI200 파생 수집 디스패처.

  1차 (무로그인·안정) KRX OPEN API  → ingest_krx_open.py
        공식 코스피200 지수 · 최근월 베이시스 · 미결제약정 · VKOSPI
  2차 (로그인 세션 O)  data.krx     → ingest_krx_web.py
        괴리율 · 공식 IV · 공식 P/C Ratio (쿠키 없으면 조용히 skip)
  T+0 (항상 실행)      네이버 m.stock API → ingest_naver_t0()
        KRX 는 T+1 공표 → 당일 현물(KPI200)·선물(FUT)·베이시스를 네이버로 브리지
        (+ vkospi_override.json 있으면 VKOSPI 당일값 주입)
  폴백(1차 실패 시)    네이버 / data.go.kr(금융위 파생상품시세정보)
        기존 경로 유지 — 리포트가 절대 비지 않도록.
"""
import re
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


def ingest_naver_t0(con):
    """【T+0 레이어, 항상 실행】 네이버 m.stock API로 KRX 미공표 구간(당일 포함) 보강.

    배경(2026-07-13 실측): KRX OPEN API 는 T+1 공표(당일 23시에도 basDd=당일 → 0행)라
    당일 급변(예: 코스피 -8.9%)을 3.1.13 이 구조적으로 못 봤다. 반면 네이버는
      m.stock.naver.com/api/index/FUT/price    → 코스피200 '선물' 당일 OHLC (제공됨 — 종전 "미제공" 판단은 오류)
      m.stock.naver.com/api/index/KPI200/price → 코스피200 현물 당일 종가
    를 T+0 제공 → 당일 현물·선물·베이시스 산출 가능. VKOSPI 만 네이버에 없음(override 참고).

    정본 유지: KRX 최신일 '이후' 날짜만 채운다. 다음 영업일 ingest_krx_open 이
    prices_daily 는 DELETE+재적재, kr_derivatives_daily 는 COALESCE(excluded 우선)로
    공식값을 자동 덮어쓴다(네이버 값은 하루짜리 임시 브리지).
    """
    import urllib.request as _u

    def _series(code, pages=2, size=30):
        out = {}
        for p in range(1, pages + 1):
            url = f"https://m.stock.naver.com/api/index/{code}/price?pageSize={size}&page={p}"
            try:
                rows = json.loads(_u.urlopen(_u.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
                                             timeout=15).read().decode("utf-8", "ignore"))
            except Exception:
                break
            if not isinstance(rows, list) or not rows:
                break
            for r in rows:
                try:
                    out[str(r["localTradedAt"])[:10]] = float(str(r["closePrice"]).replace(",", ""))
                except Exception:
                    pass
        return out

    fut, idx = _series("FUT"), _series("KPI200")
    common = sorted(set(fut) & set(idx))
    if not common:
        print("  네이버 T+0: 응답 없음 → skip")
        return 0
    last_b = (con.execute("SELECT max(date) FROM kr_derivatives_daily WHERE id=? AND basis_bp IS NOT NULL",
                          (KID,)).fetchone() or [None])[0]
    last_p = (con.execute("SELECT max(date) FROM prices_daily WHERE id=?", (KID,)).fetchone() or [None])[0]
    n = 0
    for d in common:
        if not idx[d] or idx[d] <= 0:
            continue
        new_b = (last_b is None) or (d > last_b)
        new_p = (last_p is None) or (d > last_p)
        if not (new_b or new_p):
            continue
        if new_b:
            basis = round((fut[d] / idx[d] - 1.0) * 1e4, 1)
            con.execute("""INSERT INTO kr_derivatives_daily(id,date,basis_bp) VALUES(?,?,?)
                           ON CONFLICT(id,date) DO UPDATE SET basis_bp=excluded.basis_bp""",
                        (KID, d, basis))
        if new_p:
            con.execute("INSERT OR REPLACE INTO prices_daily(id,date,spot_close,future_close,vix_close) "
                        "VALUES(?,?,?,?,NULL)", (KID, d, idx[d], fut[d]))
        n += 1
    con.commit()
    try:
        log(con, "ingest_naver_t0", n)
    except Exception:
        pass
    if n:
        print(f"  네이버 T+0 ✓ {n}일 보강(KRX 공표 전 구간: 현물 {idx[common[-1]]:,.2f} · "
              f"선물 {fut[common[-1]]:,.2f} · 베이시스)")
    else:
        print("  네이버 T+0: 신규 없음(KRX 최신 상태)")
    return n


def _krx_opt_base(con):
    """KRX T+1 코스피200 옵션 근월물 행사가별 OI — KIS 가 훑지 않은 '꼬리' 행사가를 채우는 기준."""
    try:
        from krx_openapi import call_range
        import datetime as _d
        ds = [(_d.date.today() - _d.timedelta(days=i)).strftime("%Y%m%d") for i in range(1, 6)]
        r = call_range("drv", "opt_bydd_trd", ds)
    except Exception:
        return None
    for d in sorted(r, reverse=True):
        rows = [x for x in (r[d] or [])
                if str(x.get("PROD_NM", "")).strip() == "코스피200 옵션"
                and "야간" not in str(x.get("ISU_NM", ""))]
        if not rows:
            continue
        ym = min(re.findall(r"20\d{4}", " ".join(str(x.get("ISU_NM", "")) for x in rows)) or ["0"])
        base = {"call": {}, "put": {}}
        for x in rows:
            nm = str(x.get("ISU_NM", ""))
            if ym not in nm:
                continue
            m = re.findall(r"([\d,]+\.\d+)", nm)
            if not m:
                continue
            k = _f(m[-1])
            v = _f(x.get("ACC_OPNINT_QTY"))
            side = "call" if x.get("RGHT_TP_NM") == "CALL" else "put"
            base[side][k] = v
        if base["call"] or base["put"]:
            print(f"  [KRX 기준] {d} {ym}물 행사가 {len(base['call'])}개 (콜 OI {sum(base['call'].values()):,.0f} / 풋 {sum(base['put'].values()):,.0f})")
            return base
    return None


def ingest_kis_t0(con):
    """【T+0 · 최상위】 KIS Open API — 미결제약정·PCR·IV스큐·딜러감마.

    KRX OPEN API 는 파생 전 항목이 T+1 이라 폭락 당일 시그널이 하루 늦는다. KIS 는 HTS 와 같은
    당일 데이터를 준다(실측: KRX 7/10 K=1145 풋 OI 94 → KIS 7/13 119 로 정확히 이어짐).

    ⚠️ 옵션 전광판(display-board-callput)은 쓰지 않는다 — 행사가 '최고가부터 100행'만 주고
       연속조회가 없어, 지수가 급락하면 ATM 이 창 밖으로 나가 PCR 이 쓰레기값이 된다(실측).
       대신 행사가별 개별 조회로 체인을 훑되, KRX T+1 OI 상위 99% 행사가만 훑고
       나머지 꼬리는 KRX 값으로 채워 '전 체인 PCR' 을 T+0 정확도로 만든다.

    키(SECURITY/.env)가 없으면 조용히 skip → 기존 KRX T+1 경로가 그대로 돈다.
    """
    import sys as _sys
    from pathlib import Path as _Path
    try:
        _sys.path.insert(0, str(_Path(__file__).resolve().parent))
        import kis_api
        if not kis_api._creds():
            print("  [KIS] 키 없음 — skip (KRX T+1 유지)")
            return 0
    except Exception as e:
        print("  [KIS] 모듈 로드 실패(비차단):", type(e).__name__)
        return 0

    n = 0
    spot = None
    try:
        fo = kis_api.futures_oi()
        if fo and fo.get("oi"):
            spot = fo["price"]
            con.execute("""INSERT INTO kr_derivatives_daily(id,date,oi)
                           VALUES(?,?,?)
                           ON CONFLICT(id,date) DO UPDATE SET oi=excluded.oi""",
                        (KID, fo["asof"], fo["oi"]))
            con.commit(); n += 1
            print(f"  [KIS T+0] 선물 {fo['expiry']} 미결제 {fo['oi']:,.0f} (증감 {fo['oi_chg']:+,.0f}) · 현재가 {fo['price']}")
    except Exception as e:
        print("  [KIS] 선물 skip:", repr(e)[:80])

    if spot is None:
        # 선물 한 방이 실패했다면 KIS 가 죽은 것(키 차단·장애). 옵션 체인(수백 콜)은 시도조차 하지 않는다.
        print("  [KIS] 선물 응답 없음 → 옵션 체인 skip (KRX T+1 유지)")
        return n
    try:
        base = _krx_opt_base(con)
        # 커버리지 90%: OI 상위 90% 행사가만 T+0, 꼬리는 KRX 보정. 신규 3일창(2.4건/초)에서 ~80초.
        oc = kis_api.option_chain(spot=spot, krx_base=base, coverage=0.90, max_calls=220)
        # (장전 가드 · 2026-07-17) KRX 파생 정규장(08:45~) 전 실행이면 거래량·IV 기반 지표는 구조적으로 왜곡
        #   (당일 거래량≈0 → PCR(Vol) 퇴화, 이론가 IV → 스큐·GEX 왜곡. 실측: 06:22 실행에서 PCR(Vol) 4,199).
        #   → pcr_vol/iv_skew/gex 는 기록하지 않는다(COALESCE 가 기존값 유지). OI·PCR(OI) 는 전일 정산 연속이라 T+0 유효.
        if oc:
            _kst = _dt.datetime.utcnow() + _dt.timedelta(hours=9)
            if (_kst.hour, _kst.minute) < (9, 15):
                print(f"  [KIS] 장전({_kst:%H:%M} KST) — PCR(Vol)/IV스큐/GEX 미기록(거래량·IV 왜곡), OI·PCR(OI)만 T+0 기록")
                oc["pcr_vol"] = None; oc["iv_skew"] = None; oc["gex"] = None
        if oc and oc.get("pcr_oi"):
            con.execute("""INSERT INTO kr_derivatives_daily(id,date,pcr_oi,pcr_vol,iv_skew_25d,gex)
                           VALUES(?,?,?,?,?,?)
                           ON CONFLICT(id,date) DO UPDATE SET
                             pcr_oi      = excluded.pcr_oi,
                             pcr_vol     = COALESCE(excluded.pcr_vol,     kr_derivatives_daily.pcr_vol),
                             iv_skew_25d = COALESCE(excluded.iv_skew_25d, kr_derivatives_daily.iv_skew_25d),
                             gex         = COALESCE(excluded.gex,         kr_derivatives_daily.gex)""",
                        (KID, oc["asof"], oc["pcr_oi"], oc.get("pcr_vol"),
                         oc.get("iv_skew"), oc.get("gex")))
            con.commit(); n += 1
            print(f"  [KIS T+0] {oc['expiry']}물 PCR(OI) {oc['pcr_oi']} · PCR(거래량) {oc.get('pcr_vol')} "
                  f"· IV스큐 {oc.get('iv_skew')} · GEX {oc.get('gex')}억  "
                  f"[{oc['scanned']}/{oc['strikes']} 행사가 T+0, {oc['src']}]")
    except Exception as e:
        print("  [KIS] 옵션 skip:", repr(e)[:80])

    if n:
        log(con, "ingest_kis_t0", n)
    return n


def ingest_server_close(con):
    """【서버 마감 캡처 병합 · 2026-07-17】 서버 cron(15:48 KST, kis_close_capture.py)이 기록한
    장 마감 KIS 지표(~/namoobi/data/kis_close.json)를 내려받아 해당 날짜의 NULL 셀만 채운다.

    06시 예약 실행은 장전 가드로 PCR(Vol)/IV스큐/GEX 를 비우므로, 이 병합이 없으면 새벽
    리포트에서 세 지표가 영구 공란이 된다. 기존 실측(장중 수동 실행 등)은 건드리지 않는다
    (COALESCE 기존값 우선). 배포키 없음·서버 다운·파일 없음 전부 비차단 skip.
    """
    import os as _os, glob as _glob, json as _json, subprocess as _sp, tempfile as _tf, shutil as _sh
    key = None
    for pat in ("/sessions/*/mnt/*/SECURITY/nmr_deploy_key", "D:/claudeCowork/SECURITY/nmr_deploy_key"):
        g = _glob.glob(pat)
        if g:
            key = g[0]; break
    if not key:
        return 0
    try:
        tk = _os.path.join(_tf.gettempdir(), "nmr_dk_pull")
        _sh.copy(key, tk); _os.chmod(tk, 0o600)
        r = _sp.run(["ssh", "-i", tk, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
                     "ubuntu@141.147.160.13",
                     "cat ~/namoobi/data/kis_close.json 2>/dev/null; echo __NMRSEP__; cat ~/namoobi/data/us_options_close.json 2>/dev/null"],
                    capture_output=True, text=True, timeout=30)
        try:
            _os.unlink(tk)
        except Exception:
            pass
        part_kr, part_us = ((r.stdout or "").split("__NMRSEP__") + [""])[:2]
        # ── 미국 옵션 서버 캡처 병합(2026-07-17): yfinance 옵션체인은 백필 불가 —
        #    PC 미실행일의 options_daily 공백을 서버 cron(06:40 KST)이 메운 것을 INSERT OR IGNORE 로 흡수.
        nus = 0
        try:
            for row in (_json.loads(part_us).get("rows") or []):
                cur = con.execute("SELECT 1 FROM options_daily WHERE id=? AND date=?",
                                  (row.get("id"), row.get("date"))).fetchone()
                if cur:
                    continue
                con.execute("""INSERT OR IGNORE INTO options_daily
                               (id,date,expiry_used,dte,pcr_oi,pcr_vol,iv_atm,iv_skew_25d,delta_imbalance,gex)
                               VALUES(?,?,?,?,?,?,?,?,?,?)""",
                            tuple(row.get(k) for k in ("id","date","expiry_used","dte","pcr_oi","pcr_vol",
                                                        "iv_atm","iv_skew_25d","delta_imbalance","gex")))
                nus += 1
            if nus:
                con.commit()
                print(f"  [US옵션 서버캡처] 공백 {nus}행 병합(options_daily)")
        except Exception as _ue:
            print("  [US옵션 서버캡처] skip(비차단):", repr(_ue)[:50])
        if r.returncode != 0 or not part_kr.strip():
            print("  [KIS 서버마감] 서버 캡처본 없음 — skip")
            return nus
        d = _json.loads(part_kr)
    except Exception as e:
        print("  [KIS 서버마감] skip(비차단):", repr(e)[:60])
        return 0
    date = d.get("date")
    if not date:
        return nus
    con.execute("""INSERT INTO kr_derivatives_daily(id,date,pcr_vol,iv_skew_25d,gex,oi,vkospi)
                   VALUES(?,?,?,?,?,?,?)
                   ON CONFLICT(id,date) DO UPDATE SET
                     pcr_vol     = COALESCE(kr_derivatives_daily.pcr_vol,     excluded.pcr_vol),
                     iv_skew_25d = COALESCE(kr_derivatives_daily.iv_skew_25d, excluded.iv_skew_25d),
                     gex         = COALESCE(kr_derivatives_daily.gex,         excluded.gex),
                     oi          = COALESCE(kr_derivatives_daily.oi,          excluded.oi),
                     vkospi      = COALESCE(kr_derivatives_daily.vkospi,      excluded.vkospi)""",
                (KID, date, d.get("pcr_vol"), d.get("iv_skew"), d.get("gex"), d.get("oi"), d.get("vkospi")))
    con.commit()
    print(f"  [KIS 서버마감] {date} 병합 — PCR(Vol) {d.get('pcr_vol')} · IV스큐 {d.get('iv_skew')} · GEX {d.get('gex')} · VKOSPI {d.get('vkospi')}")
    log(con, "ingest_server_close", 1 + nus)
    return 1 + nus


def ingest_vkospi_cnbc(con):
    """【T+0 자동】 VKOSPI 당일값 — CNBC .KSVKOSPI (무인증·실시간).

    ⚠️ 종전 주석은 "네이버·야후에 VKOSPI 가 없어 T+0 무료 소스 부재"라며 수동 override 만
       받았다. 사실이 아니다 — CNBC 가 당일값을 준다. 이미 fetch_us.py(3.1.12 심리)가
       같은 소스로 KSVKOSPI 를 받고 있었는데 deriv 쪽만 몰라서 T+1(KRX) 로 굴러갔다.
       2026-07-13 실측: CNBC 83.33 (15:51 KST 갱신) · KRX 는 당일값 미공표.

    수동 override 는 그대로 남긴다(CNBC 장애 시 대비) — 아래 ingest_vkospi_override().
    """
    import datetime as _dt
    import urllib.request as _ur
    u = ("https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol"
         "?symbols=.KSVKOSPI&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json")
    try:
        raw = _ur.urlopen(_ur.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=12).read()
        q = json.loads(raw)["FormattedQuoteResult"]["FormattedQuote"][0]
        v = float(str(q.get("last", "")).replace(",", ""))
        d = str(q.get("last_time", ""))[:10]          # 예: 2026-07-13T15:51:10.000+0900
        if not (len(d) == 10 and v > 0):
            print("  VKOSPI(CNBC) 응답 이상 — skip")
            return 0
        con.execute("""INSERT INTO kr_derivatives_daily(id,date,vkospi) VALUES(?,?,?)
                       ON CONFLICT(id,date) DO UPDATE SET vkospi=excluded.vkospi""",
                    (KID, d, v))
        con.commit()
        print(f"  VKOSPI(CNBC T+0) ✓ {d} = {v}")
        return 1
    except Exception as e:
        print("  VKOSPI(CNBC) 실패 → override 폴백:", repr(e)[:60])
        return 0


def ingest_vkospi_override(con):
    """【폴백】 VKOSPI 당일값 수동/에이전트 주입 — CNBC(ingest_vkospi_cnbc) 실패 시 대비.

    급변동일에 Claude in Chrome 이 data.krx.co.kr(국내 IP·브라우저에서만 접근 가능)에서
    당일 VKOSPI 를 읽어 아래 JSON 을 만들어 두면 반영된다. 파일이 없으면 조용히 skip.
      위치: $DERIV_DB 폴더 또는 이 모듈 폴더의 vkospi_override.json
      형식: {"date": "YYYY-MM-DD", "vkospi": 45.2}
    """
    import os
    from pathlib import Path
    base = Path(__file__).resolve().parent
    cands = [base / "vkospi_override.json"]
    if os.environ.get("DERIV_DB"):
        cands.insert(0, Path(os.environ["DERIV_DB"]).resolve().parent / "vkospi_override.json")
    for f in cands:
        try:
            if not f.is_file():
                continue
            o = json.loads(f.read_text(encoding="utf-8"))
            d, v = str(o.get("date", ""))[:10], float(o.get("vkospi"))
            if len(d) == 10 and v > 0:
                con.execute("""INSERT INTO kr_derivatives_daily(id,date,vkospi) VALUES(?,?,?)
                               ON CONFLICT(id,date) DO UPDATE SET vkospi=excluded.vkospi""",
                            (KID, d, v))
                con.commit()
                print(f"  VKOSPI override ✓ {d} = {v}")
                return 1
        except Exception as e:
            print("  VKOSPI override skip:", repr(e)[:60])
    return 0


def ingest_krx(con, begin, end, opt_days=90):
    """1차(KRX OPEN API) → 2차(data.krx 보강) → T+0(네이버, 항상) → 실패 시 폴백."""
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

    # T+0 레이어는 1차 성공 여부와 무관하게 '항상' 실행 — KRX 는 T+1 공표라
    # 여기서 당일 급변을 채우지 않으면 3.1.13 이 하루 늦는다(2026-07-13 -8.9% 미반영 사고의 근본 원인:
    # 종전 코드는 1차 성공 시 즉시 return → 네이버 경로가 영영 실행되지 않았다).
    try:
        n += ingest_naver_t0(con)
    except Exception as e:
        print("  네이버 T+0 skip:", repr(e)[:70])
    # KIS(한국투자증권) — OI·PCR·IV스큐 T+0. 키 없으면 0 반환(비차단) → KRX T+1 경로 유지.
    try:
        n += ingest_kis_t0(con)
    except Exception as e:
        print("  KIS T+0 skip:", repr(e)[:70])
    # 서버 마감 캡처 병합 — 서버 cron(15:48 KST)이 떠 둔 전일 마감 PCR(Vol)/IV스큐/GEX 로 NULL 셀 보강(비차단)
    try:
        n += ingest_server_close(con)
    except Exception as e:
        print("  KIS 서버마감 병합 skip:", repr(e)[:70])
    try:
        # VKOSPI T+0: CNBC 자동 수집이 1차, 수동 override 는 폴백
        if not ingest_vkospi_cnbc(con):
            n += ingest_vkospi_override(con)
        else:
            n += 1
    except Exception as e:
        print("  VKOSPI override skip:", repr(e)[:60])

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


if __name__ == "__main__":  # 수동 실행: KOSPI200 전체 디스패치
    from db import init_db, connect, publish_db
    from datetime import datetime, timedelta
    init_db(); con = connect()
    end = datetime.utcnow().strftime("%Y%m%d")
    begin = (datetime.utcnow() - timedelta(days=420)).strftime("%Y%m%d")
    print("KOSPI200 rows:", ingest_krx(con, begin, end))
    con.close(); publish_db()
