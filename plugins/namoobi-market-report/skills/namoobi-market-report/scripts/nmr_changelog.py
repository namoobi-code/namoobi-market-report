#!/usr/bin/env python3
# 변동이력(change_log) 계산: 비일간 지표(정책금리·물가·고용·CAPEX) 최종값을 캐시에 저장,
# 매 실행 직전값과 비교해 변경분만 빨간 change_log 로 report_data 에 부착. (표 위 빨간색 렌더는 build_report.js)
import json,os,sys,glob
W=sys.argv[1] if len(sys.argv)>1 else '.'
RD=sorted(glob.glob(W+'/_market_report_data/report_data_*.json'))[-1]
CWs=glob.glob('/sessions/*/mnt/claudeCowork/_market_report_data'); CW=CWs[0] if CWs else (W+'/_market_report_data')
today=os.environ.get('NMR_DATE_ISO','2026-06-26')
d=json.load(open(RD)); mac=d['markets']['macro']; rates=mac.get('rates',{})
cache_path=CW+'/nmr_valcache.json'
cache=json.load(open(cache_path)) if os.path.exists(cache_path) else {}
cur_pr={x.get('country'):x.get('rate') for x in rates.get('policy_rates',[])}
ff=rates.get('fed_funds',{}).get('current'); 
cur_pr['_fed_funds']=ff
old_pr=cache.get('policy_rates',{}); fomc=[]
for c,v in cur_pr.items():
    if c in old_pr and str(old_pr[c])!=str(v): fomc.append("%s %s 정책금리 %s%% → %s%%"%(today,c.replace('_fed_funds','美 FOMC'),old_pr[c],v))
rates['fomc_change_log']=fomc
cur_inf={x.get('name'):[x.get('yoy'),x.get('mom')] for x in mac.get('inflation',{}).get('rows',[])}
old_inf=cache.get('inflation',{}); infl=[]
for n,v in cur_inf.items():
    if n in old_inf and old_inf[n]!=v: infl.append("%s %s: YoY %s→%s · MoM %s→%s"%(today,n,old_inf[n][0],v[0],old_inf[n][1],v[1]))
mac.setdefault('inflation',{})['change_log']=infl
cur_emp={x.get('name'):x.get('value') for x in mac.get('employment',{}).get('rows',[])}
old_emp=cache.get('employment',{}); emp=[]
for n,v in cur_emp.items():
    if n in old_emp and str(old_emp[n])!=str(v): emp.append("%s %s: %s → %s"%(today,n,old_emp[n],v))
mac.setdefault('employment',{})['change_log']=emp
cap=d['markets'].get('bigtech_capex',{})
cur_cap={r.get('company'):{y:r.get(y) for y in ('y2024','y2025','y2026','y2027','y2028','y2029')} for r in cap.get('rows',[])}
old_cap=cache.get('capex',{}); cl=[]
for co,yr in cur_cap.items():
    if co in old_cap:
        for y,v in yr.items():
            if str(old_cap[co].get(y))!=str(v): cl.append("%s %s %s: %s→%s"%(today,co.split('(')[0].strip(),y[1:],old_cap[co].get(y),v))
cap['change_log']=cl
json.dump(d,open(RD,'w'),ensure_ascii=False,indent=1)
json.dump({'policy_rates':cur_pr,'inflation':cur_inf,'employment':cur_emp,'capex':cur_cap,'asof':today},open(cache_path,'w'),ensure_ascii=False)
print('changelog: fomc',len(fomc),'inf',len(infl),'emp',len(emp),'cap',len(cl))
