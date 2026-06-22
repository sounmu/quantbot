# 액티브 ETF 보유비중 변동 추적기 — 구현 명세서

> 이 문서는 코딩 에이전트(Codex 등)가 단계별로 그대로 구현할 수 있도록 작성된 실행 명세서다.
> 각 단계는 **목표 → 작업 항목 → 산출 파일 → 완료 기준(Acceptance)** 순서로 구성된다.
> 위에서부터 순서대로 구현하면 동작하는 제품이 완성된다.

---

## 0. 프로젝트 개요

미국 상장 **액티브 ETF가 매일 어떤 종목을 사고/팔고/비중을 늘리고 줄이는지**를
발행사 공식 일별 보유종목(holdings) 공시로 수집·축적하고, **스냅샷 간 변화(diff)** 를 계산해
"이 ETF가 오늘/이번 주에 무엇을 매매했는가"와 "특정 종목 비중의 시간 추이"를 보여주는 추적 도구.
(ARK 트래커 스타일을 투명 액티브 ETF 전반으로 확장.)

### 핵심 결정 사항 (확정됨)
- **추적 기준 = 보유 주식수(shares) + 비중(%) 둘 다.**
  비중%는 가격 변동만으로도 변하므로, **실제 매니저 매매는 shares Δ로 판정**하고 비중%는 배분 변화 보조지표로 함께 표시한다.
- **데이터 소스 = 발행사 공식 일별 holdings CSV.** httpx로 직접 다운로드·파싱. ARK 어댑터를 먼저, 이후 발행사별 어댑터를 점진 추가.
- **유니버스 = 투명 액티브 ETF 전반.** 발행사별 CSV 어댑터를 registry로 확장.
- **가격/수익률은 보조 컨텍스트**(yfinance). 핵심은 holdings 변동이다.
- **아키텍처**: **DDD + 헥사고날(포트 & 어댑터)** — 도메인/애플리케이션은 추상 **포트**에만 의존, DB·외부 소스는 교체 가능한 **어댑터**로 격리. → SQLite↔PostgreSQL 전환을 "어댑터 + DATABASE_URL 교체"만으로 처리.
- **배포**: 프론트 = **Vercel**, 백엔드 = **Oracle Cloud Always Free** (ARM VM, Docker)

### 핵심 화면/기능
1. **ETF 상세 — holdings 스냅샷**: 보유종목 표(shares·시장가치·비중) + 행별 **직전 대비 변동 배지**(신규/청산/▲증가/▼감소), 스냅샷 날짜 선택
2. **ETF 변동(트레이드) 피드**: 특정 ETF의 일별 매매 내역(신규·청산·증감)
3. **종목 추세 차트**: 한 종목의 shares·비중 시계열
4. **유니버스 전체 "최근 매매" 피드**: 모든 추적 ETF 횡단 트레이드
5. (보조) 목록·검색·필터, 가격/수익률 차트

### 기술 스택
| 구분 | 기술 | 버전(권장) |
|---|---|---|
| 백엔드 | FastAPI | 0.115+ |
| ORM | SQLAlchemy (async) | 2.0+ |
| 마이그레이션 | Alembic | 1.13+ |
| 스케줄러 | APScheduler | 3.10+ |
| HTTP 클라이언트 | httpx | 0.27+ |
| holdings 수집 | 발행사 공식 CSV (httpx 다운로드 + csv 파싱) | - |
| 가격 수집(보조) | yfinance | 0.2.40+ |
| 검증 | Pydantic | 2.x |
| DB | **SQLite(MVP) → PostgreSQL 이관 가능 구조** | - |
| 프론트 | Next.js (App Router, TypeScript) | 15+ |
| 데이터 패칭 | TanStack Query | 5+ |
| 스타일 | Tailwind CSS + shadcn/ui | - |
| 차트 | Recharts | 2.x |
| 아키텍처 | DDD + 헥사고날(포트 & 어댑터) | 1.5장 |
| 백엔드 배포 | Oracle Cloud Always Free (ARM VM, Docker) | - |
| 프론트 배포 | Vercel | - |

