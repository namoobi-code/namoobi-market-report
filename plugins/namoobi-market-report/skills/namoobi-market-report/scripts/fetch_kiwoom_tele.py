#!/usr/bin/env python3
# fetch_kiwoom_tele.py (v3.7 P2) — 키움증권 리서치센터 공식 텔레그램(@KiwoomResearch)에서
# 최근 리포트 메시지를 curl 로 받아 콤팩트 추출 (Chrome 불필요·토큰 최소).
# 메인세션은 이 콤팩트 출력만 읽고 nmr_securities.json 의 kiwoom 엔트리(key_reports·key_message)를 작성.
# 산출: nmr_kiwoom_tele.json {asof, source, recent:[{datetime, title, text}]}  (최근 N개)
# 사용: python3 fetch_kiwoom_tele.py [WORK_DIR] [N]
import re, html, json, urllib.request, sys, os
if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]): os.chdir(sys.argv[1])
N = int(sys.argv[2]) if len(sys.argv) > 2 else 12
URL = 'https://t.me/s/KiwoomResearch'

def strip(t):
    t = re.sub(r'<br\s*/?>', '\n', t)
    t = re.sub(r'<[^>]+>', '', t)
    return html.unescape(t).strip()

try:
    h = urllib.request.urlopen(urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'}), timeout=15).read().decode('utf-8', 'replace')
except Exception as e:
    json.dump({'asof': '', 'source': URL, 'recent': [], 'error': str(e)}, open('nmr_kiwoom_tele.json', 'w'), ensure_ascii=False)
    print('키움 텔레그램 실패(폴백 필요):', e); sys.exit(0)

bubbles = re.split(r'<div class="tgme_widget_message ', h)[1:]
recent = []
for b in bubbles:
    mt = re.search(r'js-message_text"[^>]*>(.*?)</div>', b, re.S)
    tm = re.search(r'<time[^>]*datetime="([^"]+)"', b)
    if not mt: continue
    txt = strip(mt.group(1))
    if not txt: continue
    dtm = (tm.group(1)[:16].replace('T', ' ') if tm else '')
    title = txt.split('\n', 1)[0][:80]
    recent.append({'datetime': dtm, 'title': title, 'text': txt[:600]})

recent = recent[-N:]
asof = recent[-1]['datetime'][:10] if recent else ''
json.dump({'asof': asof, 'source': URL, 'recent': recent}, open('nmr_kiwoom_tele.json', 'w'), ensure_ascii=False)
print(f'키움 텔레그램: 최근 {len(recent)}개 (asof {asof})')
for r in recent[-5:]: print(' -', r['datetime'], r['title'][:50])
