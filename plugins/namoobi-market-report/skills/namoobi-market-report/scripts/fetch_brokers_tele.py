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
            h = None
            for _host in ('t.me', 'telegram.me'):   # t.me 가 DNS 미허용인 샌드박스 → telegram.me 별칭 폴백
                try:
                    h = urllib.request.urlopen(urllib.request.Request(f'https://{_host}/s/{handle}', headers={'User-Agent': 'Mozilla/5.0'}), timeout=15).read().decode('utf-8', 'replace')
                    break
                except Exception:
                    h = None
            if h is None:
                raise RuntimeError('telegram host unreachable')
            out = []
            for b in re.split(r'<div class="tgme_widget_message ', h)[1:]:
                mt = re.search(r'js-message_text"[^>]*>(.*?)</div>', b, re.S)
                tm = re.search(r'<time[^>]*datetime="([^"]+)"', b)
                if not mt: continue
                txt = strip(mt.group(1))
                if not txt or len(txt) < 8: continue
                # (2026-07-19) 메시지 퍼머링크 — data-post="handle/12345" → https://t.me/handle/12345
                dp = re.search(r'data-post="([^"]+)"', b)
                url = ('https://t.me/' + dp.group(1)) if dp else ('https://t.me/' + handle)
                out.append({'datetime': (tm.group(1)[:16].replace('T', ' ') if tm else ''),
                            'title': txt.split('\n', 1)[0][:80], 'text': txt[:300], 'url': url})
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

# ── (v3.66) KB·NH — 텔레그램 부적합(KB=봇/비공개·NH=전 채널 초대링크)이라 공개 홈페이지 수집 ──
def _get(url, enc='utf-8'):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}),
                                  timeout=15).read().decode(enc, 'replace')

def fetch_kb():
    """KB증권 '오늘의 리서치' rc.kbsec.com/today/index.able — 로그인 無.
    모닝/마감코멘트(데일리 시황) + 당일 발간 리포트 제목 전체."""
    try:
        h = _get('https://rc.kbsec.com/today/index.able')
        body = re.sub(r'<script[\s\S]*?</script>', ' ', h)
        txt = strip(body)
        md = re.search(r'(20\d\d)년\s*(\d{1,2})월\s*(\d{1,2})일', txt)
        asof = f"{md.group(1)}-{int(md.group(2)):02d}-{int(md.group(3)):02d}" if md else ''
        items = re.findall(r'\[([^\[\]]{6,120})\]', txt)
        seen, recent = set(), []
        for t in items:
            t = t.strip()
            if t in seen or t.startswith('KB증권') or '이용안내' in t: continue
            seen.add(t)
            recent.append({'datetime': asof, 'title': t[:80], 'text': t[:300]})
        return 'kb', {'label': 'KB증권', 'channels': ['rc.kbsec.com/today (오늘의 리서치 · 공개)'],
                      'asof': asof, 'recent': recent[:max(N, 8)]}
    except Exception as e:
        return 'kb', {'label': 'KB증권', 'channels': ['rc.kbsec.com/today'], 'asof': '', 'recent': [], 'err': str(e)[:80]}

def fetch_nh():
    """NH투자증권 모바일 리서치 목록 — 로그인 無 (EUC-KR).
    시황·투자전략(rshPprDitCd=02: Global Markets Morning Brief 데일리) + 최신 전체."""
    recent, seen = [], set()
    for url in ('https://m.nhqv.com/research/boardList?rshPprDitCd=02',
                'https://m.nhsec.com/research/newestBoardList'):
        try:
            h = _get(url, 'cp949')
            body = re.sub(r'<script[\s\S]*?</script>', ' ', h)
            txt = strip(body)
            # "제목 저자 2026.07.16" 패턴 — 날짜 앞의 제목 블록 추출
            for m in re.finditer(r'([가-힣A-Za-z0-9\[\]〔〕《》()/&·%~+,.\'" \-]{8,110}?)\s+([가-힣]{2,4})?\s*(20\d\d\.\d{2}\.\d{2})', txt):
                t = m.group(1).strip(' -·')
                d = m.group(3).replace('.', '-')
                if len(t) < 8 or t in seen or '로그' in t or '검색' in t: continue
                seen.add(t)
                recent.append({'datetime': d, 'title': t[:80], 'text': t[:300]})
        except Exception:
            pass
    recent.sort(key=lambda m: m['datetime'])
    recent = recent[-max(N, 8):]
    return 'nh', {'label': 'NH투자증권', 'channels': ['m.nhqv.com/research (시황·전략 · 공개)', 'm.nhsec.com/research (최신 전체 · 공개)'],
                  'asof': (recent[-1]['datetime'][:10] if recent else ''), 'recent': recent}

with ThreadPoolExecutor(max_workers=4) as ex:  # 동시성 완화로 텔레그램 throttle 회피
    res = dict(ex.map(fetch_firm, FIRMS.items()))
for fn in (fetch_kb, fetch_nh):   # (v3.66) KB·NH 공개 홈페이지 수집 — 실패해도 비차단(빈 recent)
    try:
        k, v = fn(); res[k] = v
    except Exception as _e:
        print('web-broker fail:', fn.__name__, _e)
json.dump(res, open('nmr_brokers_tele.json', 'w'), ensure_ascii=False)
miss = [k for k, v in res.items() if not v['recent']]
for k, v in res.items():
    print(f"{k:8} {v['label']:8} asof {v['asof'] or '-':10} msgs {len(v['recent'])}  | {(v['recent'][-1]['title'] if v['recent'] else '(none)')[:40]}")
if miss: print('MISS(재시도 권장):', miss)
