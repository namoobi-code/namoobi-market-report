# -*- coding: utf-8 -*-
"""
ingest_krx_web.py — 【2차 소스, 선택적】 data.krx.co.kr 정밀도 보강 레이어.

  · 괴리율(Disparity)  = 시장베이시스 − 이론베이시스  → 캐리(잔존만기) 왜곡이 제거된 베이시스
  · 공식 내재변동성(IV)
  · 공식 P/C Ratio      → OPEN API 옵션체인 붕괴(행사가 사다리가 현물 미커버) 문제를 우회

전제: data.krx.co.kr 는 **로그인 세션(쿠키)** 이 필요하고 30분 후 자동 로그아웃된다.
      → 이 모듈은 '있으면 보강, 없으면 조용히 skip' 하는 완전 비차단 설계다.
      1차(ingest_krx_open.py)만으로도 리포트는 정상 생성된다.

※ 비밀번호는 다루지 않는다. 사용자가 브라우저에서 직접 로그인한 뒤,
   그 세션 쿠키만 아래 위치에 넣어두면 된다(선택 사항).
     · 환경변수 KRX_COOKIE
     · <연결폴더>/SECURITY/krx_cookie.txt   (예: "JSESSIONID=...; SCOUTER=...")
   쿠키가 없거나 만료되면 0을 반환하고 파이프라인은 1차 값으로 계속 진행한다.
"""
import os
import json
import urllib.request
import urllib.parse
from pathlib import Path

from db import log

KID = "KOSPI200"
URL = "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
BLD = "dbms/MDC/STAT/standard/"
PROD_K200_FUT = "KR___FUK2I"          # 코스피200 선물
PROD_K200_OPT = "KR___OPK2I"          # 코스피200 옵션(추정 — 응답 없으면 자동 skip)

# 메뉴별 bld (베이시스 추이는 실측 확인, 나머지는 동일 계열 후보 순차 시도)
BLD_BASIS = ["MDCSTAT13401"]
BLD_IV = ["MDCSTAT13501", "MDCSTAT13402"]
BLD_PCR = ["MDCSTAT13601", "MDCSTAT13403"]

_BASE_DIR = Path(__file__).resolve().parent


def _find_cookie():
    c = os.environ.get("KRX_COOKIE")
    if c and c.strip():
        return c.strip()
    for anc in [_BASE_DIR, *_BASE_DIR.parents]:
        for p in (anc / "SECURITY" / "krx_cookie.txt", anc / "krx_cookie.txt"):
            try:
                if p.is_file():
                    t = p.read_text(encoding="utf-8", errors="ignore").strip()
                    if t:
                        return t
            except Exception:
                pass
    return None


def _post(cookie, bld, extra):
    d = {"bld": BLD + bld, "locale": "ko_KR", "csvxls_isNo": "false"}
    d.update(extra)
    req = urllib.request.Request(
        URL, data=urllib.parse.urlencode(d).encode(),
        headers={"User-Agent": "Mozilla/5.0",
                 "Referer": "https://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201050401",
                 "X-Requested-With": "XMLHttpRequest",
                 "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                 "Cookie": cookie})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            j = json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        return []
    for k, v in j.items():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            return v
    return []


def _num(v):
    try:
        s = str(v).replace(",", "").replace("%", "").strip()
        return float(s) if s and s not in ("-", ".") else None
    except Exception:
        return None


def _pick(row, *cands):
    """컬럼명이 문서화돼 있지 않아 후보 키를 순차 탐색(부분일치 허용)."""
    for c in cands:
        if c in row:
            return _num(row[c])
    up = {k.upper(): k for k in row}
    for c in cands:
        for K, orig in up.items():
            if c.upper() in K:
                return _num(row[orig])
    return None


def _date(row):
    for k in ("TRD_DD", "BAS_DD", "TRDDD"):
        if k in row:
            return str(row[k]).replace("/", "-").replace(".", "-")[:10]
    for k, v in row.items():
        s = str(v)
        if len(s) == 10 and s[4] in "/-.":
            return s.replace("/", "-").replace(".", "-")
    return None


def _range(days):
    from datetime import date, timedelta
    t = date.today()
    return (t - timedelta(days=days)).strftime("%Y%m%d"), t.strftime("%Y%m%d")


def ingest_krx_web(con, back_days=420):
    cookie = _find_cookie()
    if not cookie:
        print("  data.krx 2차 보강: 세션 쿠키 없음 → skip(1차 값으로 진행)")
        return 0
    s, e = _range(back_days)
    base = {"secugrpId": "1", "aggBasTpCd": "0", "prodId": PROD_K200_FUT,
            "expmmNo": "1", "isuCd": "", "isuCd2": "", "strtDd": s, "endDd": e}

    vals = {}   # date -> dict(disparity/iv_krx/pcr_krx)

    # ① 괴리율(베이시스 추이)
    for bld in BLD_BASIS:
        rows = _post(cookie, bld, base)
        if not rows:
            continue
        for r in rows:
            d = _date(r)
            if not d:
                continue
            dis = _pick(r, "DISPARITY", "DIVERGENCE", "DSPRT")
            if dis is None:      # 괴리율 컬럼명이 다르면 시장−이론 베이시스로 직접 계산
                mb = _pick(r, "MKT_BASIS", "MKTBASIS")
                tb = _pick(r, "THEO_BASIS", "THEOBASIS")
                sp = _pick(r, "SPOT_PRC", "SPOTPRC")
                if mb is not None and tb is not None and sp:
                    dis = (mb - tb) / sp * 100.0
            if dis is not None:
                vals.setdefault(d, {})["disparity"] = dis
        break

    # ② 공식 IV / ③ 공식 P/C Ratio (옵션 상품)
    optbase = dict(base, prodId=PROD_K200_OPT)
    for blds, key, cands in ((BLD_IV, "iv_krx", ("IMP_VOLT", "IMPVOLT", "IV")),
                             (BLD_PCR, "pcr_krx", ("PC_RATIO", "PCRATIO", "PCR"))):
        for bld in blds:
            rows = _post(cookie, bld, optbase)
            if not rows:
                continue
            got = 0
            for r in rows:
                d = _date(r)
                v = _pick(r, *cands) if d else None
                if d and v is not None:
                    vals.setdefault(d, {})[key] = v
                    got += 1
            if got:
                break

    if not vals:
        print("  data.krx 2차 보강: 응답 없음(세션 만료 추정) → skip")
        return 0

    n = 0
    for d, v in vals.items():
        con.execute("""INSERT INTO kr_derivatives_daily(id,date,disparity,iv_krx,pcr_krx) VALUES(?,?,?,?,?)
                       ON CONFLICT(id,date) DO UPDATE SET
                         disparity=COALESCE(excluded.disparity, kr_derivatives_daily.disparity),
                         iv_krx   =COALESCE(excluded.iv_krx,    kr_derivatives_daily.iv_krx),
                         pcr_krx  =COALESCE(excluded.pcr_krx,   kr_derivatives_daily.pcr_krx)""",
                    (KID, d, v.get("disparity"), v.get("iv_krx"), v.get("pcr_krx")))
        n += 1
    con.commit()
    log(con, "ingest_krx_web", n)
    print(f"  data.krx 2차 보강 ✓ {n}일 (괴리율/공식IV/공식PCR)")
    return n


if __name__ == "__main__":
    from db import init_db, connect, publish_db
    init_db()
    con = connect()
    ingest_krx_web(con, 420)
    con.close()
    publish_db()
