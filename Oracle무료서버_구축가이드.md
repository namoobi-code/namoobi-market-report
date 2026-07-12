# namoobi 시황 DB + 공개 대시보드 구축 가이드
### Oracle Cloud "Always Free" 무료 서버 기준 · 리눅스 초보용
*작성일: 2026-07-11 / 2026년 7월 최신 정책 반영*

---

## 0. 전체 그림 먼저

지금 만들려는 것은 이 흐름입니다.

```
[namoobi 시황 리포트 워크플로우]
   ↓ (매일 자동 실행 → nmr_*.json 20여 개 생성)
[JSON 데이터]
   ↓ (적재 스크립트)
[PostgreSQL DB]  ← 서버 안에 설치
   ↓ (조회 API)
[FastAPI 백엔드]
   ↓
[웹 대시보드]  → https://내도메인.com  (누구나 접속)
```

이 전부가 **Oracle이 평생 무료로 빌려주는 리눅스 서버 한 대** 안에서 돌아갑니다.

**작업 순서 (Phase 1~4가 서버 구축, 5~8이 사이트 구축)**

| Phase | 내용 | 예상 소요 |
|---|---|---|
| 1 | Oracle Cloud 가입 | 20분 |
| 2 | 무료 서버(VM) 만들기 | 20분 ~ (운 나쁘면 며칠) |
| 3 | 윈도우에서 서버 접속(SSH) | 15분 |
| 4 | 방화벽 열기 ⚠️ **최대 함정** | 15분 |
| 5 | 기본 세팅 + PostgreSQL 설치 | 30분 |
| 6 | DB 설계 + namoobi 데이터 적재 | 1~2시간 |
| 7 | 백엔드 + 대시보드 | 반나절~ |
| 8 | 도메인 + HTTPS 공개 | 30분 |

> **초보자에게 드리는 말**: Phase 1~4까지만 끝내면 사실상 산은 다 넘은 겁니다. 거기서 막히는 사람이 90%예요. 그 구간의 함정을 아래에 전부 표시해뒀습니다.

---

## Phase 1 — Oracle Cloud 가입

### 준비물
- 이메일
- **신용/체크카드** (본인확인용. Always Free만 쓰면 **요금 청구 안 됨.** 가입 시 1달러 정도가 임시 승인됐다가 자동 취소됩니다)
- 휴대폰

### 절차
1. https://www.oracle.com/kr/cloud/free/ 접속 → "무료로 시작하기"
2. 국가: **대한민국**, 이메일 인증
3. 카드 정보 입력 (본인확인용)

### ⚠️ 함정 1 — 홈 리전(Home Region)은 **나중에 못 바꿉니다**

가입 중 "홈 리전" 을 딱 한 번 고르는데, **이건 영구히 고정**입니다. 신중하게.

| 선택지 | 장점 | 단점 |
|---|---|---|
| **South Korea Central (Seoul)** ✅ 추천 | 한국에서 접속 속도 가장 빠름 | 무료 ARM 서버 물량이 자주 동남 |
| **South Korea North (Chuncheon)** | 한국, 서울보다 물량 여유 있는 편 | — |
| Japan East (Tokyo) | 물량 여유, 한국서 속도도 무난 | 서울보단 약간 느림 |

**추천: 서울(Seoul).** 물량이 없으면 아래 Phase 2의 우회법으로 해결할 수 있습니다.

### ⚠️ 함정 2 — 가입 후 "업그레이드" 유혹
가입하면 30일 300달러 무료 크레딧을 주는데, 이건 **유료 체험**이라 30일 지나면 자동으로 Always Free로 내려옵니다. **카드 결제로 넘어가지 않으니 안심**하되, Always Free 대상이 아닌 서비스는 켜지 마세요. (콘솔에서 리소스마다 **"Always Free 적격"** 라벨이 붙어 있습니다. 이 라벨 없는 건 만들지 않기.)

---

## Phase 2 — 무료 서버(VM) 만들기

### 무료로 주는 사양 (2026년 7월 기준)

> ⚠️ **2026년 6월 15일부로 Oracle이 무료 ARM 사양을 절반으로 줄였습니다.** (4코어·24GB → **2코어·12GB**)
> 그래도 개인 시황 대시보드에는 **차고 넘칩니다.** (참고: 일반적인 유료 VPS 5천원짜리가 2코어·4GB입니다)