### 기본 설계 원칙
- DB는 SQLite로 시작하되 **SQLAlchemy async + DATABASE_URL**로 추상화해 Postgres 전환 시 코드 변경 최소화.
- 외부 데이터(발행사 CSV/yfinance)는 모두 `infrastructure/external/`에 어댑터로 격리. backoff/에러 로깅 필수.
- **holdings는 매일 스냅샷으로 누적**한다(`as_of_date`가 스냅샷 키). 변동은 스냅샷 diff로 파생한다.
- 프론트는 백엔드 REST만 소비. 화면 UI는 한국어, 데이터는 USD 기준.

---

## 1. 모노레포 디렉토리 구조 (최종 목표)

```
quantbot/
├─ PLAN.md
├─ README.md
├─ docker-compose.yml
├─ .env.example
├─ backend/                          # 헥사고날(포트 & 어댑터) 계층 구조
│  ├─ pyproject.toml
│  ├─ Dockerfile
│  ├─ alembic.ini
│  ├─ alembic/{env.py, versions/}
│  └─ app/
│     ├─ main.py                     # 컴포지션 루트: DI 와이어링, 스케줄러 등록
│     ├─ config.py
│     │
│     ├─ domain/                     # ⬛ 도메인 — 외부 의존 0
│     │  ├─ entities.py              # Etf, PricePoint, Holding(+shares/market_value), HoldingChange
│     │  ├─ value_objects.py         # normalize_ticker, holding_key, ChangeType
│     │  └─ repositories.py          # 포트: EtfRepository, HoldingRepository, HoldingChangeRepository ...
│     │
│     ├─ application/                # ⬛ 애플리케이션 — 포트에만 의존
│     │  ├─ services/
│     │  │  ├─ etf_service.py
│     │  │  ├─ metric_service.py
│     │  │  └─ holding_change_service.py   # 스냅샷 diff 엔진(순수 함수)
│     │  ├─ ports.py                 # MarketDataProvider, HoldingsProvider
│     │  └─ pipeline/collect.py      # 수집+diff 오케스트레이션(포트만 호출)
│     │
│     ├─ infrastructure/             # ⬛ 어댑터 — 실제 기술 구현
│     │  ├─ db/{engine,orm_models,mappers,repositories}.py
│     │  ├─ external/
│     │  │  ├─ base.py               # with_backoff 등 공통
│     │  │  ├─ yfinance_provider.py  # 가격(보조)
│     │  │  ├─ universe.py           # 유니버스 시드 로딩
│     │  │  └─ holdings/             # 발행사별 holdings 어댑터
│     │  │     ├─ base_csv.py        # CSV 다운로드/정규화 공통
│     │  │     ├─ ark_provider.py    # ARK 공식 일별 CSV 파서
│     │  │     └─ registry.py        # issuer/ticker → HoldingsProvider 매핑
│     │  └─ scheduler/jobs.py
│     │
│     ├─ interfaces/                 # ⬛ 진입점 — FastAPI
│     │  ├─ api/{etfs,changes,meta,admin}.py
│     │  ├─ schemas/{etf,price,holding,change,common}.py
│     │  └─ deps.py                  # 포트 → 어댑터 바인딩
│     │
│     └─ seed/active_etfs.json       # 유니버스(티커+발행사+분류+공시방식)
└─ frontend/
   ├─ app/
   │  ├─ etfs/{page.tsx, [ticker]/page.tsx}   # 목록 / 상세(holdings·변동·차트)
   │  ├─ changes/page.tsx                       # 전체 최근 매매 피드
   │  ├─ compare/page.tsx
   │  └─ providers.tsx
   ├─ components/    # EtfTable, HoldingsTable(+변동 배지), ChangeFeed, PositionHistoryChart, PriceChart ...
   ├─ lib/{api.ts, types.ts}
   └─ hooks/         # useEtfs, useEtfDetail, useHoldings, useHoldingChanges, usePositionHistory, useRecentChanges
```

---

