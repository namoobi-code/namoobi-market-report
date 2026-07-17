#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""send_mail_server.py — Phase 5 서버 SMTP 발송 래퍼 (v3.69 1순위 경로).

동작: ① 모드별 BCC 파일 읽기(// 주석 제외) ② docx 를 서버로 scp(대개 sync 로 이미 있음 — 크기 대조 후 재사용)
     ③ ssh 로 send_report_mail.py 에 stdin JSON 전달(주소 argv 미노출) ④ "SENT" 확인.
서버 인증파일(keys/gmail_app_password.txt) 없으면 exit 3 → 스킬은 Chrome 초안 경유(v3.68)로 폴백.

Usage: send_mail_server.py <docx절대경로(VM)> <subject> <body파일 경로> [scheduled|normal]
종료코드: 0=발송 성공 · 3=서버 인증파일 없음(폴백 요망) · 그 외=실패(폴백 요망)
출력 마지막 줄: SENT ... (성공) — BCC 는 인원수만.
"""
import glob, json, os, re, shlex, shutil, subprocess, sys

DOCX = sys.argv[1]
SUBJECT = sys.argv[2]
BODY = open(sys.argv[3], encoding="utf-8").read() if len(sys.argv) > 3 and os.path.isfile(sys.argv[3]) else "첨부 문서를 참고해 주세요."
MODE = (sys.argv[4] if len(sys.argv) > 4 else "normal").strip().lower()
SERVER = "ubuntu@141.147.160.13"
REMOTE_DIR = "namoobi/data/reports"

CW = (glob.glob("/sessions/*/mnt/claudeCowork") or ["D:/claudeCowork"])[0]
KEY = os.path.join(CW, "SECURITY", "nmr_deploy_key")
BCC_FILE = os.path.join(CW, "SECURITY", "예약메일수신자.txt" if MODE.startswith("sched") else "메일수신자.txt")

def run(cmd, timeout=35, inp=None):
    return subprocess.run(cmd, shell=True, timeout=timeout, capture_output=True, text=True, input=inp)

def main():
    if not os.path.isfile(DOCX):
        print("ERR docx 없음:", DOCX); sys.exit(2)
    bcc = []
    try:
        for ln in open(BCC_FILE, encoding="utf-8"):
            if re.match(r"^\s*//", ln):
                continue
            bcc += re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", ln)
    except Exception:
        pass
    bcc = list(dict.fromkeys(bcc))
    tmpk = "/dev/shm/nmr_mailk"
    shutil.copy(KEY, tmpk); os.chmod(tmpk, 0o600)
    SSH = f"ssh -i {tmpk} -o StrictHostKeyChecking=no -o ConnectTimeout=12 {SERVER}"
    SCP = f"scp -q -i {tmpk} -o StrictHostKeyChecking=no"
    try:
        # 인증파일 선검사 (없으면 즉시 폴백 신호)
        r = run(f'{SSH} "cd namoobi && python3 scripts/send_report_mail.py --check"')
        if r.returncode == 3 or "없음" in (r.stdout + r.stderr):
            print("AUTH_MISSING — 서버 keys/gmail_app_password.txt 미배포 → Chrome 폴백 요망"); sys.exit(3)
        base = os.path.basename(DOCX)
        remote = f"{REMOTE_DIR}/{base}"
        lsz = os.path.getsize(DOCX)
        r = run(f'{SSH} "stat -c %s {shlex.quote(remote)} 2>/dev/null"')
        if (r.stdout or "").strip() != str(lsz):   # sync 로 이미 올라갔으면 재전송 생략
            r = run(f"{SCP} {shlex.quote(DOCX)} {SERVER}:{shlex.quote(remote)}", timeout=120)
            if r.returncode != 0:
                print("ERR scp:", (r.stderr or "")[:120]); sys.exit(2)
        cfg = json.dumps({"to": "namoobi@gmail.com", "bcc": bcc, "subject": SUBJECT,
                          "body": BODY, "attach": f"/home/ubuntu/{remote}"}, ensure_ascii=False)
        r = run(f'{SSH} "cd namoobi && python3 scripts/send_report_mail.py"', timeout=90, inp=cfg)
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0 and "SENT" in out:
            print(out.strip().splitlines()[-1])
            print(f"발송 OK — To 1명 + BCC {len(bcc)}명 (주소 비공개)")
            sys.exit(0)
        print("ERR 서버 발송 실패:", out[:200]); sys.exit(r.returncode or 4)
    finally:
        try: os.remove(tmpk)
        except Exception: pass

if __name__ == "__main__":
    main()
