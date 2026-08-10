# -*- coding: utf-8 -*-
"""
[부록F] 피지컬 AI(휴머노이드) 밸류체인 관계도(해자 지도) 정적 이미지 생성기 (v3.72)

- 매일 실행되는 파이프라인이 아니라, 구성이 바뀔 때만 1회 실행하는 자산 생성기.
- 산출물: assets/appf_physical_ai.html (전체 미리보기)
          assets/appf_physical_ai_1.png / _2.png / _3.png (docx 삽입용, 페이지 분할 3장)
- 요구사항: pip install weasyprint pillow --break-system-packages / Noto Sans CJK KR + pdftocairo
- 빌더 연동: build_report.js renderAppendixF 가 assets/appf_physical_ai_{1..3}.png 를 찾아
             $WORK/charts/ 로 무결성(IEND) 검증 후 복사·삽입. 파일 없으면 부록F 자동 생략.
- 근거: 한경비즈니스 2026.08.05-11 커버스토리 '피지컬 AI 핵심 밸류체인'(6계층) + 모건스탠리 2025 핵심기업,
        골드만삭스(2025 휴머노이드 생산량 국가별), 옴디아(2025 출하 점유), 딜로이트·프리시던스리서치(수요·시뮬레이터).
"""
import os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

B1 = "b1"  # 파랑: 독점·준독점 (대체재 사실상 없음)
B2 = "b2"  # 황색: 과점·복점·양강
B3 = "b3"  # 회색: 비상장 (투자 불가 — 구조 이해용)