## 1.5 아키텍처: DDD + 헥사고날 (포트 & 어댑터)

### 의존성 규칙 (가장 중요)
> **의존성은 항상 안쪽(도메인)으로만 향한다.** 도메인은 그 무엇도 import 하지 않는다.

```
interfaces (FastAPI)        ─┐
infrastructure (DB/외부소스) ─┼──▶  application  ──▶  domain
                             │      (포트 사용)      (포트 정의)
                             └──▶ (포트 구현)
```

- **domain**: 엔티티·값객체·**포트(추상 인터페이스)**. SQLAlchemy·httpx·FastAPI를 절대 import 안 함.
- **application**: 유스케이스/서비스 + **diff 엔진**. 포트에만 의존. 어떤 DB/소스인지 모름.
- **infrastructure**: 포트의 **구현(어댑터)**. SQLAlchemy 리포지토리, 발행사 CSV 파서, yfinance 등 실제 기술 격리.
- **interfaces**: FastAPI 라우터 + DTO. `deps.py`에서 포트에 어댑터 주입.

### SQLite → PostgreSQL 전환
1. 상위 계층은 `EtfRepository`/`HoldingRepository` 등 **포트**만 사용 → DB 종류를 모름.
2. 실제 DB 접근은 `infrastructure/db/repositories.py`에만 존재.
3. `DATABASE_URL` 드라이버만 교체(`sqlite+aiosqlite` → `postgresql+asyncpg`)하면 동일 구현이 양쪽에서 동작.
4. DB별 방언(upsert, JSON, bigint)이 필요하면 **그 차이도 어댑터 내부에만** 둔다.
5. **계약 테스트**를 SQLite/Postgres 양쪽 어댑터에 돌려 동등성 보장.

### 도메인 엔티티 ↔ ORM 분리
- 도메인 엔티티(`domain/entities.py`)와 ORM 모델(`infrastructure/db/orm_models.py`)을 **분리**하고 `mappers.py`로 변환.

### diff 엔진은 순수 함수
- `holding_change_service.diff(...)`는 외부 의존 0인 순수 함수 → DB 없이 픽스처만으로 단위 테스트.
- 서비스 테스트는 **인메모리 가짜 리포지토리**로 DB 없이 검증.

### 포트/어댑터 코드 스켈레톤

> 계층 간 의존 방향과 핵심 도메인 타입을 보여주는 **최소 골격**. 실제 구현 시 필드/메서드를 확장한다.

**① 도메인 엔티티** — `domain/entities.py` (외부 의존 0)
```python
from dataclasses import dataclass
from datetime import date

@dataclass(slots=True)
class Holding:
    ticker: str                 # 모펀드 티커 (예: ARKK)
    as_of_date: date            # 스냅샷 날짜 (= 스냅샷 키)
    holding_name: str
    weight: float               # 비중(%)
    holding_ticker: str | None = None
    shares: float | None = None         # 보유 주식수 (실제 매매 판정 기준)
    market_value: float | None = None   # 시장가치($)

@dataclass(slots=True)
class HoldingChange:
    ticker: str
    as_of_date: date            # 새 스냅샷 날짜
    prev_date: date | None
    holding_name: str
    holding_ticker: str | None
    change_type: str            # NEW | EXIT | INCREASE | DECREASE | UNCHANGED
    shares_before: float | None
    shares_after: float | None
    shares_delta: float | None
    shares_delta_pct: float | None      # 직전 대비 % 증감
    weight_before: float | None
    weight_after: float | None
    weight_delta: float | None
```

**② 값객체/매칭 키** — `domain/value_objects.py`
```python
import re

class ChangeType:
    NEW = "NEW"; EXIT = "EXIT"; INCREASE = "INCREASE"
    DECREASE = "DECREASE"; UNCHANGED = "UNCHANGED"

_CASH_TOKENS = {"CASH", "USD", "DOLLAR", "--", ""}

def holding_key(holding_ticker: str | None, holding_name: str) -> str | None:
    """스냅샷 간 종목 매칭 키: 티커 우선, 없으면 정규화 이름. 현금/노이즈는 None(제외)."""
    if holding_ticker and holding_ticker.strip().upper() not in _CASH_TOKENS:
        return holding_ticker.strip().upper()
    name = re.sub(r"[^A-Z0-9]", "", holding_name.upper())
    if not name or name in _CASH_TOKENS:
        return None
    return f"NAME:{name}"
```