| 항목 | 무료 제공량 |
|---|---|
| **ARM 서버 (Ampere A1)** | **2 OCPU · 12 GB RAM** ← 이걸 씁니다 |
| AMD 마이크로 서버 | 1/8 OCPU · 1 GB RAM × 2대 (예비용) |
| 디스크 | 총 200 GB |
| 트래픽(외부 전송) | 월 10 TB |
| 비용 | **0원 · 기간 제한 없음** |

### 절차
1. 콘솔 로그인 → 메뉴 → **Compute → Instances → Create instance**
2. **Image**: `Canonical Ubuntu` 선택 → 버전은 **24.04 LTS** 또는 **26.04 LTS** (둘 다 무난. 목록에 있는 최신 LTS)
3. **Shape (사양)**: `Change shape` →
   - **Ampere** 탭 → `VM.Standard.A1.Flex`
   - **OCPU: 2**, **Memory: 12 GB** 로 설정
4. **Networking**: 기본값 그대로 (VCN 자동 생성), **"Assign a public IPv4 address" 반드시 체크**
5. **SSH keys**: `Generate a key pair for me` 선택 → **⚠️ Private key(개인키) 반드시 다운로드!**
   - 이 파일을 잃어버리면 서버에 영영 못 들어갑니다. (예: `ssh-key-2026-07-11.key`)
   - 윈도우에서 `C:\Users\namoo\.ssh\` 폴더를 만들고 그 안에 보관하세요.
6. **Create** 클릭

### ⚠️ 함정 3 — "Out of host capacity" (초보자 최대의 좌절 지점)

무료 ARM 서버는 전 세계에서 인기가 폭발해서, **"Out of host capacity"(물량 없음)** 오류가 자주 뜹니다. 당신 잘못이 아닙니다. 해결법을 난이도 순으로:

**① 그냥 재시도 (가장 쉬움)**
몇 분~몇 시간 간격으로 `Create` 버튼을 다시 누릅니다. 다른 사용자가 서버를 반납하면 자리가 납니다. 새벽 시간대가 잘 됩니다.

**② Availability Domain / Fault Domain 바꿔보기**
생성 화면에서 AD-1, AD-2, AD-3을 번갈아 시도.

**③ AMD 마이크로 서버로 먼저 시작 (현실적인 우회) ⭐**
`VM.Standard.E2.1.Micro` (1GB RAM)는 **거의 항상 물량이 있습니다.** 사양은 약하지만 —
- PostgreSQL + FastAPI + 가벼운 대시보드 → **1GB로도 충분히 돌아갑니다**
- 일단 이걸로 사이트를 완성해두고, 나중에 ARM 물량이 나면 옮기면 됩니다.
- **초보자에게는 오히려 이 길을 권합니다.** 몇 날 며칠 Create 버튼만 누르다 지치는 것보다 낫습니다.

**④ Pay As You Go로 계정 업그레이드 (가장 확실)**
계정을 유료형으로 전환하면 물량 우선권이 생깁니다. **중요: 전환해도 Always Free 리소스는 계속 무료**입니다. 다만 실수로 무료 범위를 넘기면 과금될 수 있으니, 초보 단계에선 권하지 않습니다.

> 💡 **정리**: ARM이 안 잡히면 **③번(AMD 마이크로)으로 시작하세요.** 사이트 만드는 법을 배우는 게 먼저고, 서버 사양은 나중에 언제든 키울 수 있습니다.

### 마지막으로 할 것
서버가 생성되면 **Public IP 주소**(예: `123.45.67.89`)를 메모해 두세요. 앞으로 계속 씁니다.

---

## Phase 3 — 윈도우에서 서버 접속하기 (SSH)

윈도우 10/11에는 SSH가 이미 내장돼 있습니다. 별도 프로그램 설치 불필요.

### 1) 개인키 권한 고치기 (⚠️ 안 하면 접속 거부됨)
`PowerShell`을 열고 (시작 → "PowerShell" 검색):

```powershell
cd $env:USERPROFILE\.ssh
icacls ssh-key-2026-07-11.key /inheritance:r
icacls ssh-key-2026-07-11.key /grant:r "$($env:USERNAME):(R)"
```
> 윈도우 SSH는 개인키 파일이 "아무나 읽을 수 있는 상태"면 접속을 거부합니다. 위 명령이 그걸 고쳐줍니다.

### 2) 접속
```powershell
ssh -i $env:USERPROFILE\.ssh\ssh-key-2026-07-11.key ubuntu@123.45.67.89
```
- `123.45.67.89` → 아까 메모한 Public IP
- 사용자명은 Ubuntu 이미지면 **`ubuntu`** 입니다 (root 아님)
- 처음 접속 시 `Are you sure you want to continue connecting?` → **yes** 입력

접속에 성공하면 프롬프트가 이렇게 바뀝니다:
```
ubuntu@myserver:~$
```
**축하합니다. 이제 당신은 리눅스 서버 안에 들어와 있습니다.** 여기서 치는 명령어는 전부 서버에서 실행됩니다.

---

## Phase 4 — 방화벽 열기 ⚠️ **가장 많이 막히는 곳**

Oracle 서버는 방화벽이 **두 겹**입니다. **둘 다** 열어야 외부에서 웹사이트가 보입니다.
초보자 대부분이 첫 번째만 열고 "왜 사이트가 안 뜨지?" 하며 몇 시간을 헤맵니다.

### 겹 1 — Oracle 콘솔의 보안 목록 (Security List)
1. 콘솔 → **Networking → Virtual Cloud Networks** → 내 VCN 클릭
2. **Security Lists** → `Default Security List` 클릭
3. **Add Ingress Rules** → 아래 2개 추가:

| Source CIDR | IP Protocol | Destination Port | 용도 |
|---|---|---|---|
| `0.0.0.0/0` | TCP | `80` | HTTP |
| `0.0.0.0/0` | TCP | `443` | HTTPS |

### 겹 2 — 서버 안의 iptables ⚠️ **이걸 놓칩니다**
Oracle의 Ubuntu 이미지는 **서버 내부에도 방화벽이 켜져 있습니다.** SSH로 접속한 상태에서:

```bash
sudo iptables -I INPUT 1 -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 1 -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```
> 마지막 `netfilter-persistent save` 를 빼먹으면 **서버 재부팅 시 방화벽이 다시 닫힙니다.** 꼭 실행하세요.

#### 🔥 왜 `-I INPUT 1` 인가 (실전에서 겪은 함정)

인터넷의 많은 가이드가 `-I INPUT 6` (6번 자리에 삽입)을 쓰라고 합니다. **하지만 이건 서버마다 다릅니다.**

iptables는 **위에서부터 순서대로** 읽다가 매칭되면 **거기서 멈춥니다.** 체인 중간에 있는 `REJECT` 규칙보다 **뒤에** ACCEPT를 넣으면, 그 규칙은 **영원히 읽히지 않는 죽은 규칙**이 됩니다.

실제로 이 서버(Ubuntu 24.04 / E2.1.Micro)는 **REJECT가 5번**에 있었습니다:
```
4    ACCEPT   tcp dpt:22        ← SSH는 여기서 허용 (그래서 SSH만 됨)
5    REJECT   icmp-host-prohibited   ← 여기서 전부 차단하고 끝
6    ACCEPT   tcp dpt:443       ← 죽은 규칙 (도달 불가)
7    ACCEPT   tcp dpt:80        ← 죽은 규칙 (도달 불가)
```
→ **증상: SSH는 되는데 웹사이트만 `ERR_CONNECTION_TIMED_OUT`**

**`-I INPUT 1` 을 쓰면 맨 첫 줄에 꽂히므로 REJECT 위치와 무관하게 항상 동작합니다.**

확인 명령:
```bash
sudo iptables -L INPUT -n --line-numbers
```
80/443 ACCEPT가 **REJECT보다 위에** 있으면 정상입니다.

### 확인 테스트
```bash
sudo apt update && sudo apt install -y nginx
```
설치 후 브라우저에서 `http://123.45.67.89` 접속 → **"Welcome to nginx!"** 페이지가 뜨면 **방화벽 통과 성공**입니다. 🎉

