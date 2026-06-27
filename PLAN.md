# Quantbot — 다음 단계 로드맵 (PLAN.md)

> 이 문서는 **앞으로 할 일**을 기록하는 살아있는 로드맵이다.
> 이미 구현된 내용(헥사고날 백엔드, 발행사 holdings 수집, shares 기반 diff 엔진, 변동 API/피드, 수집 품질 대시보드)은 `CLAUDE.md`와 git 히스토리에 정리되어 있으므로 여기서 반복하지 않는다.
> 각 단계는 **목표 → 근거 → 작업 항목 → 완료 기준(Acceptance)** 순서로 쓴다. 위에서부터 의존 순서대로 진행한다.

---

## 0. North Star (최종 목표)

**일류 액티브 ETF 매니저들이 사는 종목을 따라 사서 내 수익률을 높인다.**

투명 액티브 ETF는 일급 운용역들이 매일 보유내역을 공시한다 = **스마트머니의 손패가 매일 공개**된다. Quantbot의 목적은 이 정보로
1. **그들이 지금 무엇을 모으고 있는지**(오늘의 실행 가능한 "따라 살 후보")를 보여주고,
2. **그렇게 따라 샀을 때 실제로 돈이 됐는지**(과거 시그널의 검증된 성과)를 함께 보여줘서 신뢰할 수 있게 만드는 것이다.

> 즉 ① **실행(무엇을 따라 살까)** 이 제품의 본체이고, ② **검증(Phase E)** 은 그 실행을 믿어도 되는지 뒷받침하는 근거다. 검증 없는 추종은 도박, 추종 없는 검증은 논문일 뿐 — 둘 다 필요하다.

### 핵심 가설 (= 따라 사기가 통하는 조건)
> 여러 투명 액티브 ETF가 **동시에 주식수를 늘리는(shares↑) 종목**은, 매수 시점 이후 일정 기간 동안 **벤치마크 대비 초과수익(excess return)** 을 낸다. → 이게 사실이면 "컨빅션 높은 종목을 따라 사는" 전략이 성립한다.

### 불변 원칙 (기존 + 신규)
- **매매 판정은 항상 `shares` Δ 기준.** `weight` Δ는 가격 드리프트가 섞이므로 시그널의 주축이 아니라 보조축이다. (분석에서도 동일: "비중이 올랐다"는 가격 때문일 수 있으므로, **주식수가 오른** 케이스를 1차 시그널로 본다.)
- **Point-in-time 규율.** holdings는 장 마감 후 공시되므로, 시그널은 `as_of_date` 다음 거래일(T+1)부터 실행 가능한 것으로 간주한다. forward return은 반드시 공시 인지 시점 **이후** 가격으로만 계산한다(look-ahead 금지).
- **초과수익으로 평가.** 상승장에서는 아무거나 오르므로 raw return이 아니라 벤치마크(QQQ/SPY 또는 모펀드 ETF) 대비 초과수익으로 시그널을 평가한다.

### 대상 유니버스 (확정)
- **주요 거래소(NASDAQ·NYSE Arca·Cboe BZX 등) 상장 + AUM ≥ $100M의 투명 액티브 ETF.** "나스닥 한정"은 모집단을 과하게 줄여서 **주요 거래소 + 규모 절충**으로 확정. 규모 임계값 `SIGNAL_MIN_AUM = 100_000_000`(env로 조정).
- 분석(가격 검증) 대상은 **미국 상장 주식을 보유하는 equity 액티브 ETF**로 한정한다. 채권/우선주 ETF(TOTL, PFFA 등)는 diff 추적은 유지하되 **시그널-가격 분석에서는 제외**한다(개별 종목 가격 매핑 비용·의미 한계).

---

## 현재 상태 → 목표 간 격차 (Gap Analysis)

| 영역 | 지금 | 최종 목표에 필요한 것 |
|---|---|---|
| 가격 데이터 | **ETF 자체** 가격만(yfinance) | **개별 보유종목(underlying)** 일별 가격 |
| 종목 정체성 | `holding_key`(ID/ticker/name) | `holding_key` → **거래 가능한 미국 주식 심볼** 해석 |
| 시그널 | per-ETF 변동 행 | **ETF 횡단 집계(conviction)** + 크기 버킷 |
| 평가 | 없음 | **forward return / hit rate / IC** 계산 엔진 |
| 유니버스 | 손큐레이션 ~75개 | **나스닥 + AUM 게이팅** + 거래소/AUM 메타 |
| UI | 반응형(테이블 중심, PC 가정) | **모바일 전용** 레이아웃 + 분석 화면 |