**③ holdings 포트** — `application/ports.py`
```python
from typing import Protocol
from app.domain.entities import Etf, Holding, PricePoint

class HoldingsProvider(Protocol):
    """발행사별 holdings 어댑터가 구현하는 포트."""
    def supports(self, issuer: str) -> bool: ...
    async def fetch_holdings(self, etf: Etf) -> list[Holding]: ...  # 최신 일별 스냅샷(shares 포함)

class MarketDataProvider(Protocol):       # 가격(보조)
    async def fetch_prices(self, ticker: str, *, lookback_days: int) -> list[PricePoint]: ...
```

**④ diff 엔진** — `application/services/holding_change_service.py` (순수 함수)
```python
from datetime import date
from app.domain.entities import Holding, HoldingChange
from app.domain.value_objects import ChangeType, holding_key

class HoldingChangeService:
    def __init__(self, *, shares_epsilon: float = 1.0) -> None:
        self._eps = shares_epsilon   # 반올림 노이즈 무시 임계치

    def diff(self, ticker: str, as_of: date, prev_date: date | None,
             current: list[Holding], previous: list[Holding]) -> list[HoldingChange]:
        cur = {k: h for h in current if (k := holding_key(h.holding_ticker, h.holding_name))}
        prev = {k: h for h in previous if (k := holding_key(h.holding_ticker, h.holding_name))}
        changes: list[HoldingChange] = []
        for key in cur.keys() | prev.keys():
            c, p = cur.get(key), prev.get(key)
            changes.append(self._classify(ticker, as_of, prev_date, c, p))
        return changes
    # _classify: shares_delta(없으면 weight_delta)로 NEW/EXIT/INCREASE/DECREASE/UNCHANGED 판정
```

**⑤ ARK CSV 어댑터** — `infrastructure/external/holdings/ark_provider.py` (포트 구현)
```python
from app.application.ports import HoldingsProvider
from app.domain.entities import Etf, Holding

class ArkHoldingsProvider:                # HoldingsProvider 구현
    _CSV = "https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_{fund}_HOLDINGS.csv"
    def supports(self, issuer: str) -> bool: return issuer.upper() == "ARK"
    async def fetch_holdings(self, etf: Etf) -> list[Holding]:
        ...  # httpx 다운로드 → csv 파싱 → date/ticker/shares/"market value ($)"/"weight (%)" 정규화
```

**⑥ DI 와이어링** — `interfaces/deps.py`
```python
def get_holding_repo(session = Depends(get_session)) -> SqlAlchemyHoldingRepository:
    return SqlAlchemyHoldingRepository(session)   # ← DB 교체 시 이 어댑터만
# HoldingsProvider registry, HoldingChangeService도 동일하게 주입
```

> 포인트: 상위 계층은 **포트 타입만 참조**한다. DB 교체는 ⑤ 어댑터 + `DATABASE_URL`만, 데이터 소스 추가는 새 `HoldingsProvider` 어댑터 + registry 등록만으로 끝난다. 도메인·서비스·diff 엔진은 그대로다.

---

## 2. 데이터 모델 명세

### 2.1 `etf`
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | int PK | |
| ticker | str, unique, index | 예: ARKK |
| name | str | 펀드 정식명 |
| issuer | str, index | 운용사 |
| theme | str, nullable, index | 테마/카테고리 |
| expense_ratio | float, nullable | 보수율(%) |
| inception_date | date, nullable | |
| is_active_etf | bool, default True | |
| discloses_daily | bool, default True | **일별 holdings 공시 여부**(준투명 ETF=False, diff 대상 제외) |
| currency | str, default "USD" | |
| description | text, nullable | |
| created_at / updated_at | datetime | |

