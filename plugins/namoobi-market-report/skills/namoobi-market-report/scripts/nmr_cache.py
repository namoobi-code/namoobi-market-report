#!/usr/bin/env python3
# nmr_cache.py (P2) -- slow-change cache for namoobi-market-report.
# Avoids daily re-research of items that change only at events (FOMC/13F/rebalance/month).
# PER-RUN REAL CHECK (schedules can change!): every run the workflow cheaply fetches the
# latest event MARKER for each item and calls `check`; reuse only if the marker is unchanged,
# otherwise (or if the check is inconclusive) refresh. `due` is a calendar HINT only.
# Cache: <connected>/_market_report_data/nmr_cache.json
# Usage:
#   nmr_cache.py check <item> <observed_marker> [cache.json]  -> {status:due|reuse,reason,as_of}
#   nmr_cache.py due   <YYYY-MM-DD> [cache.json]              -> calendar hint (when to expect next)
#   nmr_cache.py get   <item> [cache.json]                   -> cached value JSON to stdout
#   nmr_cache.py set   <item> <as_of> <event_marker> [cache.json]   (value JSON on stdin)
# Items: dot_plot, berkshire, index_rebalance, hy_spread, cautions
# Marker examples: 13F filing date, FOMC SEP meeting date, latest S&P/Nasdaq change date,
#   FRED HY latest data month (YYYY-MM); cautions -> "static".
import sys, json, os, glob, datetime as dt

def parse(s): return dt.date.fromisoformat(str(s)[:10])
def ym(d): return d.strftime('%Y-%m')
def third_friday(y, mo):
    d = dt.date(y, mo, 1); return d + dt.timedelta(days=(4 - d.weekday()) % 7 + 14)
def last_quarter_effective(t):
    c=[third_friday(y,mo) for y in (t.year-1,t.year) for mo in (3,6,9,12)]; p=[x for x in c if x<=t]; return max(p) if p else None
def last_13f_deadline(t):
    qe=[dt.date(y,m,d) for y in (t.year-1,t.year) for (m,d) in ((3,31),(6,30),(9,30),(12,31))]
    dl=[q+dt.timedelta(days=45) for q in qe]; p=[x for x in dl if x<=t]; return max(p) if p else None
def find_cache():
    for b in glob.glob('/sessions/*/mnt/claudeCowork/_market_report_data'): return os.path.join(b,'nmr_cache.json')
    return 'nmr_cache.json'
def load(cf):
    try: return json.load(open(cf,encoding='utf-8'))
    except Exception: return {}

def check(item, observed, cache):
    c=cache.get(item) or {}
    if not c.get('value'): return {'status':'due','reason':'no cache value'}
    obs=str(observed if observed is not None else '').strip()
    if obs.lower() in ('','none','unknown','null','error'):
        return {'status':'due','reason':'check inconclusive -> refresh (stale 방지)'}
    if item=='cautions': return {'status':'reuse','reason':'static','as_of':c.get('as_of')}
    stored=c.get('event_marker')
    if stored is None: return {'status':'due','reason':'no stored marker -> refresh'}
    if str(stored)!=obs: return {'status':'due','reason':'event changed: '+str(stored)+' -> '+obs}
    return {'status':'reuse','reason':'marker unchanged: '+str(stored),'as_of':c.get('as_of')}

def due(today, cache):
    t=parse(today); out={}
    h={'dot_plot':(cache.get('dot_plot') or {}).get('next_refresh') or 'check each run (FOMC SEP date)',
       'berkshire':'next 13F deadline ~ '+str(last_13f_deadline(t)),
       'index_rebalance':'last quarterly effective ~ '+str(last_quarter_effective(t)),
       'hy_spread':'monthly (current '+ym(t)+')','cautions':'static'}
    for k,vv in h.items(): out[k]={'hint':vv}
    return out

def main():
    a=sys.argv[1:]
    if not a: print('usage: check|due|get|set'); sys.exit(2)
    cmd=a[0]
    if cmd=='check':
        cf=a[3] if len(a)>3 else find_cache(); print(json.dumps(check(a[1], a[2], load(cf)), ensure_ascii=False, indent=1))
    elif cmd=='due':
        cf=a[2] if len(a)>2 else find_cache(); print(json.dumps(due(a[1], load(cf)), ensure_ascii=False, indent=1))
    elif cmd=='get':
        cf=a[2] if len(a)>2 else find_cache(); print(json.dumps((load(cf).get(a[1]) or {}).get('value'), ensure_ascii=False))
    elif cmd=='set':
        it,as_of,marker=a[1],a[2],a[3]; cf=a[4] if len(a)>4 else find_cache()
        c=load(cf); c[it]={'value':json.load(sys.stdin),'as_of':as_of,'event_marker':marker}
        os.makedirs(os.path.dirname(cf) or '.',exist_ok=True)
        json.dump(c,open(cf,'w',encoding='utf-8'),ensure_ascii=False,indent=1); print('cache set: '+it+' as_of='+as_of+' marker='+marker)
    else: print('unknown cmd'); sys.exit(2)

if __name__=='__main__': main()
