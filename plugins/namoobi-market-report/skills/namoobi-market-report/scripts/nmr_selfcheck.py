#!/usr/bin/env python3
# Phase 0 자가점검: 지금 실행하려는 '설치본 스크립트'가 GitHub repo HEAD(진실 원본)와 일치하는지 확인.
# 불일치(설치본 STALE)면 목록 출력 + exit 2 → 스킬은 사용자에게 '플러그인 업데이트' 요청 후 진행 여부 확인.
# 사용: python3 nmr_selfcheck.py <설치 scripts 디렉터리> [<githubtoken.txt 경로>]
import sys, os, subprocess, tempfile, glob
SRC = sys.argv[1]
TOKP = sys.argv[2] if len(sys.argv) > 2 else None
REPO = "github.com/namoobi-code/namoobi-market-report.git"
def h(p):
    return subprocess.run(["git","hash-object",p],capture_output=True,text=True).stdout.strip()
tok = None
if TOKP and os.path.exists(TOKP):
    tok = open(TOKP).read().strip()
url = ("https://%s@%s" % ("namoobi-code:"+tok, REPO)) if tok else ("https://"+REPO)
tmp = tempfile.mkdtemp(prefix="nmr_sc_")
r = subprocess.run(["git","clone","--depth","1","--quiet",url,tmp],capture_output=True,text=True)
if r.returncode != 0:
    print("selfcheck: GitHub clone 실패(네트워크/토큰) — 점검 생략, 계속 진행"); sys.exit(0)
RS = os.path.join(tmp,"plugins/namoobi-market-report/skills/namoobi-market-report/scripts")
if not os.path.isdir(RS):
    print("selfcheck: repo 구조 예상과 다름 — 점검 생략"); sys.exit(0)
stale=[]
for f in sorted(glob.glob(RS+"/*")):
    n=os.path.basename(f); local=os.path.join(SRC,n)
    if not os.path.exists(local): stale.append(n+" (설치본에 없음 = 신규파일 미반영)")
    elif h(local)!=h(f): stale.append(n+" (옛 버전)")
if stale:
    print("⚠️ 설치본 STALE — GitHub 최신과 다른 스크립트 %d개:"%len(stale))
    for s in stale: print("   -",s)
    print("→ 플러그인을 업데이트한 뒤 다시 실행하세요(설정→Capabilities/플러그인). 지금 실행하면 옛 결과가 나올 수 있음.")
    sys.exit(2)
print("selfcheck ✓ 설치본 == GitHub HEAD (최신)")
sys.exit(0)