### 2.2 `etf_holding` (일별 스냅샷) — **shares/market_value 추가**
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | int PK | |
| etf_id | FK→etf, index | |
| as_of_date | date, index | 스냅샷 날짜 |
| holding_ticker | str, nullable, index | |
| holding_name | str | |
| weight | float | 비중(%) |
| **shares** | float, nullable | **보유 주식수** |
| **market_value** | float, nullable | **시장가치($)** |
| (etf_id, as_of_date, holding_ticker, holding_name) | **unique 제약** | 스냅샷 멱등성 |

### 2.3 `etf_holding_change` (스냅샷 간 파생 변동) — **신규**
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | int PK | |
| etf_id | FK→etf, index | |
| as_of_date | date | 새 스냅샷 날짜 |
| prev_date | date, nullable | 비교 기준(직전) 스냅샷 |
| holding_ticker | str, nullable | |
| holding_name | str | |
| change_type | str | NEW/EXIT/INCREASE/DECREASE/UNCHANGED |
| shares_before / shares_after / shares_delta / shares_delta_pct | float, nullable | |
| weight_before / weight_after / weight_delta | float, nullable | |
| 인덱스 | (etf_id, as_of_date), (etf_id, holding_ticker, as_of_date), (as_of_date) | 일별/종목이력/전체피드 |
| (etf_id, as_of_date, holding_ticker, holding_name) | **unique 제약** | 재계산 멱등성 |

### 2.4 `etf_price` (일별 시계열, 보조)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | int PK | |
| etf_id | FK→etf, index | |
| date | date, index | |
| open/high/low/close | float | |
| nav | float, nullable | |
| volume | bigint, nullable | |
| (etf_id, date) | **unique 제약** | 멱등성 |

### 2.5 `etf_metric` (집계 캐시, 보조)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | int PK | |
| etf_id | FK→etf, unique | 1:1 |
| as_of | date | |
| aum | float, nullable | |
| return_1m / return_3m / return_ytd / return_1y | float, nullable | |

### 2.6 `collection_run` (운영 로그)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | int PK | |
| job_name | str | |
| status | str | running/success/**partial**/failed |
| started_at / finished_at | datetime | |
| items_processed | int | |
| error | text, nullable | 종목/ETF 단위 실패 상세 |

---

## 3. 단계별 구현

> 현재 코드베이스에는 이미 헥사고날 골격 + 가격/목록/상세/비교(가격 기반)가 구현되어 있다.
> 아래 단계는 그 위에 **holdings 스냅샷·변동 추적**을 더하는 작업이다.

### 단계 M1 — 스키마·도메인 확장 (shares/market_value + HoldingChange)

**목표**: 스냅샷에 주식수·시장가치를 담고, 변동 엔티티/테이블을 추가한다.

**작업 항목**
1. `domain/entities.py`: `Holding`에 `shares`, `market_value` 추가. 신규 `HoldingChange` 엔티티(2.3 필드).
2. `domain/value_objects.py`: `ChangeType`, `holding_key()` 추가(현금/노이즈 제외 규칙).
3. `domain/repositories.py`:
   - `HoldingRepository`에 `snapshot(ticker, as_of_date)`, `latest_snapshot_date(ticker)`, `previous_snapshot_date(ticker, before)`, `snapshot_dates(ticker)`, `position_history(ticker, holding_key)` 추가.
   - 신규 포트 `HoldingChangeRepository`: `upsert_many`, `for_snapshot`, `for_position`, `recent(limit, change_types=None)`.
4. `infrastructure/db/orm_models.py`: `EtfHoldingORM`에 `shares`/`market_value` + unique 제약, 신규 `EtfHoldingChangeORM`(인덱스 포함), `EtfORM`에 `discloses_daily`.
5. `infrastructure/db/mappers.py`: `to_holding`(shares/mv 포함), `to_holding_change`/역변환.
6. Alembic 리비전 `0002_holdings_change.py`: etf_holding ALTER + etf_holding_change CREATE + etf.discloses_daily. **SQLite는 `batch_alter_table` 사용.**

