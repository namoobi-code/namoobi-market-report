#!/usr/bin/env python3
"""[Phase 5] 서버 동기화 — 리포트 발송 성공 후 1회 실행.

역할: 이 실행에서 갱신된 db/*.json + 방금 만든 docx 를 공개 대시보드 서버로 올린다.
비차단: 실패해도 리포트 워크플로우 전체를 막지 않는다(경고만 출력).

사용: python3 scripts/sync_server.py [새_docx_경로]
      (인자 없으면 _market_report_data 에서 가장 최근 global_market_report_*.docx 를 자동 선택)
"""
import glob, os, subprocess, sys, shlex
from pathlib import Path

SERVER   = "ubuntu@141.147.160.13"
REMOTE   = "~/namoobi/data"
KEEP_DAYS = 7          # 서버에 보관할 보고서 일수


def find(patterns):
    for p in patterns:
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
        print("[sync] ⚠️ _market_report_data 또는 배포키 없음 — 동기화 건너뜀")
        return 0

    base = Path(base)
    # 키 권한(600) 확보: 마운트 권한이 불안정하므로 /tmp 로 복사해 사용
    tmpkey = "/tmp/.nmr_deploy_key"
    subprocess.run(f"cp {shlex.quote(key)} {tmpkey} && chmod 600 {tmpkey}", shell=True, check=True)
    SSH = f"ssh -i {tmpkey} -o StrictHostKeyChecking=no -o ConnectTimeout=15"

    def run(cmd, label):
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        if r.returncode == 0:
            print(f"[sync] ✅ {label}")
            return True
        print(f"[sync] ⚠️ {label} 실패: {(r.stderr or '').strip()[:160]}")
        return False

    ok = True

    # 1) db/*.json (변경분만) + deriv_signals.db
    dbdir = base / "db"
    if dbdir.is_dir():
        ok &= run(f'tar czf - -C {shlex.quote(str(base))} db | '
                  f'{SSH} {SERVER} "cd {REMOTE} && tar xzf -"',
                  f"db/ 동기화 ({len(list(dbdir.glob('*.json')))}개)")

    deriv = base / "deriv_signals.db"
    if deriv.exists():
        ok &= run(f'scp -q -i {tmpkey} -o StrictHostKeyChecking=no '
                  f'{shlex.quote(str(deriv))} {SERVER}:{REMOTE}/', "deriv_signals.db")

    # 2) 신규 docx
    docx = sys.argv[1] if len(sys.argv) > 1 else None
    if not docx:
        cands = sorted(glob.glob(str(base / "global_market_report_*.docx")) +
                       glob.glob(str(base.parent / "global_market_report_*.docx")),
                       key=os.path.getmtime)
        docx = cands[-1] if cands else None
    if docx and os.path.exists(docx):
        ok &= run(f'scp -q -i {tmpkey} -o StrictHostKeyChecking=no '
                  f'{shlex.quote(docx)} {SERVER}:{REMOTE}/reports/',
                  f"보고서 업로드 ({os.path.basename(docx)})")
    else:
        print("[sync] ⚠️ 업로드할 docx 없음")

    # 3) 서버 보고서 회전 — 날짜별 최종본만, 최근 KEEP_DAYS 일
    ok &= run(
        f'{SSH} {SERVER} "cd {REMOTE}/reports && '
        f'ls -1 *.docx 2>/dev/null | sed -E \'s/.*_([0-9]{{8}})_[0-9]{{4}}\\.docx/\\1/\' | sort -u | head -n -{KEEP_DAYS} | '
        f'while read d; do rm -f global_market_report_\\${{d}}_*.docx; done; '
        f'ls -1 *.docx | sed -E \'s/.*_([0-9]{{8}})_([0-9]{{4}})\\.docx/\\1/\' | sort | uniq -d | '
        f'while read d; do ls -1 global_market_report_\\${{d}}_*.docx | head -n -1 | xargs -r rm -f; done"',
        f"서버 보고서 회전 (최근 {KEEP_DAYS}일·날짜별 최종본)")

    print(f"[sync] {'완료' if ok else '일부 실패(비차단)'} → http://namoobi.duckdns.org")
    return 0   # 항상 0 — 리포트 워크플로우를 막지 않음


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[sync] ⚠️ 예외(비차단): {e}")
        sys.exit(0)