# (표기, 회사명, 배지텍스트|None, 배지종류, 해자 한 줄)
SECTIONS = [
 ("1. 완성체 — 휴머노이드 메이커 (부품 발주의 출발점)",
  "로봇 1대 = 신규 부품 약 1만 개 · 2025년 생산량 중국 87.7%(1만2868대)·미국 3.1%·한국 1.2% [골드만삭스]", [
  ("TSLA","테슬라 옵티머스",None,None,"칩·SW 수직통합 + 기가팩토리 라인 — 단가 2만~3만 달러를 노린 양산 설계"),
  ("005380","현대차그룹·BD","수직계열",B2,"아틀라스 2028년 미국 공장 투입 — 액추에이터(모비스)·물류(글로비스) 내재화"),
  ("피겨AI (Figure)","",None,B3,"오픈AI 협업 → 자체 모델 헬릭스 02로 전환, 물류 현장 200시간 실증"),
  ("애지봇 (AgiBot)","비상장","점유 1위",B2,"2025년 5168대 출하·점유 39%[옴디아] — 로봇 렌털 플랫폼까지 선점"),
  ("유니트리 (Unitree)","비상장","가성비",B2,"엔비디아 아이작 GR00T 레퍼런스 파트너 — 가격으로 시장 압박"),
  ("9880.HK","UBTech",None,None,"워커S 양산 — 중국 산업용 휴머노이드 선두권"),
  ("002594","BYD",None,None,"8월 첫 휴머노이드 공개 — 판매 현장 우선 배치(서비스형)"),
  ("XPEV","샤오펑 (XPeng)",None,None,"광저우 공장에서 '아이언(IRON)' 소량 테스트 생산"),
  ("277810","레인보우로보틱스",None,None,"삼성전자 자회사 — 국내 휴머노이드 상용화의 축"),
  ("앱트로닉·1X·에이로봇","",None,B3,"미국·노르웨이·한국 후발 — 손 자유도(1X 25)와 데이터 수급이 승부처"),
 ]),
 ("2. 두뇌 — 파운데이션 모델(VLA) · 온디바이스 AI 칩",
  "챗GPT와 다른 난이도: 카메라 영상을 0.1초 안에 관절 명령으로 — 빅테크가 선점", [
  ("NVDA","NVIDIA","사실상 표준",B1,"GR00T N1.6(행동)+코스모스(물리추론)+아이작 심(훈련)+젯슨 토르(실행) 풀스택 장악"),
  ("GOOGL","구글 딥마인드","선두",B1,"제미나이 로보틱스 1.5 + ER 1.6 — 언어·추론을 동작으로 확장한 VLA"),
  ("QCOM","퀄컴",None,None,"드래곤윙 IQ10 — 700TOPS·18코어로 저전력 온디바이스 추론 도전"),
  ("AMD","AMD",None,None,"로봇 가속기의 유일한 규모 대안 — 완성체가 키우는 2등"),
  ("ARM","Arm","IP 표준",B1,"저전력 엣지 설계 IP — 로봇 '소뇌'의 기본 아키텍처, 로열티 수취"),
  ("000660","SK하이닉스","HBM 1위",B1,"로봇 영상·센서 학습량 폭증 → AI 데이터센터 HBM 수요로 환류"),
  ("005930","삼성전자",None,None,"DX 직속 로봇 조직 + 데이터팩토리 — 메모리와 완성체를 동시에 보유"),
  ("오픈AI","",None,B3,"모델 생태계 주도 — 완성체와 제휴/결별을 반복하며 두뇌 표준 경쟁"),
 ]),
 ("3. 신경·감각 — 비전 · 라이다 · 촉각 · IMU (센서 퓨전)",
  "로봇 1대당 카메라 6대 이상 + 깊이·촉각·힘토크 센서 수십 개 · 센서 없는 로봇은 자기 움직임도 제어 못 한다", [
  ("6758.T","소니그룹","이미지센서 1위",B1,"로봇 '눈'의 기본 공급자 — 완성체 대부분이 의존"),
  ("HSAI","헤사이 (Hesai)","라이다 1위",B2,"로봇개 부이봇 공개 = 라이다를 휴머노이드 표준으로 밀어붙이는 쇼케이스"),
  ("STM","ST마이크로",None,None,"MEMS·ToF — 소형 로봇 감각의 범용 공급자"),
  ("TXN","텍사스인스트루먼트",None,None,"아날로그·모터 드라이버 — 신경계 저변 부품"),
  ("6762.T","TDK","IMU 강자",B2,"초정밀 관성센서 — LG이노텍과 차세대 멀티센싱 모듈 공동개발(7/28)"),
  ("011070","LG이노텍",None,None,"광학 비전 + TDK IMU 결합 → 밀리초 단위 센서퓨전 모듈로 반도체급 패키지화"),
  ("009150","삼성전기",None,None,"MLCC·카메라모듈 — 로봇 1대당 수동부품 탑재량 급증 수혜"),
  ("204320","HL만도",None,None,"자율주행 레이더·센서 역량의 로보틱스 전용"),
  ("214430","아이쓰리시스템",None,None,"적외선 영상센서 국산화 — 야간·열 감지"),
  ("464080","에스오에스랩",None,None,"고정형 라이다 국산화 — 정부가 지목한 3대 취약부품 대응"),
  ("메타(촉각 스킨)·샤르파","",None,B3,"손가락당 촉각 픽셀 1000개·0.005뉴턴 감지 — 촉각이 마지막 관문"),
 ]),
 ("4. 근육·관절 — 액추에이터 · 감속기 · 모터 · 베어링 · 영구자석",
  "제조원가의 30~60%(평균 40%) · 1대당 액추에이터 25~30개 이상 · 가장 견고한 기술 장벽", [
  ("6324.T","하모닉드라이브","세계 표준",B1,"파동기어 감속기 — 관절 정밀도의 기준, 수십 년 내구성 데이터가 해자"),
  ("6268.T","나브테스코","과점",B2,"산업용 RV 감속기 — 대형 관절 내구성의 다른 축"),
  ("6594.T","니덱","소형모터 1위",B2,"손가락·관절 구동 모터의 대량 공급자"),
  ("6481.T","THK",None,None,"LM가이드·리니어 액추에이터 최상위"),
  ("6471.T","NSK",None,None,"초정밀 베어링 — 관절 마찰·수명의 결정 부품"),
  ("2049.TW","하이윈 (HIWIN)",None,None,"볼스크루 — 리니어 액추에이터 핵심 스크루"),
  ("TKR / RRX","팀켄 · 리갈렉스노드",None,None,"베어링·모션컨트롤 — 미국계 고하중 관절 공급"),
  ("300124","이노반스 (Inovance)","중국 1위",B2,"서보모터 — 중국 휴머노이드 원가경쟁력의 뿌리"),
  ("002747","에스툰 (Estun)",None,None,"중국 로봇 본체·액추에이터 수직계열"),
  ("LYC.AX / 600111","라이너스·북방희토","원료 병목",B1,"영구자석 희토류 — 중국 편중이 모터 원가·수급의 지배 변수"),
  ("012330","현대모비스","공급 파트너",B2,"아틀라스 핵심 액추에이터 낙점 — 시제품 공급 후 본격 양산 체제"),
  ("066570","LG전자",None,None,"세탁기 DD모터 기술의 로봇 전용 — 가전에서 온 구동 노하우"),
  ("108490","로보티즈",None,None,"모듈형 액추에이터 다이나믹셀 — NASA ISS 납품 이력"),
  ("389500","에스비비테크",None,None,"하모닉 감속기 국산화 — 일본 의존 대체 시도"),
  ("004380","삼익THK",None,None,"리니어모션 국내 1위 — THK 기술 제휴"),
  ("맥슨모터 · 1X · 샤르파 · 우지","",None,B3,"로봇 손 자유도 경쟁(1X 25 · 샤르파 22 · 우지 20, 인간 27) — '몸체보다 손이 비싸다'"),
 ]),
 ("5. 골격 · 에너지 — 경량 소재(CFRP·알루미늄) · 휴머노이드 전용 배터리",
  "'몇백 g'이 상품성을 좌우 · 배터리는 휴머노이드 가격의 5~10% · 아틀라스 3700Wh로 약 4시간 작동", [
  ("HXL","헥셀 (Hexcel)","항공급",B2,"탄소섬유 복합재 — 팔다리 경량화의 대표 소재주(기업가치 약 12조원)"),
  ("3402.T","도레이 (Toray)","CFRP 1위",B1,"탄소섬유 세계 1위 — 현대차그룹과 미래 모빌리티 소재 협력"),
  ("알코닉 (Arconic)","",None,B3,"고강도 알루미늄 1위 — 가격을 앞세워 CFRP와 경쟁(아폴로 인수로 비상장)"),
  ("006400","삼성SDI","전고체 선두",B2,"AI 로봇용 파우치 전고체 '솔리드스택' 공개 — 2027년 양산 목표, 작동 8시간 지향"),
  ("373220","LG에너지솔루션","3사 납품",B2,"피겨AI·보스턴다이내믹스·테슬라 모두에 공급 — 2028년 800Wh/L 로드맵"),
  ("096770","SK이노베이션 (SK온)",None,None,"대전 파일럿 플랜트 — 2029년 전고체 상용화 목표"),
  ("300750","CATL",None,None,"LFP 고밀도 — 중국 휴머노이드 물량을 등에 업은 원가 공세"),
  ("298050","효성첨단소재",None,None,"탄소섬유 국산화 — 로봇 경량화 소재 공급"),
  ("199430","케이엔알시스템",None,None,"유압·로봇 구동 시스템 — 경량 부품 국산화 참여"),
  ("엔진AI","",None,B3,"항공우주급 마그네슘–알루미늄 합금 일체형 다이캐스팅 — 15분에 1대 라인 시도"),
 ]),
 ("6. 가상훈련장 — 시뮬레이터 · 물리엔진 · 모션 데이터 (데이터 폭발의 시발점)",
  "현실 1초 → 가상 수십만 시간으로 증폭 · 시뮬레이터 시장 2025년 8.2억달러 → 2035년 30.9억달러(CAGR 14.2%)", [
  ("NVDA ★","아이작 심 / 아이작 랩","가상 표준",B1,"공장 도면·영상을 그대로 복제해 무한 훈련 — 가상 데이터 주도권 선점"),
  ("GOOGL ★","MuJoCo (딥마인드)",None,None,"정밀 물리엔진 — 미세한 손가락 감각을 가상에서 단련"),
  ("META","하비타트 (Habitat)",None,None,"가정환경 복제 — 서비스 로봇용 가상 데이터베이스 축적"),
  ("TSLA ★","기가팩토리 디지털트윈",None,None,"자체 공장을 가상 복제해 옵티머스를 밀폐 훈련 — 데이터 자급"),
  ("SNPS","시놉시스 (앤시스 통합)",None,None,"설계·검증 물리 시뮬레이션 — 로봇 하드웨어의 디지털트윈"),
  ("U","유니티 (Unity)",None,None,"로봇 학습용 3D 엔진 — 합성 데이터 생성 저변"),
  ("모션 토큰 이코노미(한국)","",None,B3,"장인 동작을 토큰화해 거래·저작권료 — 공장 보유국 한국의 역전 카드(에이로봇 제안·정부 검토)"),
 ]),
]

