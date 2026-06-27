#!/usr/bin/env python3
# 3.1.5 일일 지수 — ^GSPC(S&P500)·^KS11(KOSPI) 2년 일봉 종가(실측, Yahoo). 차트의 일일 지수선 + EPS/PER 결측 보정 앵커.
import urllib.request,json,sys,os,datetime as dt
W=sys.argv[1] if len(sys.argv)>1 else '.'
def y(sym):
    u="https://query1.finance.yahoo.com/v8/finance/chart/"+sym+"?range=2y&interval=1d"
    req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'})
    j=json.load(urllib.request.urlopen(req,timeout=25))
    r=j['chart']['result'][0]; ts=r['timestamp']; cl=r['indicators']['quote'][0]['close']
    return [[dt.datetime.utcfromtimestamp(t).strftime('%Y-%m-%d'),round(c,2)] for t,c in zip(ts,cl) if c is not None]
try:
    out={'spx':y("%5EGSPC"),'kospi':y("%5EKS11"),'updated':os.environ.get('NMR_DATE_ISO','')}
    json.dump(out,open(os.path.join(W,'nmr_idx_daily.json'),'w'))
    print('idx_daily spx',len(out['spx']),'kospi',len(out['kospi']),'spx_last',out['spx'][-1],'kospi_last',out['kospi'][-1])
except Exception as e:
    print('idx_daily ERR',type(e).__name__,e)
