# Quantbot

미국 상장 투명 액티브 ETF의 발행사 공식 보유종목 CSV/XLSX/JSON을 매일 수집하고, 스냅샷 간 보유 주식수 변화를 계산해 “오늘 무엇을 샀고 팔았는지”를 보여주는 풀스택 웹 애플리케이션입니다.

핵심 판정 기준은 `shares` 변화입니다. 비중(`weight`)은 가격 변동만으로도 흔들릴 수 있어, 실제 매매 추정은 주식수 변화로 분류하고 비중 변화는 보조 컨텍스트로 함께 표시합니다.

## 현재 구현 범위

- DDD + 헥사고날 계층 구조
- SQLAlchemy async 기반 SQLite/PostgreSQL 교체 가능 DB 어댑터
- ETF, 가격, holdings, holdings change, 메트릭, 수집 로그 ORM 모델과 Alembic 마이그레이션
- ARK 공식 일별 CSV 어댑터: ARKK, ARKG, ARKW, ARKF, ARKX
- BlackRock/iShares product-data JSON 어댑터: DYNF
- State Street/SPDR 일별 XLSX 어댑터: TOTL
- Capital Group 공식 일별 XLSX 어댑터: CGGR, CGDV
- T. Rowe Price 상품 페이지 embedded JSON 어댑터: TCAF
- holdings 스냅샷 수집, 직전 스냅샷 diff 계산, 변동 저장
- APScheduler 기반 일일 자동 수집과 admin 수동 수집 API
- ETF별 holdings 날짜, 스냅샷, 변동, 종목 이력, 전체 최근 매매 피드 API
- Next.js App Router 프론트: ETF 목록, 상세 holdings diff, 종목 이력 차트, 전체 최근 매매 피드, 가격 컨텍스트, 비교 화면

## 아키텍처 규칙

의존성은 항상 안쪽으로 향합니다.

```text
interfaces / infrastructure -> application -> domain
```

- `backend/app/domain`: 순수 도메인 엔티티와 리포지토리 포트. FastAPI, SQLAlchemy, httpx 등을 import하지 않습니다.
- `backend/app/application`: 유스케이스, 수집 오케스트레이션, holdings diff 엔진. 포트에만 의존합니다.
- `backend/app/infrastructure`: DB, 발행사 CSV, yfinance, 스케줄러 등 실제 기술 어댑터입니다.
- `backend/app/interfaces`: FastAPI 라우터, DTO, DI 조립부입니다.

SQLite에서 PostgreSQL로 옮길 때는 `DATABASE_URL`과 필요한 드라이버/운영 설정만 바꾸는 방향을 유지합니다.

## 로컬 실행

### 1. 환경변수

```bash
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local
```

### 2. 백엔드

`uv`가 없으면 macOS 기준 `brew install uv`로 설치한 뒤 진행합니다.

```bash
cd backend
uv sync --extra dev
uv run alembic upgrade head
uv run python -m app.application.pipeline.collect
uv run uvicorn app.main:app --reload
```

`SEED_UNIVERSE_ON_STARTUP=true`가 기본값이라 API 서버를 띄우면 ETF 기본 목록은 자동으로 upsert됩니다. holdings 스냅샷과 변동 데이터까지 채우려면 위의 `collect` 명령이나 admin 수동 수집 API를 실행합니다.

확인:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/etfs/ARKK/holdings/dates
curl http://localhost:8000/api/changes/recent
```

가격 데이터까지 함께 수집하려면:

```bash
uv run python -m app.application.pipeline.collect --with-prices --lookback-days 365
```

첫 수집에는 이전 스냅샷이 없으므로 대부분 `NEW`로 표시됩니다. 두 번째 영업일 스냅샷부터 `INCREASE`, `DECREASE`, `EXIT` 변동이 의미 있게 쌓입니다.

스케줄러를 로컬에서 켜려면 `.env`에 다음을 설정합니다.

```bash
SCHEDULER_ENABLED=true
COLLECT_CRON_HOUR=22
COLLECT_CRON_MINUTE=0
```

수동 수집과 수집 로그 확인:

```bash
curl -X POST "http://localhost:8000/api/admin/collect" -H "x-admin-token: $ADMIN_TOKEN"
curl -X POST "http://localhost:8000/api/admin/collect?with_prices=true&lookback_days=365" -H "x-admin-token: $ADMIN_TOKEN"
curl "http://localhost:8000/api/admin/runs" -H "x-admin-token: $ADMIN_TOKEN"
```

### 3. 프론트

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:3000`을 열면 `/etfs`로 이동합니다.