ARROWS = [
 "부품 발주 — 완성체의 양산 계획이 아래 모든 단(段)의 매출을 결정한다",
 "두뇌가 판단 → 관절·근육에 0.1초 안에 명령 (VLA 모델)",
 "센서가 읽은 물리 세계 → 두뇌로 (밀리초 단위 센서 퓨전)",
 "명령을 실제 힘으로 — 원가의 40%가 여기서 나간다",
 "가볍고 오래 가는 몸 — 소재·배터리가 작동 시간을 정한다",
]
CYCLE = ("⟳ 현장 데이터(모션 토큰) → 가상훈련장에서 수십만 시간 증폭 → 모델 성능 ↑ → 로봇 판매 ↑ → "
         "다시 데이터 ↑  ·  한 대가 배우면 전 대수가 진화하는 선순환")

CSS = """
@page { size: 840px 3000px; margin: 0; }
body { font-family:'Noto Sans CJK KR','Noto Sans KR',sans-serif; margin:0; padding:10px;
       background:#ffffff; color:#0f172a; width:820px; box-sizing:border-box; }
.leg { font-size:12px; color:#475569; margin:0 0 10px; }
.leg .b1,.leg .b2,.leg .b3 { float:none; }
.sec { border:1px solid #dbe2ea; border-radius:12px; padding:12px 14px; background:#f8fafc; }
.sh  { margin:0 0 9px; }
.sh .t { font-size:15.5px; color:#0f172a; letter-spacing:-0.2px; font-weight:700; }
.sh .s { font-size:11.5px; color:#94a3b8; display:block; margin-top:3px; }
.cards { display:flex; flex-wrap:wrap; margin:-3px; }
.card { box-sizing:border-box; width:246px; margin:3px; border:1px solid #dbe2ea;
        border-radius:8px; background:#ffffff; padding:7px 9px 8px; }
.tk { font-size:13px; color:#0f172a; font-weight:700; }
.nm { font-size:11.5px; color:#64748b; margin-left:4px; }
.mo { font-size:11px; color:#475569; margin-top:3px; line-height:1.5; }
.b1,.b2,.b3 { float:right; font-size:10.5px; padding:1px 7px; border-radius:8px; margin-left:4px; }
.b1 { background:#dbeafe; color:#1d4ed8; }
.b2 { background:#fef3c7; color:#b45309; }
.b3 { background:#e2e8f0; color:#475569; }
.arr { text-align:center; color:#475569; font-size:12.5px; padding:9px 0; }
.cyc { text-align:center; color:#1d4ed8; font-size:12.5px; padding:10px 0 2px; line-height:1.6; }
"""

