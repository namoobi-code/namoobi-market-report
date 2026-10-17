#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""compose_crypto.py — 6장 암호화폐 nmr_crypto.json 기계 조립 (v3.81 신설 · 2026-07-22)

서버 사전 DB(WORK/server_crypto_overview|movers|fng.json — Phase 1 curl 캐시)와
fetch_us.py 김프(nmr_kimchi.json)로 nmr_crypto.json 을 조립한다.
CryptoAgent 발행·CoinInfo MCP 재조사 없이 끝 (req9~11·19 서버 DB 우선의 구현체).

업다운 카운트·평균등락은 서버 overview 에 없어, 메인세션이 CoinInfo get_market_overview
1콜 결과를 WORK/nmr_coininfo_extra.json 으로 저장하면 주입한다
({"coins_up":64,"coins_down":28,"avg_change_pct":1.1}). 없으면 null(비차단 — 해당 칸 '-').

사용: python3 compose_crypto.py [WORK]
"""
import json, os, sys, datetime

W = sys.argv[1] if (len(sys.argv) > 1 and os.path.isdir(sys.argv[1])) else '.'


def L(p):
    try:
        return json.load(open(os.path.join(W, p), encoding='utf-8'))
    except Exception:
        return {}


ov = L('server_crypto_overview.json'); mv = L('server_crypto_movers.json')
fg = L('server_crypto_fng.json'); km = L('nmr_kimchi.json'); ex = L('nmr_coininfo_extra.json')
hist = fg.get('hist') or []
today = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).date()  # KST


def near(days):
    if not hist:
        return None
    tgt = today - datetime.timedelta(days=days)
    try:
        best = min(hist, key=lambda r: abs((datetime.date.fromisoformat(r['date']) - tgt).days))
        return {'value': best['v'], 'classification': best['label'], 'date': best['date']}
    except Exception:
        return None


cur = near(0) or {'value': None, 'classification': ''}
fng = {'current': {'value': cur.get('value'), 'classification': cur.get('classification')}, 'history': {}}
# 전일 = 이력 마지막-1 항목 (당일-1 근사검색은 같은 값을 재선택할 위험 — 2026-07-22 실측)
if len(hist) >= 2:
    y = hist[-2]
    fng['history']['yesterday'] = {'value': y['v'], 'classification': y['label'], 'date': y['date']}
for k, d in (('last_week', 7), ('last_month', 30), ('last_3month', 91), ('last_6month', 182), ('last_year', 365)):
    fng['history'][k] = near(d)
for k, v in list(fng['history'].items()):
    if v:
        fng[k] = v['value']; fng[k + '_cls'] = v['classification']


def rows(a):
    return [{'symbol': r.get('sym'), 'name': r.get('name'), 'price': r.get('price'),
             'change_24h': r.get('chg24'), 'volume': r.get('vol'), 'mcap': r.get('mcap'),
             'rank': r.get('rank')} for r in (a or [])[:10]]


out = {
    'market_overview': {
        'total_mcap_usd': ov.get('mcap_usd'), 'total_volume_24h_usd': ov.get('vol24_usd'),
        'mcap_change_24h_pct': ov.get('mcap_chg24'),
        'avg_change_pct': ex.get('avg_change_pct'), 'coins_up': ex.get('coins_up'), 'coins_down': ex.get('coins_down'),
        'total_coins': ov.get('coins'), 'btc_dominance': ov.get('btc_dom'), 'eth_dominance': ov.get('eth_dom'),
        'as_of': ov.get('as_of'), 'source': '서버 crypto_overview DB' + (' + CoinInfo MCP(업다운)' if ex else '')},
    'fear_greed': fng,
    'top_gainers': rows(mv.get('gainers')), 'top_losers': rows(mv.get('losers')),
    'kimchi_premium': km if km else {},
    'asof': str(today),
    'source_note': '서버 사전수집 DB(crypto_overview/movers/fng) + fetch_us 김프 — compose_crypto.py 기계 조립(req9~11·19)'}
json.dump(out, open(os.path.join(W, 'nmr_crypto.json'), 'w'), ensure_ascii=False)
print('nmr_crypto.json OK — fng cur %s · G/L %d/%d · 김프 %d종 · extra %s' % (
    cur.get('value'), len(out['top_gainers']), len(out['top_losers']),
    len((km or {}).get('coins') or []), 'O' if ex else 'X'))
