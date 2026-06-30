# 자금흐름(ETF Fund Flow) 기능 — 구현 핸드오프

> **이 문서의 목적**: 다른 개발 에이전트(Codex 등)가 이 문서 **하나만** 읽고 ETF 자금흐름 기능을
> 처음부터 끝까지 구현할 수 있도록 자족적으로 정리한다. 배경·방법론·파일별 변경·테스트·함정·완료 기준을 담는다.
> 상위 로드맵 맥락은 `PLAN.md`의 **Phase H-4**를, 코드 규약 전반은 `CLAUDE.md`를 참조.

---

## 0. 한눈에

- **무엇**: 투명 액티브 ETF의 일별 **자금 유입/유출(creation/redemption)** 을 보유종목 스냅샷에서 추정하고, 그 결과로 개별 종목의 shares 증가가 "진짜 능동 매수"인지 "자금유입에 딸려간 기계적 매수"인지 구분한다.
- **왜**: 이 앱의 1차 시그널은 `shares` 증가다. 그런데 ETF에 자금이 들어오면 매니저 판단 없이도 **전 종목 shares가 일제히 증가**한다. 자금흐름을 빼지 않으면 shares 시그널이 오염된다. 자금유입분을 차감한 잔차(ε)가 진짜 컨빅션이다.
- **데이터 추가 비용 0**: 이미 수집 중인 `etf_holding`(shares·market_value)만으로 추정 가능. 외부 유료 데이터 불필요.
- **선행 조건**: 한 ETF에 **연속 2개 이상의 스냅샷**이 있어야 Δshares가 생긴다. production에는 시계열이 쌓여 있으므로 즉시 산출 가능. (로컬 dev DB는 스냅샷 1개뿐이라 합성 테스트로만 검증된다.)

---

## 1. 반드시 지킬 코드베이스 규약 (위반 금지)

`CLAUDE.md`의 핵심을 발췌한다. 어기면 리뷰에서 반려된다.

1. **매매 판정은 항상 `shares` 변화 기준.** `weight`는 가격 드리프트가 섞이므로 분류 축이 아니다. 자금흐름 분해의 잔차 ε도 **shares 단위**로 정의하고, weight는 보조 검증용으로만 쓴다.
2. **헥사고날 의존 방향은 항상 안쪽**: `interfaces / infrastructure → application → domain`.
   - `app/domain`: 순수 엔티티(dataclass) + 리포지토리 포트(Protocol). **FastAPI / SQLAlchemy / httpx import 금지.**
   - `app/application`: 유스케이스·계산 로직. 포트에만 의존. **자금흐름 계산 엔진은 여기, 외부 의존 0의 순수 함수로.**
   - `app/infrastructure`: DB·어댑터 등 구체 기술.
   - `app/interfaces`: FastAPI 라우터·DTO·DI(`deps.py`).
3. **Python 3.13**, 의존성 `uv`. **Ruff**(`line-length=100`). 편집 후 `uv run ruff check` 필수.
4. **pytest-asyncio** `asyncio_mode="auto"` — async 테스트에 데코레이터 불필요.
5. **DB 마이그레이션**: `backend/alembic/versions/` 번호순(현재 `0009`까지). **기존 마이그레이션 수정 금지**, 새 번호 파일 추가. 컬럼은 nullable로 추가 후 backfill. dev는 `AUTO_CREATE_TABLES=true`로 모델에서 바로 생성, prod는 alembic만.
6. **SQLite ↔ PostgreSQL 호환**: DB 특화 SQL 금지. `DATABASE_URL`만 바꿔 둘 다 동작해야 함. (`sqlite+aiosqlite` ↔ `postgresql+asyncpg`)
7. **문서 동기화**: 기능/API/스키마/설정 변경 시 `README.md`·`CLAUDE.md`·`.env.example`도 갱신. (`CLAUDE.md`·`docs/`는 `.gitignore`라 커밋엔 포함하지 말 것.)
8. **신규 provider/ETF 추가와는 무관** — 이 기능은 기존 데이터 위에서 계산만 한다.

