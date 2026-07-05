# -*- coding: utf-8 -*-
"""
[부록D] AI 반도체 밸류체인 관계도(해자 지도) 정적 이미지 생성기 (v3.52)

- 매일 실행되는 파이프라인이 아니라, 종목 구성이 바뀔 때만 1회 실행하는 자산 생성기.
- 산출물: assets/appd_valuechain.html (전체 미리보기용)
          assets/appd_valuechain_1.png / _2.png / _3.png (docx 삽입용, 페이지 분할 3장)
- 요구사항: pip install weasyprint pillow --break-system-packages
            시스템에 Noto Sans CJK KR + pdftocairo(poppler) 필요 (Cowork 샌드박스 기본 충족)
- 빌더 연동: build_report.js renderAppendixD 가 assets/appd_valuechain_{1..3}.png 를 찾아
             $WORK/charts/ 로 무결성 검증(IEND) 후 복사·삽입. 파일 없으면 부록D 자동 생략.
"""
import os, subprocess, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))

B1 = "b1"  # 파랑: 독점·준독점 (대체재 사실상 없음)
B2 = "b2"  # 황색: 과점·복점·양강

# (분류, 티커표기, 회사명, 배지텍스트|None, 배지종류, 해자 한 줄)
SECTIONS = [
 ("1. 수요 — 빅테크 (돈의 출발점)", "연 수천억 달러 AI CAPEX 집행", [
  ("MSFT","Microsoft",None,None,"OpenAI 동맹 + Azure — AI 소프트웨어 배급망 장악"),
  ("GOOGL","Alphabet",None,None,"자체 TPU 설계 + 검색·클라우드 데이터 해자"),
  ("AMZN","Amazon",None,None,"AWS 점유 1위 + 자체칩(Trainium)으로 원가 통제"),
  ("META","Meta",None,None,"광고 AI로 CAPEX를 즉시 수익화하는 구조"),
  ("ORCL","Oracle",None,None,"OCI 대형 AI 계약 수주로 '제4 클라우드' 부상"),
 ]),
 ("2. 설계 — 팹리스 · EDA · 인터커넥트", "공장 없이 설계도와 생태계로 지배", [
  ("NVDA","NVIDIA","독점적",B1,"CUDA 소프트웨어 락인 — 칩이 아니라 생태계가 해자"),
  ("AMD","AMD",None,None,"유일하게 규모 있는 GPU 대안 — 수요처가 키워주는 2등"),
  ("AVGO","Broadcom","과점",B2,"빅테크 자체칩(ASIC) 설계 대행 + 네트워크칩 지배"),
  ("MRVL","Marvell",None,None,"커스텀 실리콘 2강 — Broadcom과 시장 분할"),
  ("ARM","Arm","표준",B1,"저전력 CPU 설계 IP의 사실상 표준 — 로열티 수취"),
  ("SNPS","Synopsys","복점",B2,"EDA 툴 없인 칩 설계 불가 — Cadence와 복점"),
  ("CDNS","Cadence","복점",B2,"설계·검증 EDA 복점의 다른 한 축"),
  ("ANET","Arista",None,None,"GPU 수만 개를 묶는 AI 클러스터 스위치 1위"),
  ("CRDO","Credo",None,None,"칩 간 고속연결 SerDes — 대역폭 병목 해소"),
  ("ALAB","Astera Labs",None,None,"PCIe/CXL 리타이머 선점 — AI 서버 표준 부품화"),
 ]),
 ("3. 장비 · 소재 — 제조의 병목 공급자", "파운드리·메모리가 전량 의존", [
  ("ASML","ASML","완전독점",B1,"EUV 노광기 지구상 유일 제조사 — 최상위 병목"),
  ("AMAT","Applied Materials",None,None,"증착·이온주입 등 최광폭 장비 포트폴리오"),
  ("LRCX","Lam Research","과점",B2,"식각 장비 강자 — 적층 늘수록 수혜"),
  ("KLAC","KLA","독점적",B1,"검사·계측 점유 과반 — 수율 관리의 관문"),
  ("8035.T","Tokyo Electron","준독점",B1,"포토레지스트 도포 트랙 등 준독점 영역 보유"),
  ("6857.T","Advantest","양강",B2,"AI 가속기·HBM 테스터 양강 — 검사 없인 출하 불가"),
  ("6146.T","Disco","준독점",B1,"웨이퍼 그라인더·다이서 사실상 독점 — HBM 적층 필수"),
  ("4063.T","Shin-Etsu","양강",B2,"실리콘 웨이퍼·포토레지스트 최상위 소재"),
  ("3436.T","SUMCO","양강",B2,"웨이퍼 양강의 다른 축 — 신규진입 사실상 불가"),
 ]),
 ("4. 제조 — 파운드리 & 메모리(HBM)", "설계도를 실물 칩으로", [
  ("TSM","TSMC","독점적",B1,"3nm 이하 선단공정 사실상 독점 — NVDA·AMD·AVGO 전부 여기서 생산"),
  ("005930","삼성전자",None,None,"메모리+파운드리 동시 보유 유일 기업"),
  ("INTC","Intel",None,None,"미국 내 파운드리 재건 — 지정학이 만든 옵션가치"),
  ("000660","SK하이닉스","1위",B1,"HBM 점유 1위 — NVIDIA 최우선 공급사 지위"),
  ("MU","Micron","3강",B2,"HBM·DRAM 3강 — 미국 유일 메모리사"),
 ]),
 ("5. 후공정 — 패키징 · 테스트 · 기판", "HBM 적층과 서버 조립의 관문", [
  ("042700","한미반도체","선두",B1,"HBM TC본더 선두 — SK하이닉스와 동반 성장"),
  ("095340","ISC",None,None,"테스트 소켓 핵심 — 신규 칩마다 반복 매출"),
  ("058470","리노공업",None,None,"고마진 테스트핀·소켓 — 영업이익률 40%대 해자"),
  ("353200","대덕전자",None,None,"FC-BGA 서버 패키징 기판 강자"),
  ("007660","이수페타시스",None,None,"AI 서버·스위치용 고다층 MLB 직접 수혜"),
  ("AMKR","Amkor","과점",B2,"글로벌 OSAT 2위 — 첨단 패키징 외주 수혜"),
 ]),
 ("6. 전력 · 인프라 — 데이터센터를 돌리는 힘", "칩보다 전기가 부족한 시대", [
  ("VRT","Vertiv","핵심",B1,"전력·액체냉각·UPS 토탈 — 데이터센터 순수 수혜주"),
  ("ETN","Eaton",None,None,"배전·전력관리 글로벌 대표 — 수주잔고 해자"),
  ("GEV","GE Vernova",None,None,"가스터빈 공급부족 — 수년치 주문 선점"),
  ("CEG","Constellation","희소",B1,"원전 무탄소 전력 — 빅테크 장기 PPA 직계약"),
  ("PWR","Quanta",None,None,"송전망 시공 인력·장비 — 복제 어려운 실행력"),
  ("NVT","nVent",None,None,"전력기기 인클로저·열관리 니치 강자"),
  ("VST","Vistra",None,None,"발전+소매판매 통합 — 전력가격 상승 직수혜"),
  ("010120","LS ELECTRIC",None,None,"배전반·스마트그리드 국내 핵심 — 북미 수출 확대"),
  ("298040","효성중공업",None,None,"초고압 변압기·GIS·ESS — 미국 현지 공장 보유"),
  ("267260","HD현대일렉트릭","공급부족",B2,"변압기 글로벌 품귀 — 수년치 수주잔고"),
  ("034020","두산에너빌리티",None,None,"원전 주기기·가스터빈 — SMR 옵션 보유"),
 ]),
]

