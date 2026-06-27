#!/usr/bin/env python3
# 3.1.5 선행EPS/PER 시계열 누적: 매 실행 새로 수집한 nmr_spx/kospi_fwd_series 를
# 연결폴더 nmr_fwd_history.json 에 date 키로 병합(신규 추가·기존 갱신) → 시계열이 매일 향상.
import json,os,sys,glob
W=sys.argv[1] if len(sys.argv)>1 else '.'
cw=glob.glob('/sessions/*/mnt/claudeCowork/_market_report_data')
HP=(cw[0] if cw else W+'/_market_report_data')+'/nmr_fwd_history.json'
hist=json.load(open(HP)) if os.path.exists(HP) else {}

def harvest():
    # MacroAgent 가 매 실행 수집하는 최신 선행EPS/PER 스냅샷을 월(YYYY-MM) 포인트로 누적
    try: mm=json.load(open(os.path.join(W,'nmr_macro.json')))
    except Exception: return
    sent=mm.get('macro',mm).get('sentiment',{})
    for key,sk in (('spx','spx_fwd'),('kospi','kospi_fwd')):
        e=sent.get(sk) or {}
        ev=e.get('fwd_eps'); af=e.get('asof')
        if ev is None or not af: continue
        if isinstance(ev,str):
            try: ev=float(ev.replace('$','').replace(',','').replace('p','').strip())
            except Exception: continue
        mo=str(af)[:7]
        cur={x['date']:x for x in hist.get(key,[]) if x.get('date')}
        cur[mo]={'date':mo,'fwd_eps':ev,'fwd_per':e.get('fwd_per'),'source':(e.get('note') or '')[:30]}
        hist[key]=sorted(cur.values(), key=lambda z:z['date'])

def merge(key,f):
    cur={x['date']:x for x in hist.get(key,[]) if x.get('date')}
    try: new=json.load(open(os.path.join(W,f))).get('series',[])
    except Exception: new=[]
    add=0
    for x in new:
        d=x.get('date')
        if d and x.get('fwd_eps') is not None:
            if d not in cur: add+=1
            cur[d]=x  # 신규 추가 또는 최신값으로 갱신
    hist[key]=sorted(cur.values(), key=lambda z:z['date'])
    return add,len(hist[key])
sa,sn=merge('spx','nmr_spx_fwd_series.json'); ka,kn=merge('kospi','nmr_kospi_fwd_series.json')
harvest()  # 일일 스냅샷 누적
sn=len(hist.get('spx',[])); kn=len(hist.get('kospi',[]))
hist['updated']=os.environ.get('NMR_DATE_ISO','')
os.makedirs(os.path.dirname(HP),exist_ok=True)
json.dump(hist,open(HP,'w'),ensure_ascii=False)
json.dump(hist,open(os.path.join(W,'nmr_fwd_history.json'),'w'),ensure_ascii=False)  # gen_fwd3 용 사본
print('accum: spx +%d (총%d) / kospi +%d (총%d)'%(sa,sn,ka,kn))