---

## 2. 데이터 전제 & 현황 (방법론의 토대 — 검증 완료)

로컬 dev DB(`backend/quantbot.db`) 실측 결과:

- `etf_holding`의 `shares`·`market_value` **결측 0** → 가격 역산·NAV 합산의 전제 충족.
- `weight_i = mv_i / NAV` **완전 정합**(ARKK TSLA: weight 9.59% vs `mv/Σmv` 9.592%). 역산 가격 `p_i = mv_i/s_i`도 실제 시가와 일치(TSLA $375, AMD $532).
- **NAV 기준 = `Σ market_value`(공시 보유 기준)를 채택한다.** `etf_metric.aum`(yfinance totalAssets)은 현금·시점차로 ±15% 벗어나므로 **쓰지 말 것**(보조 표시만 허용).
- 로컬은 **스냅샷 1개뿐**이라 변동이 전부 `NEW`다. 따라서 로컬에선 자금흐름이 N/A로 나오는 게 정상. production 시계열에서 검증한다.

관련 스키마(이미 존재):
- `etf_holding`: `UNIQUE(etf_id, as_of_date, holding_key)`. 컬럼 `holding_ticker, security_id, holding_name, weight, shares, market_value`.
- 직전 스냅샷 조회 헬퍼가 이미 있음: `HoldingRepository.previous_snapshot_date(ticker, before)`, `.snapshot(ticker, as_of_date)`, `.latest_snapshot_date(ticker)`.
- `holding_key`는 `app/domain/value_objects.py::holding_key()`로 계산(이미 `.strip().upper()` 정규화). 현금류는 `None` → 제외.

---

## 3. 방법론 (정밀)

두 스냅샷 `t-1`(prev), `t`(cur). 각 보유종목 `i`에 대해 `holding_key`로 매칭.

- 가격(현재 스냅샷 역산): `p_i = mv_i(t) / s_i(t)`  (단 `s_i(t) > 0`)
- `NAV(t) = Σ_i mv_i(t)`
- `Δs_i = s_i(t) − s_i(t-1)`
- 집합: **공통** `C`(prev·cur 양쪽 존재), **신규** `N`(cur만), **청산** `X`(prev만)

### 3.1 순자금흐름(달러)
```
NetFlow = Σ_{i∈C} p_i·Δs_i  +  Σ_{i∈N} mv_i(t)  −  Σ_{i∈X} mv_i(t-1)
```
매니저의 종목 교체(A 사고 B 팔고)는 대체로 자금-중립이라 상쇄되고, 남는 순매수액 ≈ net creation으로 근사한다. `NetFlow > 0` = 순유입(creation), `< 0` = 순유출(redemption).

### 3.2 공통 성장률 g
```
denom = Σ_{i∈C} p_i·s_i(t-1)          # 직전 보유를 현재가로 평가한 값
g = NetFlow / denom                    # denom<=0 이면 g=None → 자금흐름 N/A
```

### 3.3 종목별 분해 — **시그널 정화의 핵심**
공통종목 `i∈C`에 대해:
```
passive_i = g · s_i(t-1)               # 자금유입에 따른 기계적 증감분
ε_i       = Δs_i − passive_i           # active residual (능동 매매분, shares 단위)
```
- `ε_i`의 부호 → `active_direction = BUY | NEUTRAL | SELL`.
- `|ε_i|`만 보지 않고 `residual_nav_bp = |ε_i|·p_i/NAV·10000`와
  `residual_position_pct = |ε_i|/max(s_i(t-1), s_i(t), 1)`로
  `active_intensity = NONE | WEAK | MEDIUM | STRONG`를 나눈다.
- legacy 호환용 `flow_adjusted = BUY | HOLD | SELL`은 남기되,
  `active_intensity=NONE`이면 `HOLD`, 그 외에는 방향에 따라 `BUY`/`SELL`.
