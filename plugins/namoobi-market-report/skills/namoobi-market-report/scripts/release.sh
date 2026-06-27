#!/usr/bin/env bash
# release.sh - bump EVERY version location together, commit, sync working tree, push.
# Why: the marketplace/plugin version was frozen (marketplace 1.7.19 / plugin 1.9.0) while
# only the internal SKILL version moved, so the plugin manager saw "no new version" and
# 'update plugin' was a no-op -> the installed copy stayed stale and fixes never took effect.
# This script makes the three versions move together so an update is always offered & taken.
#
# Usage: scripts/release.sh <plugin_ver e.g. 1.11.0> <skill_ver e.g. v3.41.0> "<changelog one-liner>"
set -euo pipefail
PV="${1:?plugin version e.g. 1.11.0}"; SV="${2:?skill version e.g. v3.41.0}"; MSG="${3:?changelog one-liner}"
SCRIPTDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPTDIR"
while [ "$ROOT" != "/" ] && [ ! -f "$ROOT/.claude-plugin/marketplace.json" ]; do ROOT="$(dirname "$ROOT")"; done
[ -f "$ROOT/.claude-plugin/marketplace.json" ] || { echo "repo root not found"; exit 2; }
SD="$ROOT/plugins/namoobi-market-report/skills/namoobi-market-report"
PJ="$ROOT/plugins/namoobi-market-report/.claude-plugin/plugin.json"
MK="$ROOT/.claude-plugin/marketplace.json"; SK="$SD/SKILL.md"; CL="$SD/CHANGELOG.md"
TODAY="$(TZ=Asia/Seoul date +%F)"

python3 - "$PJ" "$MK" "$SK" "$CL" "$PV" "$SV" "$MSG" "$TODAY" <<'PY'
import json,sys
PJ,MK,SK,CL,PV,SV,MSG,TODAY=sys.argv[1:9]
d=json.load(open(PJ,encoding="utf-8")); d["version"]=PV
json.dump(d,open(PJ,"w",encoding="utf-8"),ensure_ascii=False,indent=2); open(PJ,"a",encoding="utf-8").write("\n")
m=json.load(open(MK,encoding="utf-8")); m["plugins"][0]["version"]=PV
json.dump(m,open(MK,"w",encoding="utf-8"),ensure_ascii=False,indent=2); open(MK,"a",encoding="utf-8").write("\n")
t=open(SK,encoding="utf-8").read().split("\n")
for i,l in enumerate(t):
    if l.startswith("# Namoobi Market Report"):
        t[i]="# Namoobi Market Report (plugin v%s · SKILL %s)"%(PV,SV); break
open(SK,"w",encoding="utf-8").write("\n".join(t))
cl=open(CL,encoding="utf-8").read().split("\n")
entry="## %s (plugin %s, %s) — %s"%(SV,PV,TODAY,MSG)
cl=([cl[0],"",entry,""]+cl[1:]) if (cl and cl[0].startswith("#")) else ([entry,""]+cl)
open(CL,"w",encoding="utf-8").write("\n".join(cl))
print("bumped: plugin/marketplace -> %s ; SKILL title -> %s"%(PV,SV))
PY

cd "$ROOT"
git add "$PJ" "$MK" "$SK" "$CL"
# truncation guard: staged blob must match on-disk byte size (mount can read short)
for f in "$PJ" "$MK" "$SK" "$CL"; do
  rel="${f#$ROOT/}"; st=$(git cat-file -s ":$rel" 2>/dev/null || echo 0); dk=$(wc -c < "$f")
  [ "$st" = "$dk" ] || { echo "ABORT: $rel staged=$st disk=$dk (mount truncation) - re-run"; exit 3; }
done
git commit -q -m "$SV: $MSG"
git reset --hard HEAD -q   # keep on-disk tree == commit so the installed copy is not stale
TOK="$ROOT/../SECURITY/githubtoken.txt"
if [ -r "$TOK" ]; then
  export GH_TOKEN="$(tr -d ' \r\n' < "$TOK")"
  git -c credential.helper='!f(){ echo username=namoobi-code; echo "password=$GH_TOKEN"; };f' push -u origin HEAD:main 2>&1 | sed "s/$GH_TOKEN/***/g"
  unset GH_TOKEN
else
  echo "NOTE: SECURITY/githubtoken.txt not readable - push manually:  git push -u origin main"
fi
echo "RELEASED $SV (plugin $PV). Next: Cowork 에서 '플러그인 업데이트' 클릭 -> /namoobi-market-report 재실행."
