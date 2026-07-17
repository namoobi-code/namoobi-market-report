#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_krliq.py — 3.1.14 국내 유동성·레버리지 (Phase 1).

데이터 원본 = 서버 kr_liquidity.db (서버가 cron 1일 3회 수집: 06:35/14:10/16:10 KST,
namoobi-market-report-server/scripts/fetch_kr_liquidity.py).
  1순위: 서버에서 scp 로 DB 회수 (시점고정 T+0 스냅샷 포함)
  2순위: 연결폴더의 PC 사본 (sync_server 가 백업해 둔 것)
  3순위: 서버레포 수집기를 로컬에서 직접 실행 (금융위·다음·ECOS 직접 호출 — 키는 SECURITY)
산출: W/nmr_krliq.json  {as_of, daily[≤420], monthly, verdict}
  daily 행: [date, 예탁금, 미수금, 반대매매금액, 반대매매비중%, 신용전체, 신용코스피, 신용코스닥,
             코스피, 코스피거래대금, 코스닥, 코스닥거래대금]  (금액 원)
  verdict: ① 예탁금 5일 증감 × 회전배수(거래대금÷예탁금) 5일 방향 2×2 자동 판정
Usage: fetch_krliq.py <WORK_DIR>
"""
import json, os, sys, glob, sqlite3, shutil, subprocess, tempfile

W = sys.argv[1] if len(sys.argv) > 1 else "."
CW = (glob.glob("/sessions/*/mnt/claudeCowork") or ["D:/claudeCowork"])[0]
SRV_REPO = os.path.join(CW, "namoobi-market-report-server")
PC_DB = os.path.join(SRV_REPO, "data", "kr_liquidity.db")

def try_scp(dst):
    key = os.path.join(CW, "SECURITY", "nmr_deploy_key")
    if not os.path.exists(key): return False
    tmpk = "/dev/shm/nmr_k_krliq"
    try:
        shutil.copy(key, tmpk); os.chmod(tmpk, 0o600)
        r = subprocess.run(["scp", "-q", "-i", tmpk, "-o", "StrictHostKeyChecking=no",
                            "-o", "ConnectTimeout=12",
                            "ubuntu@141.147.160.13:namoobi/data/kr_liquidity.db", dst],
                           timeout=35, capture_output=True)
        return r.returncode == 0 and os.path.getsize(dst) > 10000
    except Exception:
        return False
    finally:
        try: os.remove(tmpk)
        except Exception: pass

def local_build(dst):
    fk = os.path.join(SRV_REPO, "scripts", "fetch_kr_liquidity.py")
    if not os.path.exists(fk): return False
    env = dict(os.environ)
    tmpd = tempfile.mkdtemp(prefix="krliq_")
    # 수집기는 스크립트 위치 기준 ../data/kr_liquidity.db 에 쓴다 → 복사본으로 실행
    os.makedirs(os.path.join(tmpd, "scripts"), exist_ok=True)
    shutil.copy(fk, os.path.join(tmpd, "scripts", "fetch_kr_liquidity.py"))
    r = subprocess.run([sys.executable, os.path.join(tmpd, "scripts", "fetch_kr_liquidity.py"),
                        "--backfill", "400"], timeout=280, capture_output=True, text=True, env=env)
    print(r.stdout.strip()[-200:] if r.stdout else r.stderr.strip()[-200:])
    built = os.path.join(tmpd, "data", "kr_liquidity.db")
    if os.path.exists(built):
        shutil.copy(built, dst); return True
    return False

def main():
    db = os.path.join(W, "kr_liquidity.db")
    src = None
    if try_scp(db): src = "server-scp"
    elif os.path.exists(PC_DB):
        shutil.copy(PC_DB, db); src = "pc-copy"
    if not src and local_build(db): src = "local-api"
    if not src:
        print("krliq: 소스 확보 실패 (서버·PC사본·로컬수집 모두 불가)"); sys.exit(1)

    c = sqlite3.connect(db)
    daily = c.execute(
        "SELECT date,deposit,ucol,opp_amt,opp_ratio,crd_whl,crd_kospi,crd_kosdaq,"
        "kospi,kospi_trdval,kosdaq,kosdaq_trdval FROM kr_liq_daily "
        "ORDER BY date DESC LIMIT 420").fetchall()[::-1]
    monthly = c.execute("SELECT month,m2,kospi,kosdaq FROM kr_liq_monthly ORDER BY month").fetchall()
    vr = c.execute("SELECT date,deposit,kospi_trdval FROM kr_liq_daily "
                   "WHERE deposit IS NOT NULL AND kospi_trdval IS NOT NULL "
                   "ORDER BY date DESC LIMIT 40").fetchall()[::-1]
    c.close()
    verdict = None
    if len(vr) >= 6:
        d5 = (vr[-1][1] / vr[-6][1] - 1) * 100
        t5 = vr[-1][2] / vr[-1][1] - vr[-6][2] / vr[-6][1]
        lab = (("유입·가동", "강세") if d5 > 0 and t5 > 0 else
               ("유입·관망", "중립") if d5 > 0 else
               ("이탈·소진성 회전", "경계") if t5 > 0 else ("이탈·위축", "약세"))
        verdict = {"label": lab[0], "tone": lab[1], "dep_5d_pct": round(d5, 2),
                   "turn_5d_chg": round(t5, 4), "as_of": vr[-1][0]}
    as_of = max((r[0] for r in daily if r[1] is not None), default="")
    out = {"src": src, "as_of": as_of, "daily": daily, "monthly": monthly, "verdict": verdict}
    json.dump(out, open(os.path.join(W, "nmr_krliq.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"krliq OK src={src} daily={len(daily)} monthly={len(monthly)} as_of={as_of} verdict={verdict and verdict['label']}")

if __name__ == "__main__":
    main()