- 신규 `i∈N`: `s_i(t-1)=0` → `passive=0`, `ε_i = s_i(t)` 전액 능동 매수.
- 청산 `i∈X`: 전액 능동 매도(`ε = −s_i(t-1)`).
- `shares_epsilon = 1.0`은 미세 shares 노이즈 억제용으로만 쓰고, 해석 강도는 NAV bp와 포지션 비중이 결정한다.

> ε는 weight 변화와 대응(weight↑ ⟺ 평균보다 빠른 성장)하지만 **가격효과를 제거**했다는 점이 우월하다.

### 3.4 집계 지표
```
active_buy   = Σ_{i: ε_i>0} p_i·ε_i              # 능동 매수 달러
active_sell  = Σ_{i: ε_i<0} p_i·(−ε_i)           # 능동 매도 달러
turnover     = ( Σ_{i∈C} p_i·|Δs_i| + Σ_{i∈N} mv_i(t) + Σ_{i∈X} mv_i(t-1) ) / NAV(t)
creation_r2  = 1 − SS_res / SS_tot
               SS_res = Σ_{i∈C} (p_i·ε_i)²       # 원점통과 회귀 Δs ~ g·s_prev 의 잔차(달러가중)
               SS_tot = Σ_{i∈C} (p_i·Δs_i)²
               # SS_tot==0 이면 creation_r2=None
```
`creation_r2`가 높으면 자금흐름 지배(패시브 성향), 낮으면 능동적 리밸런싱 활발(ARK류) → **"얼마나 액티브한가" 척도**로도 쓰인다.

### 3.5 N/A 처리
- prev 스냅샷이 없는 ETF(첫 스냅샷, single-snapshot) → 자금흐름 전체 N/A(행 미생성).
- `denom <= 0` → `g=None`, 분해 불가 → 행 미생성.
- `discloses_daily=False` ETF는 스냅샷이 거의 없으므로 자연히 제외된다.

---

## 4. 구현 단계 (파일별 — 위에서부터 순서대로)

> **권장 순서**: 4.1 → 4.2(엔진을 **TDD로 먼저**, §5 테스트와 함께) → 4.3 → 4.4 → 4.5 → 4.6 → 4.7. 4.8은 선택.

### 4.1 도메인 엔티티 — `app/domain/entities.py`
기존 dataclass 스타일로 추가:
```python
@dataclass(slots=True)
class EtfFlowDaily:
    ticker: str
    as_of_date: date
    prev_date: date
    net_flow: float
    flow_rate: float            # g
    active_buy: float
    active_sell: float
    turnover: float
    creation_r2: float | None

@dataclass(slots=True)
class SecurityFlowComponent:
    holding_key: str
    holding_ticker: str | None
    delta_shares: float
    passive_shares: float
    active_residual: float      # ε
    flow_adjusted: str          # "BUY" | "HOLD" | "SELL"
    active_direction: str       # "BUY" | "NEUTRAL" | "SELL"
    active_intensity: str       # "NONE" | "WEAK" | "MEDIUM" | "STRONG"
    active_confidence: str      # "LOW" | "MEDIUM" | "HIGH"
    residual_nav_bp: float | None
    residual_position_pct: float
```

### 4.2 순수 계산 엔진 — `app/application/services/flow_service.py` (신규)
`signal_service.py`의 `aggregate_daily_signals()`와 **동일한 스타일**(외부 의존 0의 순수 함수 + 얇은 서비스 클래스). 입력은 도메인 `Holding` 리스트.
```python
def decompose_flow(
    prev: list[Holding],
    cur: list[Holding],
    *,
    as_of_date: date,
    prev_date: date,
    ticker: str,
) -> tuple[EtfFlowDaily | None, list[SecurityFlowComponent]]:
    """§3 방법론 그대로. 산출 불가(prev 없음/denom<=0)면 (None, []) 반환."""
```
- `holding_key()`로 매칭, 현금류(None) 제외.
- `s<=0`·`mv<=0` 방어(ZeroDivision 금지).
- 순수 함수이므로 합성 데이터 단위 테스트만으로 완전 검증 가능 — **여기서 TDD 시작**.