→ 단계는 **데이터 토대(C) → 시그널(D) → 평가(E) → 표현(F)** 순으로 쌓고, 그와 병행해 **모바일 전환(A)** 과 **유니버스 정제(B)** 를 먼저/동시에 처리한다.

---

## Phase A — 모바일 전용 UI 전환

**목표**: PC 레이아웃 가정을 버리고 **모바일 단일 컬럼 / 카드 / 하단 탭** 중심으로 재설계한다. 설치형 PWA를 지향한다.

**근거**: 최종 산출물은 "오늘 매니저가 무엇을 모으는가 + 그게 올랐는가"를 손에서 빠르게 보는 경험이다. 데이터 밀도 높은 테이블(현재 `EtfTable`/`HoldingsTable`)은 모바일에서 가독성이 떨어진다.

**작업 항목**
1. 레이아웃: `frontend/app/layout.tsx`에 모바일 고정 셸(최대폭 `max-w-[480px]` 중앙 정렬, `AppShell` 재작성). 데스크톱 전용 가로 테이블 제거.
2. 내비게이션: 상단 nav → **하단 고정 탭바**(목록 / 변동피드 / 분석 / 비교). 터치 타겟 ≥44px, `aria-label` 유지.
3. 컴포넌트 모바일화:
   - `HoldingsTable` → **포지션 카드 리스트**(종목명·shares·weight + 변동 배지). 가로 스크롤 금지.
   - `EtfTable` → ETF 카드.
   - `ChangeFeed` → 타임라인형 카드.
   - 차트(`PriceChart`/`PositionHistoryChart`/`CompareChart`)는 `ResponsiveContainer` 폭 100%, 모바일 높이 프리셋.
4. PWA: `manifest.json`(standalone, theme color), 아이콘, `viewport`에 `viewport-fit=cover`. (선택) 오프라인 폴백.
5. E2E: `frontend/e2e/`의 Playwright를 **모바일 뷰포트**(예: iPhone 13)로 고정, 핵심 페이지 smoke 갱신.

**완료 기준**
- 360–430px 뷰포트에서 모든 페이지가 가로 스크롤 없이 렌더.
- 하단 탭으로 4개 주요 화면 이동.
- Playwright 모바일 smoke 통과. `npm run lint && npm run typecheck` 통과.

---

## Phase B — 유니버스 정제 (나스닥 + 규모 게이팅)

**목표**: 추적 대상을 **주요 거래소 상장 + AUM ≥ $100M**의 액티브 ETF로 좁히고, 거래소·AUM 메타를 데이터로 보유한다.

**근거**: 분석의 신뢰도는 "의미 있는 규모의" 펀드로 모집단을 정의할 때 올라간다. 규모가 큰 펀드일수록 creation/redemption 노이즈 대비 매니저 의사결정 신호가 또렷하다. "나스닥 한정"은 ARK 계열 등 다수가 NYSE Arca/Cboe BZX 상장이라 모집단을 과하게 줄이므로 **주요 거래소 + 규모 절충**으로 확정.

**작업 항목**
1. 메타 확장: `etf`에 `exchange`(상장 거래소, MIC/이름)와 `aum`(이미 `etf_metric.aum` 존재 → 활용/승격) 추가. 새 alembic 마이그레이션(`0006_etf_exchange_aum`).
2. AUM/거래소 소스: 1차로 yfinance `Ticker.info`(`totalAssets`, `exchange`) 어댑터에서 보강. 신뢰도 한계 문서화, 수동 보정 허용(시드 JSON에 override 필드).
3. 게이팅: `universe.py`/`seed`에서 `exchange`·`aum` 기준으로 **분석 대상 플래그**(`in_signal_universe: bool`) 산출. 설정: `SIGNAL_MIN_AUM`(기본 `100_000_000`), `SIGNAL_EXCHANGES`(기본 주요 거래소 화이트리스트: NASDAQ·NYSE Arca·Cboe BZX 등).
4. 품질 대시보드(`/api/admin/dashboard/quality`)에 거래소/AUM/게이팅 결과 컬럼 추가.

**완료 기준**
- 각 추적 ETF에 거래소·AUM이 채워지고, 게이팅 기준으로 분석 유니버스가 산출된다.
- 임계값을 env로 바꾸면 분석 유니버스가 재계산된다.

