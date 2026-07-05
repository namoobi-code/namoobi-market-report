#!/usr/bin/env python3
# nmr_runsrc.py - 마운트 잘림 근본해결. 로컬 repo의 git HEAD에서 완전한 스크립트를
#   런타임 디렉터리로 추출(git객체=절대 안 잘림) + 무결성검증 후 그 경로를 stdout 출력.
#   Phase 0 가 이 경로를 SRC 로 써서 '설치본 잘림'과 무관하게 항상 최신·완전 스크립트로 실행한다.
# 사용: python3 nmr_runsrc.py [out_dir]  -> 마지막 줄에 RUNSRC=<dir> (실패 시 RUNSRC=)
import sys, os, glob, subprocess, hashlib
OUT = sys.argv[1] if len(sys.argv) > 1 else (glob.glob('/sessions/*/mnt/outputs') or ['.'])[0] + '/nmr_runsrc'
REPO = next(iter(glob.glob('/sessions/*/mnt/claudeCowork/namoobi-market-report')), None)
BASE = 'plugins/namoobi-market-report/skills/namoobi-market-report'
def run(args, cwd=None): return subprocess.run(args, cwd=cwd, capture_output=True, text=True)
if not REPO or not os.path.isdir(os.path.join(REPO, '.git')):
    print('nmr_runsrc: 로컬 repo 없음 -> 설치본 사용'); print('RUNSRC='); sys.exit(0)
os.makedirs(OUT, exist_ok=True); os.makedirs(os.path.join(OUT,'references'), exist_ok=True); os.makedirs(os.path.join(OUT,'fonts'), exist_ok=True)
os.makedirs(os.path.join(OUT,'deriv_signals'), exist_ok=True)  # (fix) 파생 라이브 런처·모듈 추출
# git HEAD 의 모든 스크립트/references/fonts 추출
lst = run(['git','-c','core.quotepath=false','ls-tree','-r','--name-only','HEAD', BASE], cwd=REPO)
if lst.returncode != 0: print('nmr_runsrc: git ls-tree 실패 -> 설치본'); print('RUNSRC='); sys.exit(0)
n_ok=0; bad=[]; dbad=[]
for f in lst.stdout.splitlines():
    rel = f.split(BASE+'/',1)[-1]
    is_deriv = False
    if 'fonts/' in rel: dst = os.path.join(OUT,'fonts', os.path.basename(rel))
    elif rel.startswith('scripts/'): dst = os.path.join(OUT, os.path.basename(rel))
    elif rel.startswith('references/'): dst = os.path.join(OUT,'references', os.path.basename(rel))
    elif rel.endswith('SKILL.md'): dst = os.path.join(OUT,'SKILL.md')
    elif rel.startswith('deriv_signals/') and (rel.endswith('.py') or rel.endswith('requirements.txt')):
        # (fix) 파생 런처·모듈만 추출(.md/.csv 제외 — 한글명·불필요). 실패는 비차단(파생은 non-blocking).
        is_deriv = True; dst = os.path.join(OUT, 'deriv_signals', rel[len('deriv_signals/'):])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
    else: continue
    if rel.lower().endswith(('.ttf','.otf','.png','.woff','.woff2')):
        blob = subprocess.run(['git','show','HEAD:'+f], cwd=REPO, capture_output=True)
        if blob.returncode != 0: bad.append(rel); continue
        open(dst,'wb').write(blob.stdout); n_ok+=1; continue
    blob = run(['git','show','HEAD:'+f], cwd=REPO)
    if blob.returncode != 0:
        (dbad if is_deriv else bad).append(rel); continue
    open(dst,'w',encoding='utf-8',newline='\n').write(blob.stdout); n_ok+=1
# 무결성: build_report.js EOF + py 구문
import ast
intact=True
brj=os.path.join(OUT,'build_report.js')
if os.path.exists(brj) and 'EOF — namoobi-market-report' not in open(brj,encoding='utf-8').read()[-200:]: intact=False; bad.append('build_report.js EOF')
for pyf in glob.glob(OUT+'/*.py'):
    try: ast.parse(open(pyf,encoding='utf-8').read())
    except Exception as e: intact=False; bad.append(os.path.basename(pyf)+':'+str(e)[:30])
for pyf in glob.glob(OUT+'/deriv_signals/*.py'):
    try: ast.parse(open(pyf,encoding='utf-8').read())
    except Exception as e: dbad.append(os.path.basename(pyf)+':'+str(e)[:30])
print('nmr_runsrc: %d파일 추출 / 무결성 %s%s%s' % (n_ok, 'OK' if intact and not bad else 'FAIL', (' '+str(bad[:3]) if bad else ''), (' | deriv경고:'+str(dbad[:3]) if dbad else ' | deriv OK')))
print('RUNSRC='+(OUT if intact and not bad else ''))