def card(tk, nm, bt, bk, mo):
    b = f'<span class="{bk}">{bt or "비상장"}</span>' if bk else ""
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
          '&nbsp;&nbsp;&nbsp;<span class="b2">과점·양강·선두</span> 소수가 시장 분할'
          '&nbsp;&nbsp;&nbsp;<span class="b3">비상장</span> 직접 투자 불가 — 구조 이해용'
          '&nbsp;&nbsp;&nbsp;★ 상위 단(段)과 중복 표기</div>')

PARTS = [
    LEGEND + section(0) + arrow(0) + section(1) + arrow(1),
    section(2) + arrow(2) + section(3) + arrow(3),
    section(4) + arrow(4) + section(5) + f'<div class="cyc">{CYCLE}</div>',
]

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
            if any(px[x, y] != (255, 255, 255) for x in range(0, w, 8)):
                bottom = y
                break
        im.crop((0, 0, w, min(h, bottom + 24))).save(out_png, optimize=True)
        print(out_png, im.size[0], "x", min(h, bottom + 24))

def main():
    with open(os.path.join(HERE, "appf_physical_ai.html"), "w", encoding="utf-8") as f:
        f.write(html_doc(FULL))
    for i, body in enumerate(PARTS, 1):
        render(body, os.path.join(HERE, f"appf_physical_ai_{i}.png"))
    print("done")

if __name__ == "__main__":
    main()
