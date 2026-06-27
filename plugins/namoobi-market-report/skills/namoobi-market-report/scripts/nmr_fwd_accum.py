#!/usr/bin/env python3
# 3.1.5 선행EPS/PER DB(schema2) 누적. 점: {eps,eps_date,per,per_date,idx,idx_date,src,link}.
# 매 실행 MacroAgent 스냅샷(nmr_macro sentiment.spx_fwd/kospi_fwd)을 월키로 upsert. EPS or PER 한쪽만 있으면 해당일 일일지수로 보정(eps*per=지수).
import json,os,sys,glob
W=sys.argv[1] if len(sys.argv)>1 else '.'
cw=glob.glob('/sessions/*/mnt/claudeCowork/_market_report_data')
HP=(cw[0] if cw else W+'/_market_report_data')+'/nmr_fwd_history.json'
hist=json.load(open(HP)) if os.path.exists(HP) else {'spx':[],'kospi':[],'schema':2}
try: daily=json.load(open(os.path.join(W,'nmr_idx_daily.json')))
except Exception: daily={'spx':[],'kospi':[]}
LINK={'spx':('FactSet Earnings Insight','https://insight.factset.com/topic/earnings'),'kospi':('FnGuide 컨센서스','https://comp.fnguide.com')}
def idx_on(key,d):
    ser=daily.get(key) or []
    if not ser: return None,None
    t=d if len(d)>7 else d+'-28'
    cand=[x for x in ser if x[0]<=t]
    x=cand[-1] if cand else ser[0]; return x[1],x[0]
def upsert(key,eps,per,date,link,src):
    if eps is None and per is None: return 0
    idx,idate=idx_on(key,date)
    if idx:
        if eps and not per: per=round(idx/eps,2)
        elif per and not eps: eps=round(idx/per,2)
    mo=date[:7]; arr=hist.setdefault(key,[])
    rec={'date':mo,'eps':eps,'eps_date':date,'per':per,'per_date':date,'idx':idx,'idx_date':idate,'src':src,'link':link}
    for i,x in enumerate(arr):
        if x.get('date')==mo: arr[i]=rec; break
    else: arr.append(rec)
    arr.sort(key=lambda z:z['date']); return 1
try: mm=json.load(open(os.path.join(W,'nmr_macro.json'))); sent=mm.get('macro',mm).get('sentiment',{})
except Exception: sent={}
n=0
for key,sk in (('spx','spx_fwd'),('kospi','kospi_fwd')):
    e=sent.get(sk) or {}; eps=e.get('fwd_eps'); per=e.get('fwd_per'); af=e.get('asof')
    if isinstance(eps,str):
        try: eps=float(eps.replace('$','').replace(',','').replace('p','').strip())
        except Exception: eps=None
    if (eps is None and per is None) or not af: continue
    af=str(af); date=af[:10] if len(af)>7 else af
    n+=upsert(key,eps,per,date,e.get('link') or LINK[key][1],e.get('src') or LINK[key][0])
hist['updated']=os.environ.get('NMR_DATE_ISO','');hist['schema']=2
os.makedirs(os.path.dirname(HP),exist_ok=True)
json.dump(hist,open(HP,'w'),ensure_ascii=False); json.dump(hist,open(os.path.join(W,'nmr_fwd_history.json'),'w'),ensure_ascii=False)
print('accum v2: spx',len(hist.get('spx',[])),'kospi',len(hist.get('kospi',[])),'upserts',n)
