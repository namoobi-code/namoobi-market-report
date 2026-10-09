# -*- coding: utf-8 -*-
"""
KOSPI200 파생/수급 데이터 수집 (무료·자격증명 불필요).

핵심 신호 = 투자자별 순매수(외국인/기관), 일별. 네이버 금융 '투자자별 매매동향'에서 수집.
  - 외국인 순매수(억원) → 미국 COT의 '레버리지펀드' 슬롯에 매핑(포지셔닝 지표)
  - 기관계 순매수(억원) → '자산운용사' 슬롯에 매핑
한국에서 외국인 순매수는 대표적 '일별' 선행지표(미국 COT는 주간 → 韓이 더 촘촘).

한계: KOSPI200 지수 원시feed(야후/네이버)는 결측·이상치 → 현물은 KODEX200 ETF(069500)로 대용(ingest.py).
선물 베이시스·옵션 PCR/IV의 1년 소급은 무료로 제한적 → data.go.kr(공공데이터) 또는 KRX 계정 필요(README).
"""
import warnings, urllib.request, io
from datetime import datetime, timedelta
import pandas as pd
from db import log

warnings.filterwarnings("ignore")
KOSPI200_ID = "KOSPI200"
_UA = {"User-Agent": "Mozilla/5.0"}


def _f(x):
    try:
        return None if pd.isna(x) else float(x)
    except Exception:
        return None


def _fetch(url):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("euc-kr", "ignore")


def _investor_page(bizdate):
    """네이버 투자자별 매매동향(거래소) 1페이지 파싱 → date/foreign/inst(억원)."""
    url = f"https://finance.naver.com/sise/investorDealTrendDay.naver?bizdate={bizdate}&sosok="
    t = pd.read_html(io.StringIO(_fetch(url)))[0]
    names = ['date', 'indiv', 'foreign', 'inst', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'etc']
    t.columns = names[:len(t.columns)]
    t = t[t['date'].astype(str).str.match(r'\d{2}\.\d{2}\.\d{2}')].copy()
    for c in ['foreign', 'inst']:
        t[c] = pd.to_numeric(t[c].astype(str).str.replace(',', '', regex=False), errors='coerce')
    t['date'] = '20' + t['date'].str.replace('.', '-', regex=False)
    return t[['date', 'foreign', 'inst']]


def ingest_kr_positioning(con, back_days=400, max_pages=34):
    """네이버 투자자별 순매수를 bizdate로 역페이징하여 ~back_days 만큼 수집."""
    start = (datetime.utcnow().date() - timedelta(days=back_days)).strftime("%Y-%m-%d")
    biz = datetime.utcnow().strftime("%Y%m%d")
    seen = {}
    for _ in range(max_pages):
        try:
            t = _investor_page(biz)
        except Exception as e:
            print("  KR investor skip:", repr(e)[:70])
            break
        if t.empty:
            break
        for _, r in t.iterrows():
            seen[r['date']] = (r['foreign'], r['inst'])
        oldest = min(t['date'])
        if oldest <= start:
            break
        biz = (datetime.strptime(oldest, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y%m%d")
    n = 0
    for d, (fn, inn) in sorted(seen.items()):
        # 외국인→lev_net 슬롯, 기관→asset_mgr_net 슬롯 (build_indicators가 그대로 사용)
        con.execute(
            "INSERT OR REPLACE INTO positioning_weekly(id,report_date,open_interest,oi_change,lev_net,asset_mgr_net,dealer_net) VALUES(?,?,?,?,?,?,?)",
            (KOSPI200_ID, d, None, None, _f(fn), _f(inn), None),
        )
        n += 1
    con.commit()
    log(con, "ingest_kr_positioning", n)
    return n


def kospi200_futures_snapshot():
    """현재 KOSPI200 최근월 선물 가격(포인트) — 참고/확장용(당일 스냅샷)."""
    try:
        tabs = pd.read_html(io.StringIO(_fetch("https://finance.naver.com/sise/sise_index.naver?code=FUT")))
        vals = tabs[0].astype(str).values.flatten()
        for v in vals:
            try:
                f = float(v.replace(",", ""))
                if 100 < f < 100000:
                    return f
            except Exception:
                continue
    except Exception:
        return None
    return None


if __name__ == "__main__":
    from db import init_db, connect, publish_db
    init_db(); con = connect()
    print("KR positioning rows:", ingest_kr_positioning(con, back_days=400))
    con.close(); publish_db()
