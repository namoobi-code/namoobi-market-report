# -*- coding: utf-8 -*-
"""표준화(z-score) + 신호 이벤트 + 선행성 검증(신호일 → 1/3/5일 후 현물수익률)."""
import numpy as np
import pandas as pd

from config import (INSTRUMENTS, INDICATOR_META, Z_WINDOW, Z_MINP,
                    Z_THRESHOLD, FWD_HORIZONS, OUT_DIR)
from db import log

IND_COLS = ["basis_bp", "oi_chg_w", "lev_net", "asset_mgr_net",
            "pcr_oi", "pcr_vol", "iv_skew_25d", "delta_imbalance", "gex"]


def _n(x):
    try:
        return None if pd.isna(x) else float(x)
    except Exception:
        return None


def _spearman(a, b):
    if len(a) < 3:
        return None
    r = pd.DataFrame({"a": a.values, "b": b.values}).rank()
    c = r["a"].corr(r["b"])
    return None if pd.isna(c) else float(c)


# ── 통합 지표 패널 ─────────────────────────────
def build_indicators(con):
    prices = pd.read_sql("SELECT * FROM prices_daily", con)
    pos = pd.read_sql("SELECT * FROM positioning_weekly", con)
    opt = pd.read_sql("SELECT * FROM options_daily", con)
    try:
        krd = pd.read_sql("SELECT * FROM kr_derivatives_daily", con)
    except Exception:
        krd = pd.DataFrame()
    con.execute("DELETE FROM indicators_daily")
    n = 0
    for inst in INSTRUMENTS:
        iid = inst["id"]
        p = prices[prices.id == iid].sort_values("date").set_index("date")
        if p.empty:
            continue
        d = pd.DataFrame(index=p.index)
        d["spot_close"] = p["spot_close"]
        d["spot_ret"] = p["spot_close"].pct_change(fill_method=None)
        d["fut_ret"] = p["future_close"].pct_change(fill_method=None)
        d["basis_bp"] = (p["future_close"] / p["spot_close"] - 1.0) * 1e4

        pp = pos[pos.id == iid].sort_values("report_date").set_index("report_date")
        for col, out in [("lev_net", "lev_net"), ("asset_mgr_net", "asset_mgr_net"), ("oi_change", "oi_chg_w")]:
            if not pp.empty:
                s = pp[col].reindex(d.index.union(pp.index)).sort_index().ffill().reindex(d.index)
            else:
                s = pd.Series(np.nan, index=d.index)
            d[out] = s.values

        oo = opt[opt.id == iid].set_index("date")
        for col in ["pcr_oi", "pcr_vol", "iv_skew_25d", "delta_imbalance", "gex"]:
            d[col] = oo[col].reindex(d.index) if not oo.empty else np.nan

        # KOSPI200: data.go.kr 파생(선물 베이시스/OI, 옵션 PCR/IV스큐) 병합
        kk = krd[krd.id == iid].set_index("date") if not krd.empty else pd.DataFrame()
        if not kk.empty:
            # (fix 2026-07-05) 컬럼별 실데이터가 있을 때만 병합 — 네이버 basis 만 있고 oi/pcr/iv 가 전부 None 일 때
            #   kk["oi"].diff(5) 가 NoneType 연산으로 크래시해 basis 반영까지 막던 문제 방지.
            if "basis_bp" in kk and pd.to_numeric(kk["basis_bp"], errors="coerce").notna().any():
                d["basis_bp"] = pd.to_numeric(kk["basis_bp"], errors="coerce").reindex(d.index)
            if "oi" in kk and pd.to_numeric(kk["oi"], errors="coerce").notna().any():
                d["oi_chg_w"] = pd.to_numeric(kk["oi"], errors="coerce").reindex(d.index).diff(5)
            for col in ["pcr_oi", "pcr_vol", "iv_skew_25d", "gex"]:
                if col in kk and pd.to_numeric(kk[col], errors="coerce").notna().any():
                    d[col] = pd.to_numeric(kk[col], errors="coerce").reindex(d.index)

        for k in FWD_HORIZONS:
            d[f"fwd_ret_{k}d"] = p["spot_close"].shift(-k) / p["spot_close"] - 1.0

        d = d.reset_index().rename(columns={"index": "date"})
        for _, r in d.iterrows():
            con.execute(
                """INSERT OR REPLACE INTO indicators_daily
                   (id,date,spot_close,spot_ret,fut_ret,basis_bp,oi_chg_w,lev_net,asset_mgr_net,
                    pcr_oi,pcr_vol,iv_skew_25d,delta_imbalance,gex,fwd_ret_1d,fwd_ret_3d,fwd_ret_5d)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (iid, r["date"], _n(r["spot_close"]), _n(r["spot_ret"]), _n(r["fut_ret"]),
                 _n(r["basis_bp"]), _n(r["oi_chg_w"]), _n(r["lev_net"]), _n(r["asset_mgr_net"]),
                 _n(r["pcr_oi"]), _n(r["pcr_vol"]), _n(r["iv_skew_25d"]), _n(r["delta_imbalance"]), _n(r.get("gex")),
                 _n(r.get("fwd_ret_1d")), _n(r.get("fwd_ret_3d")), _n(r.get("fwd_ret_5d"))),
            )
            n += 1
    con.commit()
    log(con, "build_indicators", n)
    return n


# ── z-score ─────────────────────────────
def compute_zscores(con):
    df = pd.read_sql("SELECT * FROM indicators_daily", con)
    con.execute("DELETE FROM zscores_daily")
    n = 0
    for iid, g in df.groupby("id"):
        g = g.sort_values("date")
        out = pd.DataFrame({"id": iid, "date": g["date"]})
        for c in IND_COLS:
            x = g[c].astype(float)
            m = x.rolling(Z_WINDOW, min_periods=Z_MINP).mean()
            s = x.rolling(Z_WINDOW, min_periods=Z_MINP).std()
            out["z_" + c] = (x - m) / s
        for _, r in out.iterrows():
            con.execute(
                """INSERT OR REPLACE INTO zscores_daily
                   (id,date,z_basis_bp,z_oi_chg_w,z_lev_net,z_asset_mgr_net,
                    z_pcr_oi,z_pcr_vol,z_iv_skew_25d,z_delta_imbalance,z_gex)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (iid, r["date"], _n(r.get("z_basis_bp")), _n(r.get("z_oi_chg_w")),
                 _n(r.get("z_lev_net")), _n(r.get("z_asset_mgr_net")), _n(r.get("z_pcr_oi")),
                 _n(r.get("z_pcr_vol")), _n(r.get("z_iv_skew_25d")), _n(r.get("z_delta_imbalance")), _n(r.get("z_gex"))),
            )
            n += 1
    con.commit()
    log(con, "compute_zscores", n)
    return n