서비스 클래스(리포지토리 위임용, DB 접근은 4.4 이후):
```python
class FlowService:
    def __init__(self, *, holdings: HoldingRepository, flows: EtfFlowRepository) -> None: ...
    async def recompute_for_etf(self, ticker: str, *, as_of_date: date | None = None) -> int: ...
    async def series(self, ticker: str, *, range_: str = "1y") -> list[EtfFlowDaily]: ...
```

### 4.3 ORM + 마이그레이션 — `0010_etf_flow_daily`
`SignalDailyORM`(`app/infrastructure/db/orm_models.py:131`)을 **본떠서** `EtfFlowDailyORM` 추가:
- `__tablename__ = "etf_flow_daily"`
- `UniqueConstraint("etf_id", "as_of_date", name="uq_etf_flow_daily_etf_date")`
- `Index("ix_etf_flow_daily_etf_date", "etf_id", "as_of_date")`
- 컬럼: `id`(PK), `etf_id`(`ForeignKey("etf.id", ondelete="CASCADE")`, index), `as_of_date`(Date, index), `prev_date`(Date), `net_flow`(Float), `flow_rate`(Float), `active_buy`(Float), `active_sell`(Float), `turnover`(Float), `creation_r2`(Float, nullable), `created_at`/`updated_at`(server_default `func.now()`).
- `etf` 관계: `EtfORM`에 `flows` relationship 추가(`prices/holdings/...` 옆).

마이그레이션 파일은 `backend/alembic/versions/0008_signal_daily*.py`를 템플릿으로 복사해 컬럼만 교체. `down_revision = "0009_..."`(현재 head 확인: `alembic heads`).
종목별 ε(`SecurityFlowComponent`)는 1차에선 **저장하지 않고 API 응답 시 on-the-fly 계산**으로 시작(스키마 단순화). 성능 이슈가 생기면 그때 `etf_holding_change`에 `active_residual` 컬럼을 nullable로 추가하는 후속 마이그레이션을 검토.

### 4.4 매퍼 + 리포지토리
- `app/infrastructure/db/mappers.py`: `to_etf_flow_daily(row) -> EtfFlowDaily` 추가(`to_signal_daily` 패턴, `row.etf.ticker` 사용).
- `app/domain/repositories.py`: `EtfFlowRepository` Protocol 추가
  ```python
  class EtfFlowRepository(Protocol):
      async def replace_for_etf_date(self, etf_id_or_ticker, flow: EtfFlowDaily) -> None: ...
      async def series(self, ticker: str, *, range_: str = "1y") -> list[EtfFlowDaily]: ...
      async def latest(self, ticker: str) -> EtfFlowDaily | None: ...
  ```
- `app/infrastructure/db/repositories.py`: `SqlAlchemyEtfFlowRepository` 구현. **멱등 upsert**(해당 `(etf_id, as_of_date)` DELETE 후 INSERT — `SqlAlchemySignalDailyRepository.replace_for_dates` 패턴). 범위 필터는 `SqlAlchemyPriceRepository._range_start()` 재사용.

### 4.5 파이프라인 훅 — `app/application/pipeline/collect.py`
`collect_once()`에서 ETF별 holdings 저장·diff **직후**에:
1. `prev_date = previous_snapshot_date(ticker, before=as_of_date)`
2. prev 있으면 `prev = snapshot(ticker, prev_date)`, `cur = snapshot(ticker, as_of_date)`
3. `decompose_flow(...)` → `EtfFlowRepository.replace_for_etf_date()`
- 기존처럼 **per-ETF try/except로 격리**(한 ETF 실패가 전체를 막지 않음). 멱등이라 재실행 안전.
- 전체 재계산용 admin: `POST /api/admin/recompute-flows`(선택) — `recompute-signals` 패턴.

