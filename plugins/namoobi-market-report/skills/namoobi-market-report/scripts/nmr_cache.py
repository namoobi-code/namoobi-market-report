#!/usr/bin/env python3
# nmr_cache.py (P2) -- slow-change cache for namoobi-market-report.
# Decides which slow items need refresh today vs reuse cached value, so the
# workflow can SKIP daily re-research of items that change only quarterly/at events.
# Triggers are computed DYNAMICALLY (calendar formulas; FOMC uses next_refresh
# recorded at the previous research). No hardcoded annual schedule table.
# Cache: <connected>/_market_report_data/nmr_cache.json
# Usage:
#   nmr_cache.py due <YYYY-MM-DD> [cache.json]      -> {item:{status:due|reuse,reason,as_of}}
#   nmr_cache.py get <item> [cache.json]            -> cached value JSON to stdout
#   nmr_cache.py set <item> <as_of> [next_refresh] [cache.json]  (value JSON on stdin)
import sys, json, os, glob, datetime as dt

def parse(s): return dt.date.fromisoformat(str(s)[:10])
def ym(d): return d.strftime('%Y-%m')

def third_friday(y, mo):
    d = dt.date(y, mo, 1)
    return d + dt.timedelta(days=(4 - d.weekday()) % 7 + 14)

def last_quarter_effective(today):
    c=[third_friday(y,mo) for y in (today.year-1,today.year) for mo in (3,6,9,12)]
    p=[x for x in c if x<=today]; return max(p) if p else None

def last_13f_deadline(today):
    qe=[dt.date(y,m,d) for y in (today.year-1,today.year) for (m,d) in ((3,31),(6,30),(9,30),(12,31))]
    dl=[q+dt.timedelta(days=45) for q in qe]; p=[x for x in dl if x<=today]; return max(p) if p else None

def find_cache():
    for b in glob.glob('/sessions/*/mnt/claudeCowork/_market_report_data'):
        return os.path.join(b,'nmr_cache.json')
    return 'nmr_cache.json'

def load(cf):
    try: return json.load(open(cf,encoding='utf-8'))
    except Exception: return {}

def due(today, cache):
    t=parse(today); out={}
    def v(it): return cache.get(it) or {}
    c=v('dot_plot')
    if not c.get('value'): out['dot_plot']={'status':'due','reason':'no cache'}
    elif not c.get('next_refresh'): out['dot_plot']={'status':'due','reason':'no next_refresh recorded'}
    elif t>=parse(c['next_refresh']): out['dot_plot']={'status':'due','reason':'today>=next FOMC '+c['next_refresh']}
    else: out['dot_plot']={'status':'reuse','reason':'next FOMC '+c['next_refresh'],'as_of':c.get('as_of')}
    c=v('berkshire'); dl=last_13f_deadline(t)
    if not c.get('value'): out['berkshire']={'status':'due','reason':'no cache'}
    elif c.get('as_of') and dl and parse(c['as_of'])<dl: out['berkshire']={'status':'due','reason':'13F deadline '+str(dl)+' passed since '+c['as_of']}
    else: out['berkshire']={'status':'reuse','reason':'latest 13F deadline '+str(dl),'as_of':c.get('as_of')}
    c=v('index_rebalance'); eff=last_quarter_effective(t)
    if not c.get('value'): out['index_rebalance']={'status':'due','reason':'no cache'}
    elif c.get('as_of') and eff and parse(c['as_of'])<eff: out['index_rebalance']={'status':'due','reason':'rebalance effective '+str(eff)+' passed since '+c['as_of']}
    else: out['index_rebalance']={'status':'reuse','reason':'latest effective '+str(eff),'as_of':c.get('as_of')}
    c=v('hy_spread')
    if not c.get('value'): out['hy_spread']={'status':'due','reason':'no cache'}
    elif c.get('as_of') and ym(parse(c['as_of']))<ym(t): out['hy_spread']={'status':'due','reason':'new month'}
    else: out['hy_spread']={'status':'reuse','reason':'same month','as_of':c.get('as_of')}
    c=v('cautions'); out['cautions']={'status':'reuse' if c.get('value') else 'due','reason':'static'}
    return out

def main():
    a=sys.argv[1:]
    if not a: print('usage: due|get|set'); sys.exit(2)
    cmd=a[0]
    if cmd=='due':
        cf=a[2] if len(a)>2 else find_cache(); print(json.dumps(due(a[1], load(cf)), ensure_ascii=False, indent=1))
    elif cmd=='get':
        cf=a[2] if len(a)>2 else find_cache(); print(json.dumps((load(cf).get(a[1]) or {}).get('value'), ensure_ascii=False))
    elif cmd=='set':
        it,as_of=a[1],a[2]; nr=a[3] if len(a)>3 and a[3] else None; cf=a[4] if len(a)>4 else find_cache()
        c=load(cf); c[it]={'value':json.load(sys.stdin),'as_of':as_of}
        if nr: c[it]['next_refresh']=nr
        os.makedirs(os.path.dirname(cf) or '.',exist_ok=True)
        json.dump(c,open(cf,'w',encoding='utf-8'),ensure_ascii=False,indent=1); print('cache updated: '+it)
    else: print('unknown cmd'); sys.exit(2)

if __name__=='__main__': main()
