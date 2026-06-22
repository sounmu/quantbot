# Quantbot

미국 상장 투명 액티브 ETF의 발행사 공식 보유종목 CSV를 매일 수집하고, 스냅샷 간 보유 주식수 변화를 계산해 “오늘 무엇을 샀고 팔았는지”를 보여주는 풀스택 웹 애플리케이션입니다.

핵심 판정 기준은 `shares` 변화입니다. 비중(`weight`)은 가격 변동만으로도 흔들릴 수 있어, 실제 매매 추정은 주식수 변화로 분류하고 비중 변화는 보조 컨텍스트로 함께 표시합니다.

## 현재 구현 범위

- DDD + 헥사고날 계층 구조
- SQLAlchemy async 기반 SQLite/PostgreSQL 교체 가능 DB 어댑터
- ETF, 가격, holdings, holdings change, 메트릭, 수집 로그 ORM 모델과 Alembic 마이그레이션
- ARK 공식 일별 CSV 어댑터: ARKK, ARKG, ARKW, ARKF, ARKX
- holdings 스냅샷 수집, 직전 스냅샷 diff 계산, 변동 저장
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
docker compose --profile postgres up --build
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

MVP는 ARK 공식 CSV를 사용합니다.

- ARKK: `https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv`
- ARKG: `https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_GENOMIC_REVOLUTION_ETF_ARKG_HOLDINGS.csv`
- ARKW: `https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_NEXT_GENERATION_INTERNET_ETF_ARKW_HOLDINGS.csv`
- ARKF: `https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_FINTECH_INNOVATION_ETF_ARKF_HOLDINGS.csv`
- ARKX: `https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_SPACE_EXPLORATION_&_INNOVATION_ETF_ARKX_HOLDINGS.csv`

다른 발행사는 `backend/app/infrastructure/external/holdings/`에 provider를 추가하고 registry에 등록하면 됩니다. 준투명 ETF처럼 일별 holdings를 공개하지 않는 상품은 `discloses_daily=false`로 두면 diff 수집에서 제외됩니다.

## 배포 메모

- 프론트는 Vercel에서 `frontend/`를 프로젝트 루트로 지정합니다.
- Vercel 환경변수 `NEXT_PUBLIC_API_BASE_URL=https://api.<domain>`을 설정합니다.
- 백엔드는 Oracle Cloud Always Free ARM VM에서 Docker로 실행할 수 있게 구성했습니다.
- 운영 백엔드는 Caddy 같은 리버스 프록시로 HTTPS를 붙이고, `CORS_ORIGINS`에 Vercel 도메인을 추가합니다.