여기까지 왔으면 가장 어려운 고비를 넘었습니다.

---

## Phase 5 — 기본 세팅 + PostgreSQL 설치

### 시스템 업데이트 & 한국 시간대
```bash
sudo apt update && sudo apt upgrade -y
sudo timedatectl set-timezone Asia/Seoul
```

### 필수 소프트웨어
```bash
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib git
```

### PostgreSQL 초기 설정
```bash
sudo -u postgres psql
```
psql 프롬프트(`postgres=#`)가 뜨면:
```sql
CREATE DATABASE namoobi;
CREATE USER nmr WITH PASSWORD '여기에_강력한_비밀번호';
GRANT ALL PRIVILEGES ON DATABASE namoobi TO nmr;
\c namoobi
GRANT ALL ON SCHEMA public TO nmr;
\q
```

### (권장) 자동 보안 업데이트
```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

---

## Phase 6 — DB 설계 + namoobi 데이터 적재

### 지금 데이터가 어떻게 생겼나

namoobi 워크플로우는 매일 도메인별 JSON을 20여 개 만들어냅니다:

```
nmr_macro.json          거시지표          nmr_crypto.json       암호화폐
nmr_policyrates.json    각국 정책금리      nmr_kr_ohlcv.json     코스피 시세
nmr_m7.json             매그니피센트7      nmr_semi_cycle.json   반도체 사이클
nmr_asia_etf.json       아시아 ETF        nmr_amer_etf.json     미국 ETF
nmr_oecd_cli.json       OECD 경기선행      nmr_customs.json      수출입
nmr_deriv_positioning.json  파생 포지셔닝   nmr_factset.json      실적 컨센서스
... 등
```

각 파일은 **"특정 날짜 시점의 스냅샷"** 구조입니다. (`asof`, `generated_at`, `source` 필드를 다 갖고 있음 — 아주 잘 설계돼 있습니다)

### 추천 스키마 — "원본 보존 + 조회용 평탄화" 2단 구조

초보자가 저지르는 실수는 도메인마다 테이블을 20개 만드는 겁니다. 그러면 JSON 구조가 조금만 바뀌어도 다 깨집니다. **아래 3개 테이블이면 충분합니다.**

```sql
-- 1) 매일의 리포트 실행 기록
CREATE TABLE report_runs (
    id           SERIAL PRIMARY KEY,
    report_date  DATE NOT NULL UNIQUE,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2) 원본 JSON 통째로 보존 (스키마가 바뀌어도 절대 안 깨짐)
