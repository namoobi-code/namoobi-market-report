# -*- coding: utf-8 -*-
"""1년치 백필 실행: 스키마 생성 → 수집 → 표준화/검증."""
from datetime import datetime, timedelta

from config import BACKFILL_DAYS
from db import init_db, connect, publish_db, active_db
from ingest import ingest_all
from analyze import run_analysis
from ingest_kr import ingest_kr_positioning


def main():
    init_db()
    con = connect()
    end = datetime.utcnow().date() + timedelta(days=1)
    start = end - timedelta(days=BACKFILL_DAYS)
    years = list(range(start.year, end.year + 1))
    print(f"[backfill] period {start} ~ {end}, COT years {years}")

    res = ingest_all(con, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), years, do_options=True)
    print(f"  ingest: prices {res['prices']} / COT {res['cot']} / options {res['options']}")
    kr = ingest_kr_positioning(con, back_days=BACKFILL_DAYS)
    print(f"  ingest KR: 투자자 순매수 {kr}행")
    from ingest_krx import ingest_krx
    from config import DATA_GO_KR_KEY
    if DATA_GO_KR_KEY:
        kd = ingest_krx(con, start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), opt_days=90)
        print(f"  ingest KRX(data.go.kr): 파생 {kd}행")

    ev, val = run_analysis(con)
    print(f"  analyze: signal_events {ev} / validation_rows {val}")
    con.close()
    pub = publish_db()
    print(f"[done] work_db={active_db()}")
    print(f"       publish_db={pub}")


if __name__ == "__main__":
    main()