# ── 신호 이벤트 + 검증 ─────────────────────────────
def build_signals_and_validate(con):
    ind = pd.read_sql("SELECT * FROM indicators_daily", con)
    z = pd.read_sql("SELECT * FROM zscores_daily", con)
    m = ind.merge(z, on=["id", "date"], how="left")

    con.execute("DELETE FROM signal_events")
    con.execute("DELETE FROM validation_summary")
    ev_rows, val_rows = [], 0

    for iid, g in m.groupby("id"):
        g = g.sort_values("date")
        # (1) 신호 이벤트: |z| >= 임계값
        gev_list = []
        for c in IND_COLS:
            zc = "z_" + c
            sub = g.dropna(subset=[zc])
            hit = sub[sub[zc].abs() >= Z_THRESHOLD]
            for _, r in hit.iterrows():
                direction = int(np.sign(r[zc]))
                rec = (iid, r["date"], c, float(r[zc]), direction,
                       _n(r["fwd_ret_1d"]), _n(r["fwd_ret_3d"]), _n(r["fwd_ret_5d"]))
                ev_rows.append(rec)
                gev_list.append(rec)

        # (2) 전체표본 순위상관(IC): z_indicator vs fwd_ret
        ic = {}
        for c in IND_COLS:
            zc = "z_" + c
            for k in FWD_HORIZONS:
                d2 = g[[zc, f"fwd_ret_{k}d"]].dropna()
                ic[(c, k)] = _spearman(d2[zc], d2[f"fwd_ret_{k}d"]) if len(d2) >= 10 else None

        # (3) 검증표: (지표×방향)별 이벤트 통계
        gev = pd.DataFrame(gev_list, columns=["id", "date", "indicator", "z_value", "direction",
                                              "fwd_ret_1d", "fwd_ret_3d", "fwd_ret_5d"])
        for c in IND_COLS:
            exp = INDICATOR_META[c]["expected"]
            for direction in (+1, -1):
                e = gev[(gev.indicator == c) & (gev.direction == direction)] if not gev.empty else gev
                if e.empty:
                    continue
                row = [iid, c, direction, int(len(e))]
                for k in FWD_HORIZONS:
                    fwd = e[f"fwd_ret_{k}d"].dropna()
                    row += [float(fwd.mean()) if len(fwd) else None,
                            float((np.sign(fwd) == direction * exp).mean()) if len(fwd) else None]
                row += [ic.get((c, 1)), ic.get((c, 3)), ic.get((c, 5))]
                con.execute(
                    """INSERT OR REPLACE INTO validation_summary
                       (id,indicator,direction,n_events,mean_fwd_1d,hit_1d,mean_fwd_3d,hit_3d,
                        mean_fwd_5d,hit_5d,ic_1d,ic_3d,ic_5d)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    tuple(row),
                )
                val_rows += 1

    con.executemany(
        "INSERT OR REPLACE INTO signal_events(id,date,indicator,z_value,direction,fwd_ret_1d,fwd_ret_3d,fwd_ret_5d) VALUES(?,?,?,?,?,?,?,?)",
        ev_rows,
    )
    con.commit()
    log(con, "build_signals", len(ev_rows), f"validation rows={val_rows}")

    pd.read_sql("SELECT * FROM validation_summary ORDER BY id,indicator,direction", con)\
      .to_csv(OUT_DIR / "signal_validation_summary.csv", index=False, encoding="utf-8-sig")
    pd.read_sql("SELECT * FROM signal_events ORDER BY date DESC,id,indicator", con)\
      .to_csv(OUT_DIR / "signal_events.csv", index=False, encoding="utf-8-sig")
    return len(ev_rows), val_rows


def run_analysis(con):
    build_indicators(con)
    compute_zscores(con)
    return build_signals_and_validate(con)
