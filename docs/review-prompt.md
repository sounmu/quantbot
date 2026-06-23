# quantbot 다층 리뷰 프롬프트

Codex에서 여러 에이전트를 띄워 다층 코드 리뷰를 돌릴 때 사용하는 프롬프트.
아래 블록을 그대로 붙여 쓴다.

---

```
quantbot 전체 스택에 대해 다층 코드 리뷰를 수행해줘.

## 프로젝트 컨텍스트
- 액티브 ETF의 보유 "주식 수(shares)" 변동을 추적·표시하는 서비스다. 가격 카탈로그가 아니다.
  보유비중/변동의 정확성과 수집 데이터의 무결성이 최우선 가치다.
- 스택:
  - backend/ : Python 3.13 런타임(.python-version=3.13, Dockerfile=python:3.13-slim,
               pyproject requires-python=">=3.13", ruff target-version="py313").
               FastAPI, SQLAlchemy 2.0(async), Pydantic v2, APScheduler, httpx, yfinance, openpyxl.
               클린(헥사고날) 아키텍처 4계층.
  - frontend/ : Next.js 16(App Router), React 19, TanStack Query, Recharts, Tailwind, TypeScript.
- CLAUDE.md는 존재하지 않는다. 컨벤션 기준은 다음 순서로 적용한다:
  PLAN.md / README.md / docs/ → 레포 내 기존 코드의 지배적 패턴 → 각 라이브러리 공식 문서.

## 대상 레이어
- backend/app/domain/        (entities, value_objects, repositories=포트)
- backend/app/application/    (ports, pipeline/collect, services)
- backend/app/infrastructure/external/holdings/  (발행사별 파서 + base_csv + registry)
- backend/app/infrastructure/external/           (universe, yfinance_provider, base)
- backend/app/infrastructure/db/                 (engine, mappers, orm_models, repositories)
- backend/app/infrastructure/scheduler/          (jobs)
- backend/app/interfaces/                         (api/, schemas/, deps)
- frontend/                                       (app/, components/, hooks/, lib/)

## 실행 순서

### 1단계 (병렬): 레이어별 전문 리뷰어 동시 실행
- domain-app-reviewer
    도메인 모델 무결성, 클린 아키텍처 의존성 방향(domain이 infra/interface를 import하지 않는가),
    포트/어댑터 경계, value object 불변성, services의 비즈니스 규칙 정확성.
    특히 "shares 변동" 계산 로직의 정확성(델타 산출, 신규/청산 종목 처리, 결측 처리).

- holdings-provider-reviewer  ★최우선 리스크 레이어
    발행사별 파서(ark/ishares/spdr/trowe_price/capital_group)와 base_csv, registry 리뷰.
    점검: 외부 포맷 변경(헤더 위치/컬럼명/인코딩/구분자) 취약성, 티커·CUSIP 정규화,
    날짜 파싱·타임존, 결측/0주·합계행·각주행 필터링, 단위(천주/주) 혼동,
    파싱 실패 시 부분 성공 처리(한 발행사 실패가 전체를 죽이는가),
    httpx 호출의 timeout/재시도/상태코드 검증, registry 등록 계약의 일관성.

- collect-pipeline-reviewer
    application/pipeline/collect.py의 수집 흐름.
    점검: 멱등성(같은 날 재실행 시 중복 적재 여부), 트랜잭션 경계,
    부분 실패 롤백/격리, upsert 정합성, 동시성, 대량 적재 성능.

- db-reviewer
    SQLAlchemy 2.0 async 사용. mappers/orm_models/repositories.
    점검: async 세션 수명·커밋 경계, N+1, 인덱스 누락, mapper 양방향 정합성,
    repositories가 domain 포트 계약을 충족하는가, alembic 마이그레이션과 ORM 스키마 드리프트.

- scheduler-reviewer
    APScheduler jobs. 점검: job 중복 실행/오버랩 방지, 타임존, misfire 처리,
    개별 job 예외 격리, 수집 파이프라인과의 결합도.

- api-reviewer  (보안 포함)
    interfaces/api(admin/changes/etfs/meta), schemas, deps.
    점검: ★admin.py 인증·인가(보호되지 않은 관리 엔드포인트가 있는가),
    입력 검증, 페이지네이션, 에러 응답 일관성, CORS, ORM 오용/주입 위험,
    Pydantic 스키마가 내부 ORM을 그대로 노출하는지(과다 노출).

- config-reviewer
    프로젝트 설정·운영 무결성.
    점검: pyproject 의존성 핀/버전 정합(런타임 3.13과 선언 일치 유지),
    docker-compose(.yml/.prod.yml)와 .env(.example/.production.example) 정합,
    시크릿 노출, 빌드/배포 설정, ruff/pytest 설정.

- frontend-reviewer
    Next.js 16 App Router + React 19 관용구.
    점검: server/client component 경계, TanStack Query 캐시·키·에러/로딩 상태,
    데이터 페칭 위치, 타입 안전성, Recharts 렌더 성능, 접근성, XSS,
    백엔드 API URL/환경변수 처리.

### 2단계 (순차): 레이어 간 계약 검증
- contract-reviewer
    1) 도메인 포트(domain/repositories) ↔ infra 구현(db/repositories) 계약 일치
    2) 발행사 파서 ↔ registry ↔ collect 파이프라인의 데이터 모양 계약
    3) 백엔드 Pydantic 스키마(interfaces/schemas) ↔ 프론트엔드 TS 타입/응답 사용의 일관성
       (필드명/널 허용/날짜 포맷/숫자 타입 불일치 탐지)

### 3단계 (종합): 리포트 통합
- 모든 지적을 Severity(Critical/High/Medium/Low)로 분류
- 레이어 간 상충/중복 지적은 명시적으로 표시
- 우선순위 top 10 todo 리스트 생성
- docs/review-YYYYMMDD.md 파일로 저장 (YYYYMMDD는 오늘 날짜)

## 리뷰 원칙
- 파일:줄번호 필수 명시
- 수정 예시 코드 포함 (단, 큰 리팩터링은 방향성만)
- 근거 없는 지적 금지 — 위 "컨벤션 기준" 순서(PLAN.md/README/docs → 기존 코드 → 공식 문서) 또는
  공식 문서를 명시. CLAUDE.md는 없으므로 인용하지 말 것.
- "좋아 보임" 같은 무의미한 코멘트 금지
- 이 프로젝트가 'shares 변동 추적기'라는 점을 판단 기준으로 삼을 것
  (가격 정확도보다 보유수량 델타·결측·중복의 무결성이 우선)
```
