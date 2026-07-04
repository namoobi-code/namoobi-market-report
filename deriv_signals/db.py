# -*- coding: utf-8 -*-
"""SQLite 스키마 및 접속 헬퍼.

마운트/네트워크 파일시스템은 SQLite 락을 지원하지 않아 'disk I/O error'가 난다.
connect()는 게시 경로(PUBLISH_DB)에서 먼저 시도하고, 실패하면 로컬 임시 디스크로
자동 폴백한 뒤 publish_db()에서 완성된 DB 파일을 사용자 폴더로 복사한다.
"""
import sqlite3
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from config import PUBLISH_DB, INSTRUMENTS

_WORK = {"path": PUBLISH_DB, "needs_publish": False}


def active_db():
    return _WORK["path"]


SCHEMA = """
CREATE TABLE IF NOT EXISTS instruments (
    id TEXT PRIMARY KEY, name TEXT, region TEXT,
    spot TEXT, future TEXT, option TEXT, cot TEXT, proxy_spot INTEGER
);
CREATE TABLE IF NOT EXISTS prices_daily (
    id TEXT, date TEXT, spot_close REAL, future_close REAL, vix_close REAL,
    PRIMARY KEY (id, date)
);
CREATE TABLE IF NOT EXISTS positioning_weekly (
    id TEXT, report_date TEXT, open_interest REAL, oi_change REAL,
    lev_net REAL, asset_mgr_net REAL, dealer_net REAL,
    PRIMARY KEY (id, report_date)
);
CREATE TABLE IF NOT EXISTS options_daily (
    id TEXT, date TEXT, expiry_used TEXT, dte INTEGER,
    pcr_oi REAL, pcr_vol REAL, iv_atm REAL, iv_skew_25d REAL, delta_imbalance REAL, gex REAL,
    PRIMARY KEY (id, date)
);
CREATE TABLE IF NOT EXISTS indicators_daily (
    id TEXT, date TEXT, spot_close REAL, spot_ret REAL, fut_ret REAL,
    basis_bp REAL, oi_chg_w REAL, lev_net REAL, asset_mgr_net REAL,
    pcr_oi REAL, pcr_vol REAL, iv_skew_25d REAL, delta_imbalance REAL, gex REAL,
    fwd_ret_1d REAL, fwd_ret_3d REAL, fwd_ret_5d REAL,
    PRIMARY KEY (id, date)
);
CREATE TABLE IF NOT EXISTS zscores_daily (
    id TEXT, date TEXT,
    z_basis_bp REAL, z_oi_chg_w REAL, z_lev_net REAL, z_asset_mgr_net REAL,
    z_pcr_oi REAL, z_pcr_vol REAL, z_iv_skew_25d REAL, z_delta_imbalance REAL, z_gex REAL,
    PRIMARY KEY (id, date)
);
CREATE TABLE IF NOT EXISTS signal_events (
    id TEXT, date TEXT, indicator TEXT, z_value REAL, direction INTEGER,
    fwd_ret_1d REAL, fwd_ret_3d REAL, fwd_ret_5d REAL,
    PRIMARY KEY (id, date, indicator)
);
CREATE TABLE IF NOT EXISTS validation_summary (
    id TEXT, indicator TEXT, direction INTEGER, n_events INTEGER,
    mean_fwd_1d REAL, hit_1d REAL, mean_fwd_3d REAL, hit_3d REAL,
    mean_fwd_5d REAL, hit_5d REAL, ic_1d REAL, ic_3d REAL, ic_5d REAL,
    PRIMARY KEY (id, indicator, direction)
);
CREATE TABLE IF NOT EXISTS kr_derivatives_daily (
    id TEXT, date TEXT,
    basis_bp REAL, oi REAL,
    pcr_oi REAL, pcr_vol REAL, iv_skew_25d REAL, gex REAL,
    PRIMARY KEY (id, date)
);
CREATE TABLE IF NOT EXISTS update_log (
    run_ts TEXT, step TEXT, rows INTEGER, note TEXT
);
"""


def _open(path):
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=DELETE;")   # 단일 파일 → 복사 시 항상 정합
    con.execute("CREATE TABLE IF NOT EXISTS _probe(a)")
    con.execute("DROP TABLE _probe")
    con.commit()
    return con


def connect():
    try:
        return _open(_WORK["path"])
    except sqlite3.OperationalError:
        d = Path(tempfile.gettempdir()) / "deriv_signals"
        d.mkdir(parents=True, exist_ok=True)
        local = d / "deriv_signals.db"
        if Path(PUBLISH_DB).exists() and not local.exists():
            try:
                shutil.copy(PUBLISH_DB, local)
            except Exception:
                pass
        _WORK["path"] = local
        _WORK["needs_publish"] = True
        return _open(local)


def publish_db():
    if _WORK["needs_publish"] and Path(_WORK["path"]) != Path(PUBLISH_DB):
        try:
            shutil.copy(_WORK["path"], PUBLISH_DB)
        except Exception as e:
            return f"게시 실패: {e}"
    return str(PUBLISH_DB)


def init_db():
    con = connect()
    con.executescript(SCHEMA)
    for r in INSTRUMENTS:
        con.execute(
            """INSERT INTO instruments(id,name,region,spot,future,option,cot,proxy_spot)
               VALUES(?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 name=excluded.name, region=excluded.region, spot=excluded.spot,
                 future=excluded.future, option=excluded.option, cot=excluded.cot,
                 proxy_spot=excluded.proxy_spot""",
            (r["id"], r["name"], r["region"], r["spot"], r["future"],
             r["option"], r["cot"], int(r["proxy_spot"])),
        )
    con.commit()
    con.close()


def log(con, step, rows, note=""):
    con.execute(
        "INSERT INTO update_log(run_ts,step,rows,note) VALUES(?,?,?,?)",
        (datetime.now(timezone.utc).isoformat(timespec="seconds"), step, int(rows), note),
    )
    con.commit()


if __name__ == "__main__":
    init_db()
    print("initialized:", active_db())