CREATE TABLE raw_payloads (
    id       SERIAL PRIMARY KEY,
    run_id   INT REFERENCES report_runs(id) ON DELETE CASCADE,
    domain   TEXT NOT NULL,          -- 'crypto', 'macro', 'policyrates' ...
    payload  JSONB NOT NULL,         -- JSON 원본 그대로
    UNIQUE (run_id, domain)
);

-- 3) 차트·조회용으로 숫자만 뽑아 평탄화
CREATE TABLE metrics (
    id          SERIAL PRIMARY KEY,
    run_id      INT REFERENCES report_runs(id) ON DELETE CASCADE,
    domain      TEXT NOT NULL,       -- 'crypto'
    metric_key  TEXT NOT NULL,       -- 'kimchi_premium_pct'
    symbol      TEXT,                -- 'BTC'
    value       NUMERIC,             -- -1.2341
    unit        TEXT,                -- '%'
    asof        DATE,
    source      TEXT
);
CREATE INDEX idx_metrics_lookup ON metrics(domain, metric_key, symbol, asof);
```

**이 설계가 좋은 이유**
- `raw_payloads` 덕분에 **JSON 구조가 바뀌어도 데이터를 절대 잃지 않습니다.** 나중에 언제든 다시 뽑아낼 수 있어요.
- `metrics`는 차트 그리기 좋게 평탄화된 형태 — "BTC 김치프리미엄 최근 90일" 같은 조회가 한 줄 SQL로 끝납니다.
- PostgreSQL의 `JSONB`는 JSON 안을 SQL로 직접 검색할 수도 있습니다.

### 적재 스크립트 예시 (`load_json.py`)

```python
import json, glob, os, psycopg2
from datetime import date

