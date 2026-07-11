#!/usr/bin/env python3
"""[Phase 5.5] 서버 동기화 — 리포트 발송 성공 후 1회 실행.

올림: db/*.json(통합DB) · deriv_signals.db · report_data_<날짜>.json · 정책금리 시계열 · 신규 docx
받음: poll.db (서버가 1일 2회 수집한 김치프리미엄·공포탐욕 — 서버에만 있는 데이터 → PC로 백업)

비차단: 실패해도 종료코드 0. 리포트 워크플로우를 되돌리지 않는다.
사용:  python3 scripts/sync_server.py [새_docx_경로]
"""
import glob, json, os, subprocess, sys, shlex
from pathlib import Path

SERVER    = "ubuntu@141.147.160.13"
REMOTE    = "~/namoobi/data"
KEEP_DAYS = 7


def find(pats):
    for p in pats:
        hit = glob.glob(p)
        if hit:
            return hit[0]
    return None


def main():
    base = find(['/sessions/*/mnt/claudeCowork/_market_report_data',
                 '/sessions/*/mnt/outputs/_market_report_data'])
    key = find(['/sessions/*/mnt/claudeCowork/SECURITY/nmr_deploy_key',
                '/sessions/*/mnt/*/SECURITY/nmr_deploy_key'])
    if not base or not key:
        print("[sync] ⚠️ _market_report_data 또는 배포키 없음 — 건너뜀")
        return 0

    base = Path(base)
    tmpkey = "/tmp/.nmr_deploy_key"
    subprocess.run(f"cp {shlex.quote(key)} {tmpkey} && chmod 600 {tmpkey}", shell=True, check=True)
    SSH = f"ssh -i {tmpkey} -o StrictHostKeyChecking=no -o ConnectTimeout=15"
    SCP = f"scp -q -i {tmpkey} -o StrictHostKeyChecking=no"

    def run(cmd, label):
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        ok = r.returncode == 0
        print(f"[sync] {'✅' if ok else '⚠️'} {label}" + ("" if ok else f" — {(r.stderr or '').strip()[:140]}"))
        return ok

    ok = True
    run(f'{SSH} {SERVER} "mkdir -p {REMOTE}/db {REMOTE}/reports {REMOTE}/report"', "원격 디렉토리 확인")

    # ── 0) ⭐ PULL 먼저 — 서버가 매일 cron 으로 누적한 메모리·HBM 시계열을 PC 로 당겨 병합.
    #    서버는 24시간 켜져 있어 리포트를 안 돌린 날도 데이터를 쌓는다. 먼저 당겨서 union 해야
    #    아래 PUSH 에서 PC 의 옛 파일이 서버의 최신 누적분을 덮어쓰는 사고를 막는다.
    import tempfile
    tmpd = tempfile.mkdtemp()
    if run(f'{SCP} {SERVER}:{REMOTE}/db/series_mem_*.json {tmpd}/ 2>/dev/null', "서버 누적 시계열 pull"):
        merged_n = 0
        for sp in glob.glob(os.path.join(tmpd, "series_mem_*.json")):
            name = os.path.basename(sp)
            lp = base / "db" / name
            try:
                srv = json.load(open(sp, encoding="utf-8"))
                loc = json.load(open(lp, encoding="utf-8")) if lp.exists() else {"data": []}
                by = {r[0]: r[1] for r in (loc.get("data") or [])}
                by.update({r[0]: r[1] for r in (srv.get("data") or [])})   # 서버값 우선
                out = sorted(([d, v] for d, v in by.items()), key=lambda x: x[0])
                srv["data"] = out
                json.dump(srv, open(lp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                merged_n += 1
            except Exception as e:
                print(f"[sync]    ⚠️ {name} 병합 실패: {e}")
        print(f"[sync]    → {merged_n}종 시계열 병합 (서버 누적분 반영)")

    # ── 1) 통합 DB (변경분만)
    if (base / "db").is_dir():
        n = len(list((base / "db").glob("*.json")))
        ok &= run(f'tar czf - -C {shlex.quote(str(base))} db | {SSH} {SERVER} "cd {REMOTE} && tar xzf -"',
                  f"db/ 동기화 ({n}종)")

    # ── 2) 파생 포지셔닝 SQLite
    if (base / "deriv_signals.db").exists():
        ok &= run(f'{SCP} {shlex.quote(str(base/"deriv_signals.db"))} {SERVER}:{REMOTE}/', "deriv_signals.db")

    # ── 3) 최신 report_data (CAPEX·HBM·파생포지셔닝·경기선행 등 보고서 전 섹션)
    rds = sorted(glob.glob(str(base / "report_data_*.json")), key=os.path.getmtime)
    if rds:
        ok &= run(f'{SCP} {shlex.quote(rds[-1])} {SERVER}:{REMOTE}/report/report_data.json',
                  f"report_data ({os.path.basename(rds[-1])})")

    # ── 4) 정책금리 월별 시계열 (6개국 차트용)
    pm = base / "nmr_policyrates_monthly.json"
    if pm.exists():
        ok &= run(f'{SCP} {shlex.quote(str(pm))} {SERVER}:{REMOTE}/report/policyrates_monthly.json',
                  "정책금리 시계열")

    # ── 5) 이번 회차 docx
    docx = sys.argv[1] if len(sys.argv) > 1 else None
    if not docx:
        c = sorted(glob.glob(str(base / "global_market_report_*.docx")) +
                   glob.glob(str(base.parent / "global_market_report_*.docx")), key=os.path.getmtime)
        docx = c[-1] if c else None
    if docx and os.path.exists(docx):
        ok &= run(f'{SCP} {shlex.quote(docx)} {SERVER}:{REMOTE}/reports/', f"보고서 ({os.path.basename(docx)})")
    else:
        print("[sync] ⚠️ 업로드할 docx 없음")

    # ── 6) 서버 보고서 회전 (날짜별 최종본 × 최근 KEEP_DAYS 일)
    ok &= run(
        f'{SSH} {SERVER} "cd {REMOTE}/reports && '
        f'ls -1 *.docx 2>/dev/null | sed -E \'s/.*_([0-9]{{8}})_[0-9]{{4}}\\.docx/\\1/\' | sort -u | head -n -{KEEP_DAYS} | '
        f'while read d; do rm -f global_market_report_\\${{d}}_*.docx; done; '
        f'ls -1 *.docx 2>/dev/null | sed -E \'s/.*_([0-9]{{8}})_[0-9]{{4}}\\.docx/\\1/\' | sort | uniq -d | '
        f'while read d; do ls -1 global_market_report_\\${{d}}_*.docx | head -n -1 | xargs -r rm -f; done"',
        f"보고서 회전 (최근 {KEEP_DAYS}일)")

    # ── 7) ⭐ 서버 전용 데이터를 PC로 되가져오기 (서버 소실 대비 백업)
    #    poll.db 는 서버가 1일 2회 수집해 쌓는, 서버에만 존재하는 시계열이다.
    ok &= run(f'{SCP} {SERVER}:{REMOTE}/poll.db {shlex.quote(str(base / "poll.db"))}',
              "poll.db 백업 회수 (김프·공포탐욕)")

    print(f"[sync] {'완료' if ok else '일부 실패(비차단)'} → http://namoobi.duckdns.org")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[sync] ⚠️ 예외(비차단): {e}")
        sys.exit(0)