---

## Phase C — 보유종목 가격 토대 (Underlying Security Master + Price Store)

**목표**: 개별 보유 주식의 **일별 가격 시계열**을 수집·저장한다. (분석의 데이터 토대 — 가장 무거운 단계.)

**근거**: "비중이 오른 종목이 실제로 올랐는가"를 보려면 ETF가 아니라 **개별 종목**의 가격이 있어야 한다. 현재는 없다.

**작업 항목**
1. **Security master**: `holding_key` → 거래 가능한 미국 주식 심볼 해석.
   - 1차: `holding_ticker`가 있는 US equity 행만 대상(대부분의 ARK/Avantis/iShares equity 보유가 해당).
   - `security_id`(CUSIP/ISIN)만 있고 ticker가 없는 행은 분석에서 보류(향후 CUSIP→ticker 매핑 어댑터 과제로 남김).
   - 신규 테이블 `security`(security_key PK, ticker, name, first_seen, is_priceable) + 도메인 엔티티/포트.
2. **가격 스토어**: 신규 테이블 `security_price`(security_key, date, close, adj_close, volume) — `UNIQUE(security_key, date)`. **adj_close**(배당/분할 조정)를 수익률 계산의 기준으로 둔다. **벤치마크(QQQ)도 같은 스토어에 적재**해 초과수익 계산에 사용한다.
3. **수집 어댑터**: `MarketDataProvider`를 재사용해 underlying 티커 배치 수집(yfinance). 수백~수천 종목 fan-out → 배치/스로틀/backoff, 이미 받은 구간 skip(증분).
4. **파이프라인 훅**: 수집 시 "현재 분석 유니버스 ETF들의 최신 스냅샷에 등장하는 고유 underlying 집합"을 구해 가격을 갱신. `collect.py`에 `--with-underlying-prices` 단계 추가(분리 실행 가능).
5. 보존정책: `security_price`는 분석 horizon(최대 60거래일)을 넉넉히 커버하도록 장기 보존(예: 2년+). 마이그레이션 `0007_security_price`.

**완료 기준**
- 분석 유니버스의 고유 보유 종목에 대해 일별 `adj_close`가 적재된다.
- 재실행 시 증분만 수집(멱등). 수집 실패 종목은 격리·로깅되고 전체를 막지 않는다.

---

## Phase D — 시그널 모델 (ETF 횡단 conviction 집계)

**목표**: 변동(`etf_holding_change`)을 **분석 가능한 시그널 이벤트**로 정규화하고, **여러 ETF가 같은 종목을 동시에 매집하는 강도(conviction)** 를 계산한다.

**근거**: 단일 ETF의 매수보다, **복수의 독립 액티브 매니저가 동시에** 같은 종목을 늘리는 것이 더 강한 신호라는 게 핵심 가설의 요체다.

**작업 항목**
1. 시그널 정의(도메인): `Signal(security_key, as_of_date, direction, ...)`.
   - `direction` = BUY(shares↑ / NEW) vs SELL(shares↓ / EXIT).
   - 크기 지표: `shares_delta_pct`, `weight_delta`, **달러 흐름**(`shares_delta × adj_close`).
2. **횡단 집계**: 특정 날짜·종목에 대해 분석 유니버스 ETF들을 묶어
   - `n_buying` / `n_selling`(매수·매도 ETF 수),
   - `net_shares_flow`, `net_dollar_flow`,
   - `conviction_score`(예: 매수 ETF 수 또는 순매수 비율 가중).
3. 저장: 신규 테이블 `signal_daily`(security_key, as_of_date, n_buying, n_selling, net_flow, conviction_score, ...) — 평가/조회 가속용 머티리얼라이즈. 마이그레이션 `0008_signal_daily`. 순수 집계 로직은 `application/services/signal_service.py`(외부 의존 0, 단위 테스트 가능).
4. API: `GET /api/signals/daily?date=`(그날의 컨빅션 상위 종목), `GET /api/signals/security/{security_key}`(한 종목의 시그널 이력 + 어떤 ETF들이 사는지).

**완료 기준**
- 임의 날짜에 대해 "여러 ETF가 동시에 매집한 종목" 랭킹이 나온다.
- 횡단 집계가 합성 픽스처 단위 테스트(2개 ETF가 같은 종목 매수 → conviction=2 등)를 통과한다.

