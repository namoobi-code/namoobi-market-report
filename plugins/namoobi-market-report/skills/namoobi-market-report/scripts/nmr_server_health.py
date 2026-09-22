#!/usr/bin/env python3
"""nmr_server_health.py "$WORK" — (v4.08 · 2026-09-22 신설) 서버 사전 DB '빈 값·stale' 게이트.

배경: 서버 크론이 **정상 종료하면서 빈 결과**를 내면(네이버 리서치 SPA 이관 → broker_reports 0건 6일,
KRX 빈 응답 캐시 오염 → krx 스냅샷 asof null 6일) 보고서는 폴백(웹서치·carry-forward)으로 조용히 통과해
며칠간 아무도 모른다. 이 스크립트가 Phase 1 초입에 `$WORK/server_*.json` 캐시(없으면 서버 직접 curl)를
읽어 항목별 **비어 있음 / 오래됨** 을 판정하고 `$WORK/nmr_server_health.json` 에 저장한다.
verify_report.js(req40) 가 이 파일을 읽어 warnings 로 올리고, Phase 6 결과 보고 [서버 사전 DB 상태] 에 그대로 붙인다.

판정 기준(항목별 기대 갱신 주기 → stale 시간):
  broker_reports  firms≥5 & recent 합계≥1            · 24h(주말 72h)
  ib_insights     pool+pool_72h 합계≥1               · 24h
  news_pool       토픽 합계 ≥30                       · 6h
  events_calendar upcoming ≥5                        · 24h
  policy_rates    rows ≥6 · 각 rate 비공란            · 48h
  m7_estimates    rows ≥7                             · 24h
  factset_insight posts ≥1                           · 7d
  brokers3        korea_inv.today 비공란              · 48h(주말 96h)
  ism_pmi         mfg·svc value 존재                  · 45d
  crypto_overview mcap_usd>0                         · 3h
  crypto_movers   gainers·losers 각 ≥5                · 3h
  etf_quotes      rows ≥30                           · 24h
  krx_market(deriv 회수본 nmr_krx_market.json) asof 비공란·indices≥1 · —
  deriv(nmr_deriv_positioning.json) rows ≥1          · —
비차단: exit 0 고정. 출력 1줄 요약 + 경고 목록.
"""
import json, os, sys, glob, subprocess, urllib.request
from datetime import datetime, timedelta

W = sys.argv[1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]) else '.'
SRV = "http://161.33.190.254/api/db/"
NOW = datetime.now()
WEEKEND_ADJ = 48 if NOW.weekday() in (0, 6) else 0   # 월요일·일요일 실행은 주말 공백 감안


def load(name):
    p = os.path.join(W, f"server_{name}.json")
    try:
        d = json.load(open(p, encoding='utf-8'))
        if d:
            return d
    except Exception:
        pass
    try:
        return json.loads(urllib.request.urlopen(SRV + name, timeout=15).read().decode('utf-8', 'ignore'))
    except Exception:
        return None


def age_h(d):
    for k in ('as_of', 'asof', 'updated', 'marker'):
        v = str((d or {}).get(k) or '')
        for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d'):
            try:
                return (NOW - datetime.strptime(v[:16] if ' ' in v else v[:10], fmt)).total_seconds() / 3600
            except Exception:
                continue
    return None


def _n(x):
    return len(x) if isinstance(x, (list, dict)) else 0


