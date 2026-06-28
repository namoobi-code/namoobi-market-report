#!/usr/bin/env python3
# nmr_db.py - 범용 비매일 지표 DB (Big-Arch v1.0). 섹션 무관 저장/변동체크/재사용.
# 정책: 발표주기가 매일이 아닌 모든 지표는 DB(파일)에 저장하고, 매 실행 '변동 여부만' 관측해
#       변동(marker 변경)이 있을 때만 재조사·갱신, 없으면 DB값을 그대로 재사용한다.
# DB: <connected>/_market_report_data/db/<item>.json = {"marker":..,"as_of":"YYYY-MM-DD","data":..}
# Usage:
#   nmr_db.py check  <item> <observed_marker> [dbdir]   -> {status:reuse|due, reason, as_of}
#   nmr_db.py get    <item> [dbdir]                       -> data JSON (stdout)
#   nmr_db.py set    <item> <as_of> <marker> [dbdir]      (data JSON on stdin)
#   nmr_db.py upsert <item> <as_of> <marker> <keyfield> [dbdir]  (list[dict] on stdin; merge by keyfield - 누적형)
#   nmr_db.py list   [dbdir]                              -> 각 item marker/as_of 요약
import sys, json, os, glob

def _dbdir(arg=None):
    if arg:
        os.makedirs(arg, exist_ok=True); return arg
    base = (glob.glob('/sessions/*/mnt/claudeCowork/_market_report_data') or
            glob.glob('/sessions/*/mnt/outputs/_market_report_data') or ['.'])[0]
    d = os.path.join(base, 'db'); 
    try: os.makedirs(d, exist_ok=True)
    except Exception: pass
    return d

def _path(item, dbdir): return os.path.join(dbdir, str(item) + '.json')

def _load(item, dbdir):
    try: return json.load(open(_path(item, dbdir), encoding='utf-8'))
    except Exception: return {}

def _empty(v): return v is None or v == {} or v == [] or v == ''

def check(item, observed, dbdir):
    e = _load(item, dbdir)
    if not e or _empty(e.get('data')): return {'status': 'due', 'reason': 'no DB data'}
    obs = str(observed if observed is not None else '').strip()
    if obs.lower() in ('', 'none', 'unknown', 'null', 'error', '-'):
        return {'status': 'due', 'reason': '관측 불가 -> 재조사(stale 방지)'}
    if str(e.get('marker')) != obs:
        return {'status': 'due', 'reason': 'marker 변경: %s -> %s' % (e.get('marker'), obs)}
    return {'status': 'reuse', 'reason': 'marker 불변: ' + obs, 'as_of': e.get('as_of')}

def get(item, dbdir): return _load(item, dbdir).get('data')

def set_(item, as_of, marker, dbdir, data):
    try:
        json.dump({'marker': marker, 'as_of': as_of, 'data': data},
                  open(_path(item, dbdir), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        return True
    except Exception as ex:
        sys.stderr.write('nmr_db set fail %s: %s\n' % (item, ex)); return False

def upsert(item, as_of, marker, keyfield, dbdir, rows):
    cur = _load(item, dbdir).get('data') or []
    if not isinstance(cur, list): cur = []
    idx = {str(r.get(keyfield)): i for i, r in enumerate(cur) if isinstance(r, dict)}
    for r in (rows or []):
        if not isinstance(r, dict): continue
        k = str(r.get(keyfield))
        if k in idx: cur[idx[k]] = r
        else: cur.append(r); idx[k] = len(cur) - 1
    cur.sort(key=lambda r: str(r.get(keyfield)))
    return set_(item, as_of, marker, dbdir, cur)

# (편의) 신규조사분이 있으면 DB 저장, 없으면 DB값 재사용 — merge 등 파이프라인용
def sync(item, value, as_of, marker, dbdir, nonempty=None):
    ne = nonempty or (lambda v: not _empty(v))
    if ne(value):
        set_(item, as_of, marker, dbdir, value); return value
    cached = get(item, dbdir)
    return cached if (cached is not None and ne(cached)) else value

def main():
    a = sys.argv; cmd = a[1] if len(a) > 1 else ''
    if cmd == 'check':
        print(json.dumps(check(a[2], a[3], _dbdir(a[4] if len(a) > 4 else None)), ensure_ascii=False))
    elif cmd == 'get':
        print(json.dumps(get(a[2], _dbdir(a[3] if len(a) > 3 else None)), ensure_ascii=False))
    elif cmd == 'set':
        print(set_(a[2], a[3], a[4], _dbdir(a[5] if len(a) > 5 else None), json.load(sys.stdin)))
    elif cmd == 'upsert':
        print(upsert(a[2], a[3], a[4], a[5], _dbdir(a[6] if len(a) > 6 else None), json.load(sys.stdin)))
    elif cmd == 'list':
        d = _dbdir(a[2] if len(a) > 2 else None)
        for f in sorted(glob.glob(os.path.join(d, '*.json'))):
            e = json.load(open(f, encoding='utf-8'))
            print(os.path.basename(f)[:-5], '| marker=', e.get('marker'), '| as_of=', e.get('as_of'))
    else:
        print('usage: nmr_db.py check|get|set|upsert|list ...'); sys.exit(1)

if __name__ == '__main__': main()
# EOF -- namoobi-market-report nmr_db.py