conn = psycopg2.connect(
    dbname="namoobi", user="nmr",
    password=os.environ["NMR_DB_PW"], host="localhost"
)
cur = conn.cursor()

report_date = date.today()
cur.execute(
    "INSERT INTO report_runs (report_date) VALUES (%s) "
    "ON CONFLICT (report_date) DO UPDATE SET generated_at = now() "
    "RETURNING id;", (report_date,)
)
run_id = cur.fetchone()[0]

for path in glob.glob("nmr_build/nmr_*.json"):
    domain = os.path.basename(path).replace("nmr_", "").replace(".json", "")
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)

    # 1) 원본 보존
    cur.execute(
        "INSERT INTO raw_payloads (run_id, domain, payload) VALUES (%s, %s, %s) "
        "ON CONFLICT (run_id, domain) DO UPDATE SET payload = EXCLUDED.payload;",
        (run_id, domain, json.dumps(payload, ensure_ascii=False))
    )

    # 2) 예시: 암호화폐 김치프리미엄 평탄화
    if domain == "crypto":
        for coin in payload.get("kimchi_premium", {}).get("coins", []):
            cur.execute(
                "INSERT INTO metrics (run_id, domain, metric_key, symbol, value, unit, asof) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s);",
                (run_id, "crypto", "kimchi_premium_pct", coin["symbol"],
                 coin["premium_pct"], "%", payload.get("asof"))
            )

conn.commit()
print(f"✅ 적재 완료: run_id={run_id}")
```
> 도메인별 평탄화 규칙은 하나씩 늘려가면 됩니다. **`raw_payloads`에 원본이 남아 있으니 서두를 필요 없습니다.**

---

## Phase 7 — 백엔드 + 대시보드

### FastAPI 백엔드 (`app.py`)
```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import psycopg2.extras, psycopg2, os

app = FastAPI(title="namoobi market API")

def db():
    return psycopg2.connect(dbname="namoobi", user="nmr",
                            password=os.environ["NMR_DB_PW"], host="localhost")

@app.get("/api/metrics")
def metrics(domain: str, metric_key: str, symbol: str | None = None, days: int = 90):
    sql = """SELECT asof, symbol, value FROM metrics
             WHERE domain=%s AND metric_key=%s
               AND (%s IS NULL OR symbol=%s)
               AND asof >= current_date - %s
             ORDER BY asof;"""
    with db() as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (domain, metric_key, symbol, symbol, days))
        return cur.fetchall()

@app.get("/api/latest/{domain}")
def latest(domain: str):
    sql = """SELECT payload FROM raw_payloads rp
             JOIN report_runs r ON r.id = rp.run_id
             WHERE rp.domain=%s ORDER BY r.report_date DESC LIMIT 1;"""
    with db() as c, c.cursor() as cur:
        cur.execute(sql, (domain,))
        row = cur.fetchone()
        return row[0] if row else {}

app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

실행:
```bash
python3 -m venv venv && source venv/bin/activate
pip install fastapi uvicorn psycopg2-binary
uvicorn app:app --host 127.0.0.1 --port 8000
```

### 프론트엔드
`static/index.html` 하나에 **Chart.js**(CDN)로 차트를 그리면 충분합니다. `/api/metrics` 를 호출해서 선 그래프를 그리는 정도로 시작하세요.

### nginx로 연결 (외부 공개)
`/etc/nginx/sites-available/default` 를 편집:
```nginx
server {
    listen 80;
    server_name 내도메인.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## Phase 8 — 도메인 + HTTPS (공개 마무리)

### 도메인 사기
가비아·후이즈 등에서 연 1~2만 원. (`.com`, `.kr` 등)
구입 후 **DNS 설정 → A 레코드 → 서버의 Public IP** 를 가리키게 합니다.

### HTTPS 무료 인증서 (Let's Encrypt)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d 내도메인.com -d www.내도메인.com
```
- 자동으로 인증서 발급 + nginx 설정 + **90일마다 자동 갱신**까지 해줍니다.
- 끝나면 `https://내도메인.com` 으로 **자물쇠 표시와 함께** 접속됩니다. 🎉