---

## Phase E — 평가 엔진 (Forward Return / Hit Rate / IC) — **분석의 핵심**

**목표**: 각 시그널 이후 underlying의 **forward 초과수익**을 계산하고, 시그널의 예측력을 **hit rate · 평균 초과수익 · Information Coefficient**로 측정한다.

**근거**: 이 단계가 곧 최종 목표의 답("비중↑ 종목이 실제로 오르나?")을 산출한다.

**방법론(설계 결정)**
1. **이벤트**: 각 (security, as_of_date) BUY 시그널을 이벤트로 본다. 실행 시점은 **T+1 시가 인지 가능일**(look-ahead 방지).
2. **Horizon**: H ∈ {1, 5, 20, 60} 거래일. 각 H에 대해 `adj_close` 기준 forward return.
3. **초과수익**: `excess = stock_return(H) − benchmark_return(H)`. **1차 벤치마크 = QQQ 단일**(`config`의 `BENCHMARK_TICKER`, 기본 `QQQ`). 평가 엔진은 벤치마크를 파라미터로 받게 설계해 **나중에 SPY·모펀드 ETF·베타조정 등 비교 대상을 추가**해도 코드 변경 없이 확장 가능하게 둔다.
4. **버킷팅/층화**: NEW vs INCREASE, conviction 레벨(1/2/3+), 크기 버킷(shares_delta_pct·달러흐름 분위), 모펀드 테마별.
5. **지표**:
   - **Hit rate**: 초과수익 > 0 비율.
   - **평균/중앙값 초과수익** (H별 → 시간 감쇠 곡선).
   - **IC**: 시그널 크기와 forward 초과수익의 순위상관(Spearman).
6. **편향 점검**: 생존편향(EXIT/상장폐지 포함 시도), creation/redemption 오염(절대 shares 대신 % 변화·달러흐름·conviction으로 완화), 표본 부족(초기엔 신뢰구간 넓음 → 표본수 함께 표기), 다중검정 주의.

**작업 항목**
1. `application/services/evaluation_service.py`: 순수 함수형 평가(가격·시그널 픽스처만으로 단위 테스트). forward return·excess·hit·IC 계산.
2. 캐시 테이블(선택) `signal_outcome`(signal 식별 + H별 excess return) — 무거운 재계산 회피. 마이그레이션 `0009_signal_outcome`.
3. API:
   - `GET /api/analysis/performance?bucket=&horizon=` — 버킷·horizon별 hit rate·평균 초과수익·표본수·IC(요약 통계).
   - `GET /api/analysis/security/{security_key}` — 한 종목의 과거 BUY 시그널 점들에 실제 forward 수익을 오버레이.
4. 배치: 평가 산출을 수집 파이프라인 끝 또는 별도 admin 트리거(`POST /api/admin/recompute-analysis`)로 갱신.

**완료 기준**
- "conviction≥2 BUY 시그널의 20거래일 평균 초과수익 = X%, hit rate = Y%, n = Z" 형태의 표가 API로 나온다.
- 합성 데이터(상승하도록 만든 종목 + 시그널)로 평가 엔진이 양의 초과수익·높은 hit rate를 정확히 산출(단위 테스트).
- look-ahead 차단(공시일 당일·이전 가격이 forward 계산에 절대 안 들어감)이 테스트로 보장된다.

---

## Phase F — 분석 UI (모바일)

**목표**: 평가 결과를 모바일에서 직관적으로 보여준다.

**작업 항목**
1. **시그널 성과 화면**(`app/analysis/page.tsx`): horizon 토글 + 버킷별 hit rate / 평균 초과수익 / 표본수 / IC 카드·막대.
2. **컨빅션 보드**(`app/signals/page.tsx` 또는 변동피드 통합): "오늘 여러 ETF가 동시에 매집 중인 종목" 랭킹, 각 종목에 누가 사는지.
3. **종목 상세**: 한 종목의 시그널 점 + 이후 실제 가격 궤적 오버레이(시그널이 맞았는지 시각적으로). `PositionHistoryChart` 확장.
4. 면책: "백테스트 결과이며 투자자문이 아님 / 과거 성과가 미래를 보장하지 않음 / creation·redemption 오염 가능" 고지를 분석 화면에 명시.

**완료 기준**
- 모바일에서 "시그널이 실제로 통했는가"를 한 화면에서 읽을 수 있다.
- 표본수·신뢰 경고가 함께 표기된다.

