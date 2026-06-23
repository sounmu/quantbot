# 다른 운용사 ETF holdings 추적 확장 계획

> 이 문서는 ARK 외 다른 운용사의 액티브 ETF도 holdings 변동 추적 대상으로 넣기 위한 구현 명세다.
> 코딩 에이전트(Codex 등)가 그대로 따라 구현할 수 있도록 작성됐다. 핵심 불변식과 방향은 `PLAN.md`를 따른다.

## 1. 배경 (왜 이 작업을 하는가)

quantbot의 목적은 액티브 ETF의 **보유 주식수(shares) Δ 기반 매매 추적**(ARK 트래커 스타일)이다.
현재 M1–M5는 완료됐지만 **ARK 5개 ETF만** 실제 diff 대상이다. 이유:

- `infrastructure/external/holdings/` 어댑터가 `ArkHoldingsProvider` 하나뿐이고
  `registry.py`에도 그것만 등록돼 있다.
- 시드(`app/seed/active_etfs.json`)에 BlackRock·JPMorgan·State Street 등 **15개 후보가 있지만
  전부 `discloses_daily=false`**(기본값)라 `application/pipeline/collect.py`의 holdings 단계에서 건너뛴다.

목표는 **다른 운용사의 다른 ETF도 사이트에서 추적**되도록, 다중 포맷(CSV/XLSX/JSON)을 처리하는
범용 어댑터 기반을 만들고, BlackRock/iShares(JSON)·State Street/SPDR(XLSX)·Capital Group(XLSX)·
T. Rowe Price(HTML embedded JSON)·Avantis(HTML embedded `etfHoldings`)·Virtus(legacy XLS)를
레퍼런스 어댑터로 추가한 뒤, 같은 패턴으로 나머지 발행사를 점진 확장할 수 있게 하는 것이다.

**핵심 불변식(유지)**: 실제 매매 판정은 항상 shares Δ. 비중%는 가격 드리프트가 섞이는 보조지표.
도메인·diff 엔진·서비스·API·프론트는 **변경 없음** — 확장은 인프라 어댑터 계층에만 한정된다.

## 2. 확정된 방향

- **소스 설정 위치**: 어댑터 내부 하드코딩 유지(ARK의 `_SLUGS`처럼 ticker→URL 맵). 시드 config 필드 추가 안 함.
- **포맷**: CSV / XLS / XLSX / JSON 전부 base에서 지원(XLSX용 `openpyxl`, legacy XLS용 `xlrd` 의존성 추가).
- **범위**: 범용 멀티포맷 프레임워크 + 레퍼런스 어댑터(각 포맷 경로를 실증) 우선,
  나머지 시드 활성은 동일 패턴으로 점진 추가.

## 3. 변경 대상 파일

### 3.1 의존성 — `backend/pyproject.toml`
- `dependencies`에 `openpyxl>=3.1.0` 추가(XLSX 파싱), `xlrd>=2.0.1` 추가(legacy XLS 파싱). `uv lock` 갱신.

### 3.2 멀티포맷 base — `backend/app/infrastructure/external/holdings/base_csv.py`
현재 `CsvHoldingsProviderBase`(CSV 전용)를 멀티포맷으로 확장. 기존 메서드(`download_csv`,
`parse_csv`, `normalize_header`, `parse_date`, `parse_number`)는 그대로 두고 다음을 추가:

- `download_bytes(url) -> bytes`: httpx + `with_backoff` + UA + timeout 단일 네트워크 프리미티브.
  기존 `download_csv`는 이걸 재사용하도록 리팩터(텍스트 디코드 후 `parse_csv`).
- `download_xlsx(url, *, sheet=None, header_contains=None) -> list[dict]`: `openpyxl`로 워크북 로드,
  헤더 행 자동 탐지(`header_contains`로 "Ticker"/"Weight" 같은 키워드가 있는 행 찾기), dict 리스트화.
- `download_xls(url, *, sheet=None, header_contains=None) -> list[dict]`: `xlrd`로 legacy `.xls` 워크북 로드,
  동일한 preamble/header 탐지 경로로 dict 리스트화.
- `download_json(url) -> Any`: JSON 응답 파싱(다음 JSON 발행사 어댑터용 base 준비).
- `parse_csv_with_preamble(text, *, header_contains) -> tuple[dict[str,str], list[dict]]`:
  iShares처럼 holdings 헤더 앞에 펀드 메타 전문(preamble)이 붙는 CSV 대응 — preamble 키/값과
  데이터 행을 분리 반환.
- `clean_holding_ticker(value)`: ARK 어댑터에 있던 `_clean_holding_ticker`를 base로 승격(중복 제거,
  `ark_provider.py`도 이걸 사용하도록 교체).
- `parse_number`의 cash/노이즈 토큰은 발행사별 표기를 흡수하도록 필요 시 확장(예: `"—"`, `"USD CASH"`).

### 3.3 레퍼런스 어댑터 (ARK 패턴 그대로, 하드코딩 맵)