CHECKS = [
    ("broker_reports", lambda d: _n(d.get('firms')) >= 5 and sum(_n(v) for v in (d.get('recent') or {}).values()) >= 1,
     24 + WEEKEND_ADJ, "증권사 리포트 DB(네이버 리서치) — research_watch.py 소스 구조 변경 의심"),
    ("ib_insights", lambda d: sum(_n(v) for v in (d.get('pool') or {}).values()) + sum(_n(v) for v in (d.get('pool_72h') or {}).values()) >= 1,
     24, "IB 5사 보도 풀 전무 — 구글뉴스 RSS/쿼리 점검"),
    ("news_pool", lambda d: sum(_n(v) for v in (d.get('topics') or d.get('pool') or {}).values()) >= 30 if isinstance(d.get('topics') or d.get('pool'), dict) else _n(d.get('items')) >= 30,
     6, "뉴스 풀 부족 — report_prefetch --news 크론 점검"),
    ("events_calendar", lambda d: _n(d.get('upcoming')) >= 5, 24, "이벤트 캘린더 뼈대 부족"),
    ("policy_rates", lambda d: _n(d.get('rows')) >= 6 and all(str(r.get('rate') or '').strip() for r in d.get('rows')), 48, "정책금리 6개국 결측"),
    ("m7_estimates", lambda d: _n(d.get('rows')) >= 7, 24, "M7 컨센서스 DB 결측"),
    ("factset_insight", lambda d: _n(d.get('posts')) >= 1, 24 * 7, "FactSet RSS 결측"),
    ("brokers3", lambda d: bool(((d.get('korea_inv') or {}).get('today') or '').strip()), 48 + WEEKEND_ADJ, "한투 '한눈에 투데이' 결측"),
    ("ism_pmi", lambda d: (d.get('mfg') or {}).get('value') is not None and (d.get('svc') or {}).get('value') is not None, 24 * 45, "ISM PMI 결측"),
    ("crypto_overview", lambda d: (d.get('mcap_usd') or 0) > 0, 3, "크립토 시장개요 결측"),
    ("crypto_movers", lambda d: _n(d.get('gainers') or d.get('top_gainers')) >= 5 and _n(d.get('losers') or d.get('top_losers')) >= 5, 3, "크립토 등락 상위 결측"),
    ("etf_quotes", lambda d: _n(d.get('rows') or d.get('items')) >= 30, 24, "美 ETF 시세 스냅샷 결측"),
]

out = {"as_of": NOW.strftime('%Y-%m-%d %H:%M'), "items": [], "warnings": []}
for name, ok_fn, stale_h, hint in CHECKS:
    d = load(name)
    it = {"name": name, "ok": False, "age_h": None, "note": ""}
    if not isinstance(d, dict):
        it["note"] = "조회 실패/비JSON"; out["warnings"].append(f"[server:{name}] 조회 실패 — {hint}")
    else:
        try:
            filled = bool(ok_fn(d))
        except Exception:
            filled = False
        a = age_h(d); it["age_h"] = round(a, 1) if a is not None else None
        if not filled:
            it["note"] = "빈 값"; out["warnings"].append(f"[server:{name}] 빈 값(as_of {d.get('as_of') or d.get('marker')}) — {hint}")
        elif a is not None and a > stale_h:
            it["note"] = f"stale {a:.0f}h"; out["warnings"].append(f"[server:{name}] stale {a:.0f}h(>{stale_h}h) — 크론 중단 의심")
        else:
            it["ok"] = True
    out["items"].append(it)

# 회수본(파일) 점검 — deriv 크론 산출물
try:
    k = json.load(open(os.path.join(W, 'nmr_krx_market.json'), encoding='utf-8'))
    ok = bool(k.get('asof')) and _n(k.get('indices')) >= 1
    out["items"].append({"name": "krx_market", "ok": ok, "note": "" if ok else (k.get('error') or '빈 값')})
    if not ok:
        out["warnings"].append(f"[server:krx_market] KRX 스냅샷 빈 값({k.get('error')}) — krx_openapi 캐시/키 점검")
except Exception:
    out["items"].append({"name": "krx_market", "ok": False, "note": "파일 없음"})
try:
    dv = json.load(open(os.path.join(W, 'nmr_deriv_positioning.json'), encoding='utf-8'))
    ok = _n(dv.get('rows')) >= 1
    out["items"].append({"name": "deriv", "ok": ok, "note": "" if ok else "rows 없음"})
    if not ok:
        out["warnings"].append("[server:deriv] 파생 포지셔닝 스냅샷 rows 없음 — 서버 05:50 크론 점검")
except Exception:
    out["items"].append({"name": "deriv", "ok": False, "note": "파일 없음(run_for_report 이전 실행이면 무시)"})

json.dump(out, open(os.path.join(W, 'nmr_server_health.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
n_ok = sum(1 for i in out["items"] if i["ok"])
print(f"[server-health] {n_ok}/{len(out['items'])} 정상 · 경고 {len(out['warnings'])}건 → nmr_server_health.json")
for w in out["warnings"]:
    print("  ⚠", w)
sys.exit(0)