### 4. Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

PostgreSQL 컨테이너를 함께 띄우려면:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml --profile postgres up --build
```

## 주요 API

- `GET /health`
- `GET /api/etfs`
- `GET /api/etfs/{ticker}`
- `GET /api/etfs/{ticker}/holdings?date=YYYY-MM-DD`
- `GET /api/etfs/{ticker}/holdings/dates`
- `GET /api/etfs/{ticker}/changes?date=YYYY-MM-DD`
- `GET /api/etfs/{ticker}/positions/{holding}/history`
- `GET /api/changes/recent?types=NEW&types=INCREASE&limit=100`
- `GET /api/etfs/{ticker}/prices?range=1m|3m|6m|1y|ytd|max`
- `GET /api/etfs/compare?tickers=ARKK,ARKW&range=1y`
- `GET /api/meta/issuers`
- `GET /api/meta/themes`
- `POST /api/admin/collect` with `x-admin-token`
- `GET /api/admin/runs` with `x-admin-token`

## 데이터 소스

현재 기본 registry에 등록된 공식 holdings 소스입니다.

- ARKK: `https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv`
- ARKG: `https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_GENOMIC_REVOLUTION_ETF_ARKG_HOLDINGS.csv`
- ARKW: `https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_NEXT_GENERATION_INTERNET_ETF_ARKW_HOLDINGS.csv`
- ARKF: `https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_FINTECH_INNOVATION_ETF_ARKF_HOLDINGS.csv`
- ARKX: `https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_SPACE_EXPLORATION_&_INNOVATION_ETF_ARKX_HOLDINGS.csv`
- DYNF: BlackRock product-data `component=holdings` JSON endpoint
- TOTL: `https://www.ssga.com/library-content/products/fund-data/etfs/us/holdings-daily-us-en-totl.xlsx`
- CGGR: `https://www.capitalgroup.com/api/investments/investment-service/v1/etfs/CGGR/download/daily-holdings?audience=advisor`
- CGDV: `https://www.capitalgroup.com/api/investments/investment-service/v1/etfs/CGDV/download/daily-holdings?audience=advisor`
- TCAF: T. Rowe Price Capital Appreciation Equity ETF page embedded `full.holdings` JSON
- AVUV: Avantis U.S. Small Cap Value ETF page embedded `etfHoldings` payload
- AVDV: Avantis International Small Cap Value ETF page embedded `etfHoldings` payload
- PFFA: `https://www.virtus.com/assets/files/1xx/positions_pffa.xls`

다른 발행사는 `backend/app/infrastructure/external/holdings/`에 provider를 추가하고 registry에 등록하면 됩니다. 준투명 ETF처럼 일별 holdings를 공개하지 않는 상품은 `discloses_daily=false`로 두면 diff 수집에서 제외됩니다.

## 배포 메모

- 프론트는 Vercel에서 `frontend/`를 프로젝트 루트로 지정합니다.
- Vercel 환경변수 `NEXT_PUBLIC_API_BASE_URL=https://api.<domain>`을 설정합니다.
- 백엔드는 Oracle Cloud Always Free ARM VM 또는 Docker Compose가 가능한 VM에서 실행하고, 공개 노출은 Cloudflare Tunnel로 처리합니다.
- `.env.production.example`을 `.env`로 복사하고 `ADMIN_TOKEN`, `CORS_ORIGINS`, `CLOUDFLARE_TUNNEL_TOKEN`을 운영값으로 바꿉니다.
- Cloudflare Zero Trust에서 Tunnel을 만들고 public hostname `api.<domain>`의 service URL을 `http://api:8000`으로 설정합니다.
- VM에서 `docker compose -f docker-compose.prod.yml up -d --build`를 실행합니다.
- Cloudflare Tunnel을 쓰면 API 컨테이너는 compose 내부 네트워크로만 공개되며, 호스트의 `127.0.0.1:8000` 포트는 VM 내부 점검용입니다. 일반적인 운영에서는 80/443 인바운드 방화벽을 열 필요가 없습니다.