**`holdings/ishares_provider.py`** (신규 — BlackRock/iShares, CSV+preamble + live JSON)
- `supports(issuer)`: `issuer.upper() == "BLACKROCK"`.
- 하드코딩 맵: `{"DYNF": <iShares 제품 holdings product-data URL>}`.
- iShares CSV 특성: 상단 preamble에 `"Fund Holdings as of"` 날짜가 있고 **행마다 날짜가 없음** →
  `parse_csv_with_preamble`로 as_of를 preamble에서 추출해 모든 Holding에 적용. 컬럼: `Ticker, Name,
  Shares, Market Value, Weight (%)` 등 → 도메인 `Holding` 정규화. 현금/파생/FX 행은 `holding_key`로 제외.
- 라이브 검증 메모: DYNF의 legacy `1467271812596.ajax?fileType=csv` 경로는 2026-06-22 기준
  `text/csv` 헤더에도 HTML product page를 반환하므로, 실제 fetch는 공식 BlackRock product-data JSON
  `component=holdings` endpoint를 사용한다. CSV+preamble 파서는 fixture/후속 iShares CSV 경로를 위해 유지한다.
- `parse_fixture(ticker, csv_text)` 노출(테스트용, ARK와 동일 패턴).

**`holdings/spdr_provider.py`** (신규 — State Street/SPDR, XLSX 경로 실증)
- `supports(issuer)`: `issuer.upper() == "STATE STREET"`.
- 하드코딩 맵: `{"TOTL": <SPDR 일별 holdings XLSX URL>}`.
- `download_xlsx(..., header_contains="Weight")` → 행 정규화. as_of는 시트 헤더/메타 또는 파일명 기준.
- `parse_fixture(ticker, xlsx_bytes)` 노출.

**`holdings/capital_group_provider.py`** (신규 — Capital Group, 공식 daily holdings XLSX)
- `supports(issuer)`: `issuer.upper() == "CAPITAL GROUP"`.
- 하드코딩 맵: `{"CGGR": <Capital Group daily-holdings XLSX>, "CGDV": <Capital Group daily-holdings XLSX>}`.
- `Daily Fund Holdings` 시트의 `Security Name`, `Ticker`, `Shares or Principal Amount`,
  `Market Value`, `Percent of Net Assets`를 `Holding`으로 정규화.
- Capital Group의 비중 값은 `0.0657`처럼 소수로 내려오므로 100을 곱해 `6.57` 퍼센트로 저장한다.
- `Cash & Equivalent` 행은 제외.

**`holdings/trowe_price_provider.py`** (신규 — T. Rowe Price, 상품 페이지 embedded JSON)
- `supports(issuer)`: `T. Rowe Price`.
- 하드코딩 맵: `{"TCAF": <Capital Appreciation Equity ETF page>}`.
- HTML의 `data-component-object` 중 `full.holdings` payload를 찾아 `effectiveDate`, `name`,
  `tickerSymbol`, `shareQuantity`, `marketValue`, `percentageTotalNetAssets`를 `Holding`으로 정규화.
- `tickerSymbol`이 없는 비상장/특수 보유종목은 `prioritizedIdentifier`를 보조 키로 사용한다.

**`holdings/avantis_provider.py`** (신규 — Avantis, 상품 페이지 embedded `etfHoldings`)
- `supports(issuer)`: `issuer.upper() == "AVANTIS"`.
- 하드코딩 맵: `{"AVUV": <Avantis U.S. Small Cap Value ETF page>, "AVDV": <Avantis International Small Cap Value ETF page>}`.
- HTML의 `a.portfolio.etfHoldings` payload를 찾아 `etfHoldingsAsOfDate`, `name`, `ticker`,
  `shareQuantity`, `baseMarketValue`, `weight`를 `Holding`으로 정규화.
- ticker가 비어 있는 권리/외국 주식은 CUSIP를 보조 키로 사용하고, currency/sweep investment/cash 행은 제외한다.

**`holdings/virtus_provider.py`** (신규 — Virtus, legacy XLS)
- `supports(issuer)`: `issuer.upper() == "VIRTUS"`.
- 하드코딩 맵: `{"PFFA": "https://www.virtus.com/assets/files/1xx/positions_pffa.xls"}`.
- `Positions as of ...` preamble에서 기준일을 읽고, `Name`, `Ticker`, `Quantity`, `Market Value`, `Weight`
  행을 `Holding`으로 정규화한다. cash/currency/sweep 행은 제외한다.

> 실제 URL·컬럼명·날짜 위치는 구현 시 **라이브 파일로 검증**한다. 미지원/포맷 변동 ticker는
> `return []`로 graceful skip(`collect.py`의 per-ETF try/except가 부분 실패를 격리하고 `collection_run`에 기록).
> JSON 경로는 base에 준비만 하고, JSON 공시 발행사를 추가할 때 같은 패턴으로 어댑터를 붙인다.

### 3.4 레지스트리 — `holdings/registry.py`
- 기본 provider 리스트에 신규 어댑터 등록:
  `[ArkHoldingsProvider(), ISharesHoldingsProvider(), SpdrHoldingsProvider(),
  CapitalGroupHoldingsProvider(), TRowePriceHoldingsProvider(), AvantisHoldingsProvider(),
  VirtusHoldingsProvider()]`.