---

## Phase G — (선택) 페이퍼 포트폴리오 백테스트

**목표**: 규칙 기반 가상 포트폴리오(예: 매일 conviction 상위 N 종목 동일가중 매수, 20거래일 보유)의 **누적 초과수익 곡선**을 산출해 시그널을 제품 서사로 만든다.

**작업 항목**: `evaluation_service`에 포트폴리오 시뮬레이터(거래비용·슬리피지 가정 명시), `GET /api/analysis/backtest`, 모바일 누적수익 차트.

**완료 기준**: 벤치마크 대비 누적 곡선 + 요약(연환산 초과수익, MDD, 표본기간)이 나온다. 거래비용 가정이 문서화된다.

---

## 7. 결정 사항

**확정**
1. **거래소 정책**: 주요 거래소(NASDAQ·NYSE Arca·Cboe BZX 등) + 규모 절충. "나스닥 한정" 폐기. → `SIGNAL_EXCHANGES` 화이트리스트.
2. **AUM 임계값**: `SIGNAL_MIN_AUM = 100_000_000` ($100M, env 조정).
3. **벤치마크**: **1차 QQQ 단일**(`BENCHMARK_TICKER=QQQ`). 평가 엔진은 벤치마크 파라미터화 → 추후 SPY·모펀드별·베타조정 추가.

**잠정(후속 확정)**
4. **모바일 범위**: 모바일폭 고정(`max-w-[480px]`) + PWA 권장. 데스크톱은 모바일폭으로 렌더.
5. **forward 실행 가격**: T+1 종가 기준(잠정). T+1 시가 옵션은 Phase E에서 비교.

---

## 8. 리스크 & 대응

| 리스크 | 대응 |
|---|---|
| underlying 가격 fan-out 비용·rate limit (수천 종목) | 증분 수집 + 배치/스로틀/backoff, 분석 유니버스로 모집단 축소, 실패 격리 |
| CUSIP/ISIN만 있고 ticker 없는 보유 | 1차는 ticker 보유 행만 분석, CUSIP→ticker 매핑은 후속 과제로 분리 |
| creation/redemption이 shares Δ에 오염 | %변화·달러흐름·conviction(ETF 수) 중심 평가, 절대 shares 단독 의존 회피, 면책 명시 |
| look-ahead / 생존 편향 | 공시 인지일(T+1) 이후 가격만 사용 + 테스트로 강제, EXIT/폐지 종목 포함 시도 |
| 초기 표본 부족 → 과적합/허위 유의 | 표본수·신뢰구간 병기, 다중검정 경고, horizon·버킷 사전 등록 |
| "나스닥 상장" 모집단이 과소 | Phase B에서 실제 거래소 조사 후 정책 절충(§7-1) |
| 상승장 편향(raw return 착시) | 항상 벤치마크 대비 초과수익으로 평가 |
| 모바일 차트 가독성 | Recharts 모바일 프리셋, 핵심 1–2지표만, 카드화 |

---

## 9. 진행 체크리스트

- [x] A. 모바일 전용 UI 전환 (셸/하단탭/카드화/PWA/모바일 E2E) — + Pretendard Variable 폰트, holdings 브라우저(필터칩·정렬·검색·더보기), 선택 종목 차트를 목록 위로 배치
- [x] B. 유니버스 정제 (거래소·AUM 메타 + 게이팅) — seed 티커 yfinance profile 실태 조사(`BTS`/Cboe US, `PCX`/NYSEArca, `NGM`/NasdaqGM, `NYQ`/NYSE) 반영, `0006_etf_exchange_aum`, `SIGNAL_MIN_AUM`/`SIGNAL_EXCHANGES`, quality/API 메타 노출 완료
- [ ] C. Underlying security master + 가격 스토어(adj_close)
- [ ] D. 시그널 모델 + ETF 횡단 conviction 집계
- [ ] E. 평가 엔진 (forward 초과수익 / hit rate / IC) + look-ahead 차단
- [ ] F. 분석 UI (성과 화면 / 컨빅션 보드 / 종목 시그널 오버레이)
- [ ] G. (선택) 페이퍼 포트폴리오 백테스트

> **핵심 불변식**: 시그널은 shares Δ로 정의하고, 평가는 항상 **벤치마크 대비 초과수익**으로, **공시 인지일 이후 가격**으로만 한다.