---

## Phase 9 — 자동화 (24시간 무인 운영)

### 백엔드를 서비스로 등록 (재부팅해도 자동 실행)
`/etc/systemd/system/namoobi.service`:
```ini
[Unit]
Description=namoobi market API
After=network.target postgresql.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/namoobi
Environment="NMR_DB_PW=여기에_비밀번호"
ExecStart=/home/ubuntu/namoobi/venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now namoobi
sudo systemctl status namoobi     # 잘 도는지 확인
```

### 매일 데이터 자동 적재 (cron)
```bash
crontab -e
```
```
# 매일 오전 7시 30분에 JSON 적재
30 7 * * * cd /home/ubuntu/namoobi && /home/ubuntu/namoobi/venv/bin/python load_json.py >> /home/ubuntu/namoobi/load.log 2>&1
```

### DB 백업 (꼭 하세요)
```bash
# 매일 새벽 3시 백업, 14일치 보관
0 3 * * * pg_dump -U nmr namoobi | gzip > /home/ubuntu/backup/namoobi_$(date +\%F).sql.gz && find /home/ubuntu/backup -mtime +14 -delete
```

---

## 부록 A — 초보자가 자주 막히는 곳 체크리스트

| 증상 | 원인 | 해결 |
|---|---|---|
| 서버 생성 시 "Out of host capacity" | ARM 물량 부족 | 재시도 / AD 변경 / **AMD 마이크로로 우회** |
| SSH 접속 시 "Permissions are too open" | 윈도우 키 파일 권한 | Phase 3의 `icacls` 명령 실행 |
| SSH는 되는데 웹사이트가 `ERR_CONNECTION_TIMED_OUT` | **iptables ACCEPT가 REJECT보다 뒤에 있음** | `-I INPUT 6` 말고 **`-I INPUT 1`** 로 재삽입 (⭐실제로 겪은 함정) |
| SSH는 되는데 웹사이트가 안 뜸 | iptables를 아예 안 열었음 | Phase 4의 **겹 2** 실행 |
| 재부팅하니 사이트가 다시 안 됨 | `netfilter-persistent save` 누락 | Phase 4 마지막 줄 재실행 |
| certbot 인증서 발급 실패 | 도메인 A레코드 전파 전 | DNS 반영까지 10분~1시간 기다린 후 재시도 |
| PostgreSQL 접속 거부 | 비밀번호/권한 | Phase 5의 `GRANT ALL ON SCHEMA public` 확인 |

## 부록 B — 보안 최소 수칙 (공개 사이트니까 중요)

1. **DB 비밀번호를 코드에 직접 쓰지 말 것** → 환경변수(`NMR_DB_PW`)로 관리
2. PostgreSQL은 **외부에 포트를 열지 마세요** (`localhost`만 허용 = 기본값 유지)
3. SSH는 **키 인증만** 사용 (비밀번호 로그인 비활성화 — Oracle 기본값이 이미 그렇습니다)
4. namoobi 폴더의 **SECURITY 폴더(수신자 목록 등)는 절대 웹에 올리지 마세요** — `static/` 밖에 두기
5. `sudo apt upgrade`를 가끔 실행 (보안 패치)

---

## 다음 단계 추천

**오늘 할 일은 Phase 1~4 딱 여기까지입니다.**
`http://내서버IP` 에서 nginx 기본 페이지가 뜨는 것만 확인하면 오늘은 성공입니다.

거기까지 되면 알려주세요. Phase 5부터는 실제 코드를 짜야 하니, 제가 적재 스크립트와 대시보드를 실제 파일로 만들어 드리겠습니다.

---

### 참고 출처
- [Oracle Cloud Free Tier 공식](https://www.oracle.com/cloud/free/)
- [OCI Free Tier 문서](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm)
- [Oracle, 무료 ARM 사양 절반 축소 (2026-06-15, InfoQ)](https://www.infoq.com/news/2026/07/oracle-cloud-free-tier-limits/)
- [Out of host capacity 우회 스크립트](https://github.com/hitrov/oci-arm-host-capacity)
- [Ubuntu 26.04 LTS 릴리스 노트](https://documentation.ubuntu.com/release-notes/26.04/)
