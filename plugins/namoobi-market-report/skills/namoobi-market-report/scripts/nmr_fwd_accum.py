#!/usr/bin/env python3
# 3.1.5 선행EPS/PER DB(schema2) 누적. 점:{eps,eps_date,per,per_date,idx,idx_date,src,link}. 풀날짜(eps_date) 키로 dedup.
# 매 실행 MacroAgent 스냅샷(nmr_macro sentiment.spx_fwd/kospi_fwd, asof=풀날짜, link=조사 출처 URL) upsert.
# per+eps 둘 다 있으면 idx=eps*per(출처와 일치). 한쪽만이면 해당일 일일지수로 보정. SPX 링크는 FactSet 주간 PDF(날짜) 자동 구성.
import json,os,sys,glob
W=sys.argv[1] if len(sys.argv)>1 else '.'
cw=glob.glob('/sessions/*/mnt/claudeCowork/_market_report_data')
HP=(cw[0] if cw else W+'/_market_report_data')+'/nmr_fwd_history.json'
hist=json.load(open(HP)) if os.path.exists(HP) else {'spx':[],'kospi':[],'schema':2}
try: daily=json.load(open(os.path.join(W,'nmr_idx_daily.json')))
except Exception: daily={'spx':[],'kospi':[]}
FB="https://advantage.factset.com/hubfs/Website/Resources%20Section/Research%20Desk/Earnings%20Insight/EarningsInsight_"
def factset(eps_date):
    try:
        y,m,d=eps_date[:10].split('-'); mmddyy=m+d+y[2:]
        return FB+mmddyy+("A" if mmddyy=="041026" else "")+".pdf"
    except Exception: return None
def idx_on(key,d):
    ser=daily.get(key) or []
    if not ser: return None,None
    t=d if len(d)>7 else d+'-28'; cand=[x for x in ser if x[0]<=t]
    x=cand[-1] if cand else ser[0]; return x[1],x[0]
def upsert(key,eps,per,date,link,src):
    if eps is None and per is None: return 0
    if per is not None and eps is not None:
        idx=round(eps*per,2); idate=date
    else:
        idx,idate=idx_on(key,date)
        if idx:
            if eps and not per: per=round(idx/eps,2)
            elif per and not eps: eps=round(idx/per,2)
    rec={'date':date[:10],'eps_date':date,'eps':eps,'per':per,'per_date':date,'idx':idx,'idx_date':idate,'src':src,'link':link}
    arr=hist.setdefault(key,[])
    for i,x in enumerate(arr):
        if (x.get('eps_date') or x.get('date'))==date: arr[i]=rec; break
    else: arr.append(rec)
    arr.sort(key=lambda z:z.get('eps_date') or z['date']); return 1
try: mm=json.load(open(os.path.join(W,'nmr_macro.json'))); sent=mm.get('macro',mm).get('sentiment',{})
except Exception: sent={}
SRC={'spx':'FactSet Earnings Insight','kospi':'FnGuide/증권사 컨센서스'}
n=0
for key,sk in (('spx','spx_fwd'),('kospi','kospi_fwd')):
    e=sent.get(sk) or {}; eps=e.get('fwd_eps'); per=e.get('fwd_per'); af=e.get('asof')
    if isinstance(eps,str):
        try: eps=float(eps.replace('$','').replace(',','').replace('p','').strip())
        except Exception: eps=None
    if (eps is None and per is None) or not af: continue
    af=str(af)[:10]
    if len(af)<=7: continue   # 월만 있으면 누적 안 함(풀날짜 필요)
    link=e.get('link') or (factset(af) if key=='spx' else None)
    n+=upsert(key,eps,per,af,link,e.get('src') or SRC[key])
hist['updated']=os.environ.get('NMR_DATE_ISO','');hist['schema']=2
json.dump(hist,open(HP,'w'),ensure_ascii=False); json.dump(hist,open(os.path.join(W,'nmr_fwd_history.json'),'w'),ensure_ascii=False)
print('accum: spx',len(hist['spx']),'kospi',len(hist['kospi']),'up',n)