**완료 기준**
- 마이그레이션 up/down 정상. 기존 데이터 보존.
- ORM ↔ 도메인 매핑 라운드트립 테스트 통과.

---

### 단계 M2 — HoldingsProvider 포트 + ARK CSV 어댑터

**목표**: 발행사 공식 CSV로 일별 holdings(shares 포함) 스냅샷을 수집한다.

**작업 항목**
1. `application/ports.py`: `HoldingsProvider` 포트(`supports`, `fetch_holdings`).
2. `infrastructure/external/holdings/base_csv.py`: httpx 다운로드 + csv 파싱 + 정규화 공통(현금/`--`/NaN 제거, 비중 % 스케일 통일, 숫자 파싱). `external/base.py:with_backoff` 재사용.
3. `infrastructure/external/holdings/ark_provider.py`: ARK 펀드별 CSV URL 매핑, 컬럼(`date, fund, company, ticker, shares, "market value ($)", "weight (%)"`) → 도메인 `Holding` 정규화. CSV의 date를 `as_of_date`로.
4. `infrastructure/external/holdings/registry.py`: 등록된 provider 목록에서 `supports(issuer)`로 선택. 미지원 발행사는 None(graceful skip).
5. `seed/active_etfs.json`: `issuer`, `discloses_daily`, (ARK는 펀드코드) 필드 보강.

**완료 기준**
- ARK 티커(ARKK 등)에 대해 `fetch_holdings`가 shares·weight 채워진 스냅샷 반환.
- 샘플 CSV 픽스처 기반 파싱 단위 테스트 통과(`tests/test_ark_provider.py`).
- 미지원 발행사는 예외 없이 빈 결과로 skip.

---

### 단계 M3 — diff 엔진 + 변동 저장 + 수집 파이프라인 개편

**목표**: 새 스냅샷과 직전 스냅샷을 비교해 변동을 계산·저장한다.

**작업 항목**
1. `application/services/holding_change_service.py`: `diff(...)` 순수 함수(1.5장 ④). shares_delta 기준 분류, shares 없으면 weight_delta 폴백, `shares_epsilon` 임계치, `shares_delta_pct`/`weight_delta` 계산.
2. `infrastructure/db/repositories.py`: `SqlAlchemyHoldingRepository`에 신규 포트 메서드 구현(스냅샷/이전날짜/이력 쿼리), `SqlAlchemyHoldingChangeRepository` 구현. **upsert는 N+1 회피**(ETF id 1회 조회, 날짜 묶음 비교).
3. `application/pipeline/collect.py` 개편:
   - ETF별: registry로 provider 선택 → `fetch_holdings` → 스냅샷 upsert(shares) → `previous_snapshot_date` 로드 → `HoldingChangeService.diff` → `HoldingChangeRepository.upsert_many`.
   - 가격/지표 수집은 보조 단계로 유지(`discloses_daily=False`는 holdings diff 건너뜀).
   - per-ETF try/except로 부분 실패 격리, `collection_run`에 ETF 단위 에러 기록, 일부 실패 시 상태 `partial`.
4. `interfaces/deps.py`: HoldingsProvider registry, HoldingChangeService, HoldingChangeRepository 주입 추가.

**완료 기준**
- 서로 다른 날짜 2개 스냅샷으로 collect 2회 실행 시 `etf_holding_change`에 NEW/EXIT/INCREASE/DECREASE가 정확히 생성.
- diff 엔진 단위 테스트(합성 픽스처: 신규/청산/증가/감소/이름폴백/현금제외/임계치) 통과.
- 동일 입력 재실행 시 변동 행 멱등(중복 없음).

---

### 단계 M4 — 백엔드 API (holdings·변동·종목 이력·전체 피드)

**목표**: 프론트가 소비할 변동 추적 엔드포인트 완성.