ARROWS = [
 "AI 칩 주문 — CAPEX가 아래로 흘러내린다",
 "설계도 → 위탁생산 (장비·소재 없이는 공장이 못 돈다)",
 "장비·소재 공급",
 "칩 완성 → 적층·패키징·테스트 (한국 기업 밀집 구간)",
 "AI 서버 가동 → 전력 수요 폭증 (새로운 병목)",
]
CYCLE = "⟳ 완성된 AI 데이터센터 → 다시 1번 빅테크의 매출 → CAPEX 재투자 사이클"

CSS = """
@page { size: 840px 2600px; margin: 0; }
body { font-family:'Noto Sans CJK KR','Noto Sans KR',sans-serif; margin:0; padding:10px;
       background:#ffffff; color:#0f172a; width:820px; box-sizing:border-box; }
.leg { font-size:12px; color:#475569; margin:0 0 10px; }
.leg .b1,.leg .b2 { float:none; }
.sec { border:1px solid #dbe2ea; border-radius:12px; padding:12px 14px; background:#f8fafc; }
.sh  { margin:0 0 9px; }
.sh .t { font-size:15.5px; color:#0f172a; letter-spacing:-0.2px; }
.sh .s { font-size:12px; color:#94a3b8; margin-left:8px; }
.cards { display:flex; flex-wrap:wrap; margin:-3px; }
.card { box-sizing:border-box; width:246px; margin:3px; border:1px solid #dbe2ea;
        border-radius:8px; background:#ffffff; padding:7px 9px 8px; }
.tk { font-size:13px; color:#0f172a; }
.nm { font-size:11.5px; color:#64748b; margin-left:4px; }
.mo { font-size:11px; color:#475569; margin-top:3px; line-height:1.5; }
.b1,.b2 { float:right; font-size:10.5px; padding:1px 7px; border-radius:8px; margin-left:4px; }
.b1 { background:#dbeafe; color:#1d4ed8; }
.b2 { background:#fef3c7; color:#b45309; }
.arr { text-align:center; color:#475569; font-size:12.5px; padding:9px 0; }
.cyc { text-align:center; color:#1d4ed8; font-size:12.5px; padding:10px 0 2px; }
"""

