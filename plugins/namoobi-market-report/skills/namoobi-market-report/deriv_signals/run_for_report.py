# -*- coding: utf-8 -*-
"""
run_for_report.py — 일일 보고서 실행 시 3.1.21 파생 포지셔닝 '라이브' 데이터 생성(완전 비차단).

사용:
    python run_for_report.py <출력경로>      # 예: <보고서실행폴더>\\nmr_deriv_positioning.json

동작:
  1) 필수 라이브러리(numpy·pandas·yfinance) 확인 → 없으면 requirements.txt 로 1회 설치 시도.
  2) DB 없으면 run_backfill.py(최초 1년, ~1-2분), 있으면 daily_update.py(증분) 실행.
  3) export_snapshot.py 로 DB → 출력 JSON.
어떤 단계가 실패/타임아웃해도 **exit 0** — merge/build 가 내장 스냅샷(DERIV_POS_DEFAULT)으로 렌더하므로 보고서는 절대 막히지 않는다.
data.go.kr 키는 config._find_secrets() 가 상위 SECURITY/secrets.env 등에서 자동 탐색(없으면 KOSPI200 선물/옵션만 skip).
"""
import os, sys, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.getcwd(), "nmr_deriv_positioning.json")
# 2번째 인자(선택) = 안정 DB 경로. 지정하면 재백필 방지·이력 유지(권장: ..\_market_report_data\deriv_signals.db).
# 플러그인은 매 실행 git 추출본($RUN)에서 코드를 돌리므로, DB만은 영구 경로로 분리해야 매번 1년 백필을 반복하지 않는다.
if len(sys.argv) > 2 and sys.argv[2].strip():
    os.environ["DERIV_DB"] = os.path.abspath(sys.argv[2])
if os.environ.get("DERIV_DB"):
    try:
        os.makedirs(os.path.dirname(os.environ["DERIV_DB"]), exist_ok=True)
    except Exception:
        pass
    print("[deriv] DB(안정):", os.environ["DERIV_DB"])


def _run(args, timeout):
    try:
        r = subprocess.run([PY] + args, cwd=BASE, timeout=timeout,
                           capture_output=True, text=True)
        tail = [ln for ln in (r.stdout or "").splitlines() if ln.strip()][-1:]
        print("  [deriv]", " ".join(args), "->", (tail[0][:120] if tail else ("rc=" + str(r.returncode))))
        return r.returncode == 0
    except Exception as e:
        print("  [deriv]", " ".join(args), "실패(무시):", repr(e)[:90])
        return False


def _have(mod):
    try:
        __import__(mod); return True
    except Exception:
        return False


def main():
    # 1) 의존성 확인 → 없으면 1회 설치 시도(best-effort)
    if not all(_have(m) for m in ("numpy", "pandas", "yfinance")):
        print("[deriv] 필수 라이브러리 설치 시도(requirements.txt)...")
        try:
            subprocess.run([PY, "-m", "pip", "install", "-q", "-r",
                            os.path.join(BASE, "requirements.txt")], timeout=900)
        except Exception as e:
            print("  [deriv] pip 실패(무시):", repr(e)[:90])
    if not _have("pandas"):
        print("[deriv] 필수 라이브러리 없음 → 내장 스냅샷 사용(skip)")
        return 0

    # 2) DB 없으면 최초 백필, 있으면 증분 갱신
    db = os.environ.get("DERIV_DB") or os.path.join(BASE, "deriv_signals.db")
    if os.path.exists(db) and os.path.getsize(db) > 10000:
        _run(["daily_update.py"], 300)
    else:
        print("[deriv] DB 없음 → 최초 백필(1~2분 소요)")
        _run(["run_backfill.py"], 900)

    # 3) 스냅샷 내보내기 → 보고서 실행폴더의 nmr_deriv_positioning.json
    _run(["export_snapshot.py", OUT], 120)

    # 4) KRX 공식 국내 시장데이터(지수·VKOSPI·섹터·국고채·금·ETF) → 웹서치 대체용
    _run(["krx_market_snapshot.py",
          os.path.join(os.path.dirname(os.path.abspath(OUT)), "nmr_krx_market.json")], 120)

    print("[deriv] 완료:", OUT if os.path.exists(OUT) else "(미생성 — 빌더 내장 스냅샷 사용)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("[deriv] 예외(무시, 비차단):", repr(e)[:100]); sys.exit(0)