### 4.6 DTO + API + DI
- `app/interfaces/schemas/`에 `flow.py` 신규: `EtfFlowResponse`(EtfFlowDaily 필드) + `SecurityFlowComponentResponse`.
- `app/interfaces/api/etfs.py`:
  - `GET /api/etfs/{ticker}/flow?range=1m|3m|6m|1y|ytd|max` → `list[EtfFlowResponse]`.
  - (선택) `GET /api/etfs/{ticker}/holdings`의 최신 스냅샷 응답에 **당일 flow 요약 + 종목별 능동 방향/강도 필드** 를 붙임(교차 시그널 `signal_*`을 붙인 것과 같은 방식). 종목별 ε은 4.3에서 저장 안 했으면 라우터에서 `decompose_flow`로 즉석 계산.
  - 라우터 시그니처는 `get_holdings`가 `signal_service`를 `Depends(get_signal_service)`로 받은 것과 동일하게 `flow_service: FlowService = Depends(get_flow_service)`.
- `app/interfaces/deps.py`: `get_flow_service()` 추가(`get_signal_service` 패턴, `holdings`+`flows` 리포지토리 주입).

### 4.7 프론트 — `frontend/`
- `lib/types.ts`: `EtfFlow` 타입 + (holdings에 붙이면) `Holding`에 `flow_adjusted`, `active_direction`, `active_intensity`, `active_confidence`, `residual_nav_bp`, `residual_position_pct` 추가.
- `lib/api.ts` + `hooks/useEtfDetail.ts`: `useEtfFlow(ticker, range)` 훅.
- 상세 페이지(`app/etfs/[ticker]/page.tsx`) 상단: **"오늘 자금 ±$Xm 유입/유출 · 회전율 Y% · 능동성(R²)"** 요약 카드.
- `HoldingsTable`: 종목 행에 "강한/중간/약한 능동 매수·매도 vs 자금 동반" 태그를 표시. 색 관습은 `TradeVisuals`의 rise(매수)·fall(매도)·muted(NEUTRAL) 재사용. 동적 Tailwind 클래스 금지(정적 분기).
- 면책: "추정값(공시 보유 기준), creation/redemption 정밀 데이터 아님" 1줄 명시.

### 4.8 (선택, 큰 가치) 시그널 정화 연계
`signal_service.py`의 BUY/SELL 판정을 절대 `Δs` 대신 `ε`(flow-adjusted)로 바꾸는 옵션. Phase D/E 시그널 품질을 직접 개선한다. **별도 의사결정 필요**(기존 `conviction_score` 정의 변경이므로 `signal_outcome` 재계산·문서 갱신 동반). 1차 릴리스에는 넣지 말고, 자금흐름이 실데이터로 검증된 뒤 별도 PR로.

---

## 5. 테스트 명세 — `backend/tests/test_flow_service.py` (신규)

`tests/fakes.py`에 `FakeEtfFlowRepository`, `FakeHoldingRepository`(이미 있으면 재사용) 준비. 합성 `Holding` 헬퍼는 `test_signal_service.py::_change` 스타일.

필수 케이스(순수 `decompose_flow`):
1. **순수 자금유입**: 전 종목 shares를 동일 비율 +10% → 모든 `ε_i ≈ 0`, `flow_adjusted=HOLD`, `net_flow>0`, `creation_r2 ≈ 1`.
2. **순수 능동 매수**: 한 종목만 shares↑, 나머지 불변 → 그 종목 `ε>0` BUY, `creation_r2` 낮음.
3. **자금유입 + 한 종목 역행**: 전 종목 +10%인데 한 종목만 감소 → 그 종목 `ε<0` SELL, 나머지 HOLD.
4. **신규/청산**: `N`은 전액 BUY, `X`는 전액 SELL로 분류되고 turnover/net_flow에 반영.
5. **prev 없음 / denom<=0**: `(None, [])` 반환(행 미생성).
6. **ZeroDivision 방어**: shares=0 종목이 섞여도 예외 없이 skip.
7. **부호 일관성**: `active_buy>0`, `active_sell>0`(절대값), `net_flow ≈ active_buy − active_sell + 공통패시브합` 관계가 합성값과 맞는지.