- `collect.py`가 `HoldingsProviderRegistry()`를 인자 없이 생성하므로 **이 한 곳만** 고치면 파이프라인에 반영됨.

### 3.5 시드 — `backend/app/seed/active_etfs.json`
- 커버되는 ticker에 `"discloses_daily": true` 명시:
  **DYNF**(BlackRock), **TOTL**(State Street), **CGGR/CGDV**(Capital Group), **TCAF**(T. Rowe Price),
  **AVUV/AVDV**(Avantis), **PFFA**(Virtus).
- (선택) `external/universe.py`의 fallback을 `row.get("discloses_daily", False)`로 바꿔 ARK 특례
  하드코딩 제거 — 모든 활성 ETF가 시드에서 명시적으로 플래그를 갖도록(현재 ARK는 이미 명시돼 있음).

### 3.6 테스트 (`backend/tests/`)
- `test_ishares_provider.py`: preamble+날짜추출+현금제외를 담은 합성 CSV 픽스처로 `parse_fixture` 검증
  (`test_ark_provider.py` 패턴).
- `test_spdr_provider.py`: openpyxl로 인메모리 작은 XLSX를 만들어 `parse_fixture` 검증.
- `test_capital_group_provider.py`: 공식 XLSX 컬럼 구조와 소수 비중 정규화, cash 제외 검증.
- `test_trowe_price_provider.py`: embedded JSON 파싱, ISO 날짜, cash 제외 검증.
- `test_avantis_provider.py`: embedded `etfHoldings` JS 배열 파싱, currency 제외, CUSIP fallback 검증.
- `test_virtus_provider.py`: legacy XLS row 정규화, cash 제외 검증.
- base의 `parse_csv_with_preamble`/`download_xlsx` 정규화 단위 테스트.

### 3.7 명세 동기화 — `PLAN.md`
- M6 "발행사 어댑터 확장" 항목을 **멀티포맷(CSV/XLSX/JSON) registry 패턴 + 하드코딩 소스맵**으로 구체화.
- 리스크 표에 "포맷 다양성(preamble CSV/XLSX/JSON), 펀드별 URL 라이브 검증, 발행사별 현금 토큰 차이" 추가.
- M6 체크리스트 진행 갱신. **shares 기준 불변식 문구 유지.**

## 4. 새 발행사 추가 패턴 (나머지 시드 활성 확장용)

1. `holdings/<issuer>_provider.py` 작성: `supports()` + ticker→소스 하드코딩 맵 + 포맷별 base 호출 →
   `Holding` 정규화 + `parse_fixture`.
2. `registry.py` 기본 리스트에 등록.
3. 시드에서 해당 ticker `discloses_daily: true`.
4. 합성 픽스처 파싱 테스트 추가.

→ 도메인/서비스/API/프론트는 손대지 않는다.

## 4.1 현재 활성화/보류 현황

활성화 완료:

- ARK: ARKK, ARKG, ARKW, ARKF, ARKX
- BlackRock/iShares: DYNF
- State Street/SPDR: TOTL
- Capital Group: CGGR, CGDV
- T. Rowe Price: TCAF
- Avantis: AVUV, AVDV
- Virtus: PFFA

보류 큐:

- JPMorgan: JEPI/JEPQ의 공식 Excel endpoint 후보는 확인했지만 현재 live 응답이 비어 있어, 전체 holdings URL을
  재확인할 때까지 `discloses_daily=false` 유지.
- Dimensional: DFAC 상품 페이지는 지역/리다이렉트 응답이 섞이고 전체 daily holdings 파일 URL을 아직 확정하지
  못했으므로 보류.
- Fidelity: FBCG는 준투명 ETF 성격상 tracking basket은 공개되지만 실제 전체 포트폴리오 일일 공시는 확인되지
  않아 보류.
- PIMCO: MINT/BOND는 public API에서 top-ten holdings만 확인됐고, shares diff에 필요한 전체 holdings 소스가
  확정되지 않아 보류.

## 5. 검증 (Verification)

1. `cd backend && uv run pytest` — 신규 어댑터/base 테스트 포함 전체 통과.
2. `uv run python -m app.application.pipeline.collect`(holdings 단계) 실행 후:
   - DYNF·TOTL·CGGR·CGDV·TCAF·AVUV·AVDV·PFFA 스냅샷이 `etf_holding`에 shares/weight로 저장됐는지.
   - 2일치 스냅샷 누적 시 `etf_holding_change`에 NEW/EXIT/INCREASE/DECREASE 생성(diff 엔진은 무변경).
3. API: `GET /api/etfs/DYNF/holdings`, `/holdings/dates`, `/changes`, `/api/changes/recent`가 ARK 외
   발행사 데이터를 반환하는지 `/docs`에서 확인.
4. `GET /api/admin/runs`로 수집 상태(부분 실패 격리 포함) 확인 — 미지원 ticker가 전체를 깨지 않는지.
5. 프론트 ETF 목록/상세에서 DYNF·TOTL의 holdings·변동 배지가 ARK와 동일하게 렌더되는지(코드 변경 없이 동작해야 함).