**작업 항목 (엔드포인트)**
1. `GET /api/etfs/{ticker}/holdings?date=` — 스냅샷(shares·market_value·weight + 직전 대비 `shares_delta`/`weight_delta`). `date` 생략 시 최신.
2. `GET /api/etfs/{ticker}/holdings/dates` — 사용 가능한 스냅샷 날짜 목록.
3. `GET /api/etfs/{ticker}/changes?date=` — 해당 스냅샷의 트레이드(기본 변동만, UNCHANGED 제외).
4. `GET /api/etfs/{ticker}/positions/{holding}/history` — 한 종목의 shares·weight 시계열.
5. `GET /api/changes/recent?types=&limit=` — 유니버스 전체 최신 트레이드 피드.
6. `interfaces/api/changes.py` 신규 라우터 + `interfaces/api/etfs.py` 확장. **정적 경로를 `/{ticker}` 동적 경로보다 먼저 등록**(기존 `/compare` 패턴).
7. `interfaces/schemas/`: `holding.py`에 shares/market_value/delta 추가, 신규 `change.py`(`HoldingChangeResponse`, `PositionHistoryPointResponse`).
8. 서비스 단위 테스트: 인메모리 가짜 리포지토리로 검증(`tests/fakes.py` 확장).

**완료 기준**
- 위 엔드포인트가 `/docs`에서 동작. 데이터 없는 티커/날짜는 빈 배열 또는 404.
- `/api/changes/recent`가 여러 ETF 트레이드를 최신순으로 반환.

---

### 단계 M5 — 프론트: holdings 변동 UI + 종목 추세 + 전체 피드

**목표**: 변동 추적 화면을 백엔드와 연결.

**작업 항목**
1. `lib/types.ts`/`lib/api.ts` 확장 + 훅: `useHoldings(ticker, date)`, `useHoldingChanges`, `usePositionHistory`, `useRecentChanges`.
2. `app/etfs/[ticker]/page.tsx`: holdings 탭에 스냅샷 테이블 + **행별 변동 배지**(신규/청산/▲증가/▼감소, shares·weight Δ 표시), 스냅샷 날짜 피커. 종목 클릭 시 추세 차트.
3. `components/HoldingsTable.tsx` 변동 배지 컬럼 추가, `components/PositionHistoryChart.tsx`(shares·weight 듀얼축, `PriceChart.tsx` 패턴 재사용), `components/ChangeFeed.tsx`.
4. `app/changes/page.tsx`: 유니버스 전체 "최근 매매" 피드(ETF·종목·유형·Δ·날짜).
5. 데이터 신선도(마지막 스냅샷 날짜) 배지 + 푸터에 "투자자문 아님" 면책 고지.

**완료 기준**
- 상세에서 스냅샷 날짜 전환 시 변동 배지가 갱신.
- 종목 클릭 시 shares·weight 추세 차트 표시.
- `/changes`에서 전체 매매 피드 렌더, 행 클릭 시 해당 ETF 상세 이동.

---

### 단계 M6 — 발행사 확장 · 스케줄러 · 운영 · 배포

**목표**: 유니버스 확대 + 정기 자동 수집 + Vercel/Oracle 배포.

**작업 항목**
1. `infrastructure/external/holdings/`에 발행사별 어댑터 점진 추가(공식 CSV 보유 발행사 우선), registry 등록. 준투명 ETF는 `discloses_daily=False`로 분류해 diff 제외.
2. `infrastructure/scheduler/jobs.py`: APScheduler로 매일 1회(UTC, 미국장 마감 후) collect 등록, `main.py` lifespan에서 start/shutdown.
3. `interfaces/api/admin.py`: `POST /api/admin/collect`(수동 트리거), `GET /api/admin/runs`(수집 로그) — `ADMIN_TOKEN` 보호(`secrets.compare_digest`).
4. 컨트랙트 테스트(SQLite)로 HoldingRepository 스냅샷/이전/이력 쿼리 검증. 백엔드 배포 = **Oracle Cloud Always Free**(ARM `linux/arm64` 빌드, VCN 보안목록 + OS 방화벽 둘 다 개방, Caddy 자동 HTTPS), 프론트 = **Vercel**(`NEXT_PUBLIC_API_BASE_URL`), 백엔드 CORS에 Vercel 도메인 등록.
5. `README.md`에 수집/배포/환경변수 문서화.

