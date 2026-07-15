#!/usr/bin/env python3
# fetch_brokers_tele.py (v3.8) — 한국 증권사 공식 텔레그램 리서치 채널을 curl 로 받아 콤팩트 추출.
# (fetch_kiwoom_tele.py 대체·일반화). Chrome 불필요·토큰 최소. 다른 fetch 스크립트와 bash 병렬 tool-call.
# 텔레그램 7사: 신한·키움·메리츠(research+Tech 통합)·하나·교보·유안타·현대차.
# (삼성·미래에셋·한투는 공개 공식 채널 미확인 → 메인세션 Chrome 으로 별도 수집.)
# 메인세션은 nmr_brokers_tele.json 을 읽어 nmr_securities.json 의 firm 엔트리(key_reports·key_message·view)를 작성.
# 산출: nmr_brokers_tele.json { firm: {label, channels:[...], asof, recent:[{datetime,title,text}]} }
# 사용: python3 fetch_brokers_tele.py [WORK_DIR] [N_per_firm]
import re, html, json, urllib.request, sys, os, time
from concurrent.futures import ThreadPoolExecutor
if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]): os.chdir(sys.argv[1])
N = int(sys.argv[2]) if len(sys.argv) > 2 else 6

FIRMS = {
    'shinhan': ('신한투자증권', ['shinhanresearch']),
    'kiwoom':  ('키움증권',     ['KiwoomResearch']),
    'meritz':  ('메리츠증권',   ['meritz_research', 'merITz_tech']),
    'hana':    ('하나증권',     ['HanaResearch']),
    'kyobo':   ('교보증권',     ['KyoboRSC']),
    'yuanta':  ('유안타증권',   ['yuantaresearch']),
    'hyundai': ('현대차증권',   ['hmsecresearch']),
}

def strip(t):
    t = re.sub(r'<br\s*/?>', '\n', t); t = re.sub(r'<[^>]+>', '', t)
    return html.unescape(t).strip()

def fetch_channel(handle, tries=3):
    last = ''
    for i in range(tries):
        try:
            h = urllib.request.urlopen(urllib.request.Request(f'https://t.me/s/{handle}', headers={'User-Agent': 'Mozilla/5.0'}), timeout=15).read().decode('utf-8', 'replace')
            out = []
            for b in re.split(r'<div class="tgme_widget_message ', h)[1:]:
                mt = re.search(r'js-message_text"[^>]*>(.*?)</div>', b, re.S)
                tm = re.search(r'<time[^>]*datetime="([^"]+)"', b)
                if not mt: continue
                txt = strip(mt.group(1))
                if not txt or len(txt) < 8: continue
                out.append({'datetime': (tm.group(1)[:16].replace('T', ' ') if tm else ''),
                            'title': txt.split('\n', 1)[0][:80], 'text': txt[:300]})
            if out: return out
        except Exception as e:
            last = str(e)
        time.sleep(1.5)
    return []

def fetch_firm(item):
    key, (label, handles) = item
    msgs = []
    for hd in handles: msgs += fetch_channel(hd)
    msgs.sort(key=lambda m: m['datetime'])
    msgs = msgs[-N:]
    return key, {'label': label, 'channels': handles, 'asof': (msgs[-1]['datetime'][:10] if msgs else ''), 'recent': msgs}

with ThreadPoolExecutor(max_workers=4) as ex:  # 동시성 완화로 텔레그램 throttle 회피
    res = dict(ex.map(fetch_firm, FIRMS.items()))
json.dump(res, open('nmr_brokers_tele.json', 'w'), ensure_ascii=False)
miss = [k for k, v in res.items() if not v['recent']]
for k, v in res.items():
    print(f"{k:8} {v['label']:8} asof {v['asof'] or '-':10} msgs {len(v['recent'])}  | {(v['recent'][-1]['title'] if v['recent'] else '(none)')[:40]}")
if miss: print('MISS(재시도 권장):', miss)