def card(tk, nm, bt, bk, mo):
    b = f'<span class="{bk}">{bt}</span>' if bt else ""
    return (f'<div class="card">{b}<span class="tk">{tk}</span>'
            f'<span class="nm">{nm}</span><div class="mo">{mo}</div></div>')

def section(i):
    t, s, rows = SECTIONS[i]
    cards = "".join(card(*r) for r in rows)
    return (f'<div class="sec"><div class="sh"><span class="t">{t}</span>'
            f'<span class="s">{s}</span></div><div class="cards">{cards}</div></div>')

def arrow(i):
    return f'<div class="arr">▼&nbsp;&nbsp;{ARROWS[i]}</div>'

LEGEND = ('<div class="leg"><span class="b1">독점·준독점</span> 대체재가 사실상 없음'
          '&nbsp;&nbsp;&nbsp;<span class="b2">과점·복점·양강</span> 2~3개사가 시장 분할</div>')

PARTS = [
    LEGEND + section(0) + arrow(0) + section(1),
    section(2) + arrow(2) + section(3),
    section(4) + arrow(4) + section(5) + f'<div class="cyc">{CYCLE}</div>',
]
# 부록 흐름상 파트 사이 화살표(1→2 경계는 arrow(1), 2→3 경계는 arrow(3))를 각 파트 말미에 부착
PARTS[0] += arrow(1)
PARTS[1] += arrow(3)

FULL = LEGEND + "".join(
    section(i) + (arrow(i) if i < 5 else f'<div class="cyc">{CYCLE}</div>')
    for i in range(6))

def html_doc(body):
    return f'<html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{body}</body></html>'

def render(body, out_png):
    from weasyprint import HTML
    import tempfile
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        pdf = os.path.join(td, "x.pdf")
        HTML(string=html_doc(body)).write_pdf(pdf)
        base = os.path.join(td, "x")
        subprocess.run(["pdftocairo", "-png", "-r", "192", "-singlefile", pdf, base], check=True)
        im = Image.open(base + ".png").convert("RGB")
        px = im.load()
        w, h = im.size
        bottom = 0
        for y in range(h - 1, -1, -1):
            row_has = any(px[x, y] != (255, 255, 255) for x in range(0, w, 8))
            if row_has:
                bottom = y
                break
        im.crop((0, 0, w, min(h, bottom + 24))).save(out_png, optimize=True)
        print(out_png, im.size[0], "x", min(h, bottom + 24))

def main():
    with open(os.path.join(HERE, "appd_valuechain.html"), "w", encoding="utf-8") as f:
        f.write(html_doc(FULL))
    for i, body in enumerate(PARTS, 1):
        render(body, os.path.join(HERE, f"appd_valuechain_{i}.png"))
    print("done")

if __name__ == "__main__":
    main()