**완료 기준**
- 스케줄러 등록 확인, 수동 트리거로 전체 파이프라인(holdings+diff) 1회 성공.
- 운영: Vercel 프론트가 Oracle VM API(HTTPS/CORS)로 실데이터 표시.
- `GET /api/admin/runs`로 수집 이력(partial 포함) 확인.

---

## 4. 환경 변수 (.env.example)

```bash
# backend
DATABASE_URL=sqlite+aiosqlite:///./quantbot.db   # 또는 postgresql+asyncpg://...
COLLECT_CRON_HOUR=22                              # UTC 기준 일일 수집 시각(미국장 마감 후)
HOLDINGS_HTTP_TIMEOUT=30                          # 발행사 CSV 다운로드 타임아웃(초)
ADMIN_TOKEN=change-me                             # /api/admin 보호용
CORS_ORIGINS=http://localhost:3000,https://<your-app>.vercel.app
FMP_API_KEY=                                      # (선택) 프로필/AUM 보강용, 없어도 동작

# frontend (Vercel 환경변수)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000     # 운영: https://api.<도메인>
```

---

## 5. 주요 리스크 & 대응

| 리스크 | 대응 |
|---|---|
| 발행사별 CSV 포맷 드리프트/커버리지(광범위 유니버스 = 다수 파서) | registry + graceful skip, 어댑터별 파싱 테스트, per-ETF 에러 로깅으로 격리 |
| 종목 매칭(채권/현금은 holding_ticker 없음) | `holding_key`로 이름 폴백 + 현금/노이즈 제외 |
| 준투명(ANT) ETF는 일별 미공시 | `discloses_daily=False`로 분류, diff 대상 제외 |
| 과거 이력 백필 불가(diff는 스냅샷 ≥2 필요) | 수집 시작 시점부터 누적. 발행사 아카이브 있으면 별도 백필 어댑터로 보강 |
| shares 변동에 설정/환매(creation/redemption) 혼입 | 실제 매매와 유닛 증감이 섞일 수 있음 → weight_delta(배분 변화)를 보조지표로 병기, 문서에 nuance 명시 |
| 발행사 CSV 요청 차단/rate-limit | with_backoff, 수집 간 sleep, User-Agent 설정, 실패 시 다음 배치 재시도 |
| SQLite → Postgres 전환 | 헥사고날 포트로 DB 격리 + DATABASE_URL 교체 + 계약 테스트(1.5장) |
| Oracle 무료 VM 포트 차단 | VCN 보안목록 **그리고** OS 방화벽(ufw/iptables) 둘 다 개방 |
| Oracle ARM(A1) 아키텍처 | Docker 이미지 `linux/arm64` 빌드/검증, 네이티브 휠 호환 확인 |
| 프론트(Vercel)→백엔드(Oracle) 통신 | 백엔드 HTTPS(Caddy 자동 TLS) + CORS에 Vercel 도메인 등록 |

---

## 6. 구현 순서 요약 (체크리스트)

- [x] M1 스키마·도메인 확장: shares/market_value + HoldingChange + 마이그레이션 0002
- [x] M2 HoldingsProvider 포트 + ARK CSV 어댑터 + registry
- [x] M3 diff 엔진 + 변동 저장 + collect.py 개편
- [x] M4 백엔드 API (holdings/changes/positions history/recent feed)
- [x] M5 프론트 변동 UI + 종목 추세 차트 + 전체 피드 + 면책 고지
- [ ] M6 발행사 어댑터 확장 + 스케줄러 + admin + Vercel/Oracle 배포

> 각 단계의 **완료 기준**을 만족하면 다음 단계로 진행한다. 단계는 독립적 PR/커밋 단위가 될 수 있다.
> **핵심 불변식**: 실제 매매 판정은 항상 shares Δ 기준. 비중%는 가격 드리프트가 섞이므로 보조지표로만 사용한다.
