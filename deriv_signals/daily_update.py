# -*- coding: utf-8 -*-
"""
매일 실행용 증분 업데이트 + 당일 리포트.
  최근 구간 가격/COT 갱신 → 옵션 스냅샷 1건 누적 → z/신호/검증 재계산 → 요약 출력.
스케줄러(평일 아침 등)가 이 스크립트를 호출하면 DB가 자동 갱신된다.
"""
from datetime import datetime, timedelta
import pandas as pd

from config import Z_THRESHOLD, INDICATOR_META, DB_PATH
from db import init_db, connect, publish_db
from ingest import ingest_prices, ingest_cot, ingest_options
from analyze import run_analysis
from ingest_kr import ingest_kr_positioning


def _pct(x):
    return f"{x*100:+.2f}%" if pd.notna(x) else "n/a"


def _v(x):
    return f"{x:+.1f}" if pd.notna(x) else "n/a"


def _report(con):
    print("=" * 60)
    print(f" 파생 포지셔닝 → 현물 선행신호 리포트  ({datetime.utcnow():%Y-%m-%d %H:%M UTC})")
    print("=" * 60)
    ind = pd.read_sql("SELECT * FROM indicators_daily", con)
    z = pd.read_sql("SELECT * FROM zscores_daily", con)
    for iid in ind["id"].unique():
        gi = ind[ind.id == iid].sort_values("date")
        gz = z[z.id == iid].sort_values("date")
        if gi.empty:
            continue
        last = gi.iloc[-1]
        zl = gz.iloc[-1] if not gz.empty else None
        print(f"\n[{iid}]  {last['date']}  종가={last['spot_close']:.2f}  "
              f"일간={_pct(last['spot_ret'])}  베이시스={_v(last['basis_bp'])}bp")
        if zl is not None:
            active = []
            for c, meta in INDICATOR_META.items():
                zc = "z_" + c
                if zc in zl and pd.notna(zl[zc]) and abs(zl[zc]) >= Z_THRESHOLD:
                    active.append(f"    * {meta['label']}: z={zl[zc]:+.2f}")
            print("  활성 신호(|z|>=%.1f):" % Z_THRESHOLD)
            print("\n".join(active) if active else "    (없음)")


def main():
    init_db()
    con = connect()
    end = datetime.utcnow().date() + timedelta(days=1)
    start = end - timedelta(days=20)
    years = sorted({start.year, end.year})
    ingest_prices(con, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    ingest_cot(con, years)
    ingest_options(con)
    ingest_kr_positioning(con, back_days=30)
    from ingest_krx import ingest_krx
    from config import DATA_GO_KR_KEY
    if DATA_GO_KR_KEY:
        ingest_krx(con, (end - timedelta(days=25)).strftime("%Y%m%d"), end.strftime("%Y%m%d"), opt_days=15)
    run_analysis(con)
    _report(con)
    con.close()
    publish_db()


if __name__ == "__main__":
    main()