`uv run ruff check && uv run pytest tests/test_flow_service.py -q` 통과해야 함.

---

## 6. 실데이터 검증 절차 (production 시계열)

엔진·저장이 끝나면 production(또는 스냅샷 2개 이상 쌓인 환경)에서:
1. `POST /api/admin/recompute-flows`(또는 수집 재실행)로 `etf_flow_daily` 채우기.
2. **분포 점검**: `creation_r2`가 ARK 계열은 낮고(능동적), 비교적 패시브한 액티브 ETF는 높게 나오는지. 극단값(|flow_rate|>1) 빈도.
3. **자기정합성**: `net_flow` 부호와 같은 날 전 종목 평균 `weight` 변화 방향이 모순되지 않는지(자금유입인데 전 종목 weight가 일제히 하락하면 버그).
4. **교차검증(보조)**: 가능하면 yfinance `sharesOutstanding` 일변화와 `flow_rate` 상관 — 단 좌수 데이터 신뢰도가 낮으니 참고만.
5. 이상 없으면 4.8(시그널 정화) 진행 여부 결정.

---

## 7. 함정 체크리스트

- [ ] `s_i(t)=0`/`mv_i=0`/`prev`부재 **ZeroDivision·KeyError 방어**.
- [ ] `holding_key` None(현금류)은 prev/cur 양쪽에서 **제외**(`holding_key()`가 None 반환).
- [ ] NAV는 **`Σmv`**, `etf_metric.aum` 쓰지 말 것.
- [ ] 가격은 **현재 스냅샷(`t`) 기준** `p_i = mv_i(t)/s_i(t)`로 통일(prev 가격 혼용 금지).
- [ ] `ε`·시그널 판정은 **shares 단위**(weight 아님).
- [ ] 마이그레이션은 **새 번호 파일**, 기존 수정 금지. `down_revision` 정확히.
- [ ] SQLite/PostgreSQL 양쪽 동작(특화 SQL 금지). `func.now()` 등 공통만.
- [ ] 멱등 upsert(`(etf_id, as_of_date)` DELETE→INSERT). 재수집 안전.
- [ ] per-ETF 예외 격리(한 ETF 실패가 전체 수집 롤백 아님).
- [ ] 프론트 Tailwind **동적 클래스 금지**(정적 분기). 색은 `TradeVisuals` 관습 재사용.
- [ ] 로컬 dev(스냅샷 1개)에선 flow가 비어있는 게 **정상** — 합성 테스트로만 검증.
- [ ] 문서 동기화: `README.md`·`CLAUDE.md`(커밋 제외)·`.env.example`. `PLAN.md` H-4 체크박스 갱신.

---

## 8. 완료 기준 (Definition of Done)

- `decompose_flow` 순수 함수가 §5의 7개 합성 케이스를 통과.
- `etf_flow_daily` 마이그레이션이 SQLite·PostgreSQL 양쪽에서 `alembic upgrade head` 성공.
- 수집 파이프라인이 스냅샷 2개 이상인 ETF에 대해 flow 행을 멱등 생성.
- `GET /api/etfs/{ticker}/flow` 가 시계열을 반환, 상세 페이지가 자금/회전율/능동성과 종목별 `flow_adjusted` 태그를 렌더.
- `uv run ruff check && uv run pytest` 및 프론트 `npm run typecheck && npm run lint` 통과.
- production 시계열에서 §6 검증을 거쳐 분포가 상식적(ARK 저 R² 등).
- 문서 동기화 완료.
