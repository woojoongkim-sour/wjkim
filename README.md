# MSP Archive Platform

MSP(Managed Service Provider) 운영 기록 중심 플랫폼.  
Zabbix 등 모니터링 시스템의 이벤트를 수집하고, AI 기반 분석/채팅과 함께 운영 문서 아카이브를 통합 제공합니다.

---

## 1. 프로젝트 개요

### 해결하는 문제

MSP 운영팀은 다수의 고객사 인프라를 관리하면서 아래와 같은 어려움을 겪습니다:

- 장애 이벤트가 여러 모니터링 시스템에 분산되어 있어 전체 현황 파악이 어려움
- 과거 유사 장애의 원인/해결 방법이 담당자 개인 지식에 의존
- 운영 문서(매뉴얼, 절차서)가 보호(암호/DRM)되어 있어 즉시 참조가 불가
- 장애 대응 이력이 체계적으로 기록되지 않아 재발 방지 분석이 어려움

### 주요 기능

| 기능 | 설명 |
|------|------|
| **이벤트 대시보드** | 고객사별 이벤트 현황, 심각도 분포, 위험도 상위 이벤트, 최근 조치 이력 |
| **이벤트 관리** | 이벤트 목록/상세/필터링, 상태 변경(확인/해결), 조치 기록 |
| **AI 분석** | GPT-4o 기반 이벤트 원인 분석, 위험도/재발 점수, 권장 조치사항 |
| **이벤트 채팅** | 이벤트 문맥을 이해하는 AI 채팅 (관련 문서/인시던트 참조) |
| **Zabbix 웹훅** | Zabbix 알림을 자동 수집하여 이벤트로 변환 |
| **문서 아카이브** | 운영 문서 업로드/검색/다운로드, 보호 문서 감지 및 수동 정제 |
| **인시던트 관리** | 과거 장애 이력 관리 및 정제된 지식(KB) 생성 |
| **감사 로그** | 모든 API 호출에 대한 감사 추적 |

---

## 2. 기술 스택

### Backend
- **Framework**: FastAPI (Python 3.11)
- **ORM**: SQLAlchemy 2.x (async)
- **Database**: PostgreSQL 16
- **Object Storage**: MinIO (S3 호환)
- **Task Queue**: Celery + Redis
- **AI**: OpenAI GPT-4o, text-embedding-3-small

### Frontend
- **Framework**: React 19 + TypeScript
- **Build**: Vite 8
- **Styling**: TailwindCSS 4
- **State**: TanStack React Query 5
- **Routing**: React Router 7
- **HTTP**: Axios

### Infrastructure
- **Container**: Docker + Docker Compose
- **Reverse Proxy**: Nginx (프론트엔드 서빙 + API 프록시)

---

## 3. 프로젝트 구조

```
msp-archive/
├── app/                          # Backend (FastAPI)
│   ├── main.py                   # FastAPI 앱 초기화, 라우터 등록, 미들웨어
│   ├── api/                      # API 엔드포인트 (라우터)
│   │   ├── customers.py          # 고객사/서버/서비스 CRUD
│   │   ├── documents.py          # 문서 업로드/조회/다운로드
│   │   ├── events.py             # 이벤트 관리 (상태, 이력, 조치)
│   │   ├── incident.py           # 인시던트 대시보드/이벤트/분석/채팅
│   │   ├── search.py             # 검색 (텍스트 + 벡터)
│   │   ├── chat.py               # AI 채팅 (문서 기반)
│   │   └── audit.py              # 감사 로그 조회
│   ├── services/                 # 비즈니스 로직 계층
│   │   ├── zabbix_service.py     # Zabbix 웹훅 처리 및 이벤트 변환
│   │   ├── analysis_service.py   # AI 기반 이벤트 분석/보고서 생성
│   │   ├── event_chat_service.py # 이벤트 문맥 채팅 서비스
│   │   ├── document_processor.py # 문서 처리 파이프라인 (추출→청킹→임베딩)
│   │   ├── search_service.py     # 벡터/시맨틱 검색
│   │   └── embedding.py          # OpenAI 임베딩 서비스
│   ├── models/                   # SQLAlchemy ORM 모델
│   │   ├── customer.py           # Customer, Server, Service
│   │   ├── event.py              # EventOccurrence, Assessment, IncidentCase
│   │   ├── document.py           # Document, DocumentChunk, DocumentRelation
│   │   ├── audit.py              # AuditLog, SanitizedKnowledge
│   │   └── enums.py              # EventSeverity, EventStatus 등 열거형
│   ├── schemas/                  # Pydantic 요청/응답 스키마
│   ├── core/                     # 공통 인프라
│   │   ├── config.py             # 환경 설정 (Pydantic Settings)
│   │   ├── database.py           # DB 엔진/세션 팩토리
│   │   ├── storage.py            # S3/MinIO 스토리지 클라이언트
│   │   └── audit.py              # 감사 로깅 미들웨어
│   └── workers/                  # Celery 비동기 작업
│       ├── celery_app.py         # Celery 설정
│       └── tasks.py              # 문서 처리, 이벤트 분석 태스크
├── frontend/                     # Frontend (React + Vite)
│   ├── src/
│   │   ├── App.tsx               # 라우팅 정의
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx # 대시보드 (KPI, 위험도 순위, 최근 활동)
│   │   │   ├── EventListPage.tsx # 이벤트 목록 (필터, 페이지네이션)
│   │   │   └── EventDetailPage.tsx # 이벤트 상세 (분석, 이력, 채팅)
│   │   ├── api/client.ts         # Axios API 클라이언트
│   │   ├── components/Layout.tsx # 사이드바 + 헤더 레이아웃
│   │   └── types/incident.ts     # TypeScript 타입 정의
│   ├── nginx.conf                # Nginx 설정 (SPA + API 프록시)
│   └── Dockerfile                # 멀티스테이지 빌드 (Node→Nginx)
├── scripts/
│   ├── init_db.py                # DB 테이블 생성 스크립트
│   └── seed_data.sql             # 시연용 시드 데이터
├── docker-compose.yml            # 6개 서비스 오케스트레이션
├── Dockerfile                    # Backend Docker 이미지
└── pyproject.toml                # Python 의존성 (Poetry)
```

---

## 4. 아키텍처 및 워크플로

### 전체 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Compose                        │
│                                                          │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │ Frontend │───▶│    Nginx     │───▶│  FastAPI App  │  │
│  │ React/TS │    │  (port 3000) │    │  (port 8000)  │  │
│  └──────────┘    └──────────────┘    └───────┬───────┘  │
│                        /api/*                │           │
│                       프록시                  │           │
│                                              │           │
│  ┌──────────┐    ┌──────────────┐    ┌───────▼───────┐  │
│  │  Celery  │◀──▶│    Redis     │    │  PostgreSQL   │  │
│  │  Worker  │    │  (port 6379) │    │  (port 5432)  │  │
│  └──────────┘    └──────────────┘    └───────────────┘  │
│       │                                                  │
│       │          ┌──────────────┐                        │
│       └─────────▶│    MinIO     │                        │
│                  │ (port 9000)  │                        │
│                  └──────────────┘                        │
└─────────────────────────────────────────────────────────┘
         ▲
         │ Webhook (POST)
┌────────┴────────┐
│  Zabbix Server  │
└─────────────────┘
```

### 이벤트 처리 워크플로

```
1. Zabbix에서 장애 감지
   └─▶ POST /api/v1/incident/webhook/zabbix

2. 웹훅 수신 및 이벤트 생성
   └─▶ ZabbixService.process_webhook()
       ├─ 심각도 매핑 (Zabbix → EventSeverity)
       ├─ 중복 이벤트 감지 (source_event_id 기준)
       ├─ EventOccurrence 생성 또는 occurrence_count 증가
       └─ EventStateHistory 기록

3. 대시보드에서 모니터링
   └─▶ GET /api/v1/incident/dashboard
       ├─ KPI 집계 (전체/오픈/크리티컬/해결)
       ├─ 심각도/상태 분포
       ├─ 위험도 상위 이벤트 (risk_score 기준)
       └─ 최근 조치 활동

4. 이벤트 상세 확인
   └─▶ GET /api/v1/incident/events/{id}
       ├─ 상태 변경 이력 (state_history)
       ├─ 조치 기록 (handling_records)
       ├─ AI 분석 결과 (assessment)
       ├─ 메트릭/로그 증거 (metric_log_evidence)
       ├─ 관련 문서 자동 매칭 (키워드 기반)
       └─ 관련 인시던트 매칭

5. AI 분석 요청
   └─▶ GET /api/v1/incident/events/{id}/analysis
       ├─ 재발 패턴 분석 (recurrence_score)
       ├─ 위험도 평가 (risk_score)
       ├─ 추정 원인 도출
       └─ 권장 조치사항 생성

6. 이벤트 문맥 채팅
   └─▶ POST /api/v1/incident/events/{id}/chat
       ├─ 이벤트 정보 + 관련 문서 + 과거 인시던트 참조
       ├─ GPT-4o 기반 답변 생성
       └─ 근거 문서/인시던트 인용 (evidence)

7. 상태 변경 및 조치 기록
   ├─ POST /events/{id}/acknowledge (확인)
   └─ POST /events/{id}/resolve (해결 + 메모)
```

### 문서 처리 워크플로

```
1. 문서 업로드
   └─▶ POST /api/v1/documents
       ├─ 파일 검증 (확장자, 크기, MIME)
       ├─ SHA256 해시 계산
       ├─ MinIO에 파일 저장
       └─ Celery 태스크 큐잉

2. 백그라운드 처리 (Celery Worker)
   └─▶ DocumentProcessor.process()
       ├─ 보호 타입 감지 (암호, DRM, 정책)
       ├─ 텍스트 추출
       ├─ 청크 분할 (1000자, 200자 오버랩)
       └─ 벡터 임베딩 생성

3. 검색 가능 상태
   └─▶ processing_status: READY_FOR_SEARCH
       ├─ 텍스트 기반 검색
       └─ 벡터 기반 시맨틱 검색
```

---

## 5. 실행 방법

### 사전 요구사항

- Docker & Docker Compose (v1.25+ 또는 Docker Compose V2)
- OpenAI API Key (AI 분석/채팅 기능용)

### 환경 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일에서 OPENAI_API_KEY 설정
vi .env
```

### 실행

```bash
# 전체 서비스 빌드 및 실행
docker-compose up --build -d

# 로그 확인
docker-compose logs -f app
```

### 접속

| 서비스 | URL | 설명 |
|--------|-----|------|
| Frontend | http://localhost:3000 | 메인 UI |
| Backend API | http://localhost:8000 | FastAPI 서버 |
| API 문서 | http://localhost:8000/docs | Swagger UI |
| MinIO Console | http://localhost:9001 | 오브젝트 스토리지 관리 (minioadmin/minioadmin) |

### 시드 데이터 적용

시연용 데이터를 넣으려면:

```bash
# 시드 데이터 삽입
docker cp scripts/seed_data.sql msp-archive_postgres_1:/tmp/seed_data.sql
docker exec msp-archive_postgres_1 psql -U postgres -d msp_archive -f /tmp/seed_data.sql
```

시드 데이터에는 2개 고객사, 13대 서버, 18개 이벤트, AI 분석 결과, 조치 이력, 운영 문서, 과거 인시던트가 포함됩니다.

---

## 6. 테스트 방법

### API 테스트 (curl)

```bash
# 헬스 체크
curl http://localhost:8000/health

# 대시보드 조회 (customer_id=1: 한국핀테크)
curl "http://localhost:8000/api/v1/incident/dashboard?customer_id=1"

# 이벤트 목록 (필터링)
curl "http://localhost:8000/api/v1/incident/events?customer_id=1&page=1&page_size=10"

# 심각도별 필터
curl "http://localhost:8000/api/v1/incident/events?customer_id=1&severity=CRITICAL"

# 이벤트 상세 (관련 문서/인시던트 포함)
curl "http://localhost:8000/api/v1/incident/events/1"

# 이벤트 확인 처리
curl -X POST "http://localhost:8000/api/v1/incident/events/1/acknowledge?actor=테스트유저"

# 이벤트 해결 처리
curl -X POST "http://localhost:8000/api/v1/incident/events/1/resolve?actor=테스트유저&resolution_note=테스트해결"
```

### Zabbix 웹훅 테스트

```bash
curl -X POST "http://localhost:8000/api/v1/incident/webhook/zabbix?customer_id=1" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "99999",
    "trigger_name": "Test: High memory usage on web server",
    "trigger_severity": "High",
    "trigger_status": "PROBLEM",
    "host_name": "kfin-web-01",
    "host_ip": "10.10.1.11",
    "event_date": "2026.04.08",
    "event_time": "15:00:00"
  }'
```

### 프론트엔드 시연 시나리오

1. **대시보드 확인**: http://localhost:3000/dashboard
   - KPI 카드 4개 (전체/오픈/크리티컬/오늘해결)
   - 위험도 상위 이벤트 테이블
   - 최근 활동 타임라인

2. **이벤트 목록**: http://localhost:3000/events
   - 심각도/상태 필터 적용
   - 검색어로 이벤트 검색
   - 페이지네이션 동작

3. **이벤트 상세**: 이벤트 목록에서 항목 클릭
   - AI 분석 결과 (위험도, 재발 점수, 추정 원인)
   - 상태 변경 이력 타임라인
   - 조치 기록 목록
   - 관련 문서 (보호 문서는 제한 표시)
   - 관련 인시던트 (과거 유사 장애)
   - 채팅 패널에서 AI와 대화

4. **상태 변경 테스트**:
   - OPEN 이벤트에서 "확인" 버튼 클릭 → ACKNOWLEDGED
   - ACKNOWLEDGED 이벤트에서 "해결" 버튼 클릭 → RESOLVED

### 고객사별 테스트 데이터

| customer_id | 고객사명 | 이벤트 수 | 주요 시나리오 |
|-------------|----------|-----------|--------------|
| 1 | 한국핀테크 | 12건 | DB replication lag, CPU 과부하, Redis 메모리, 배치 실패 |
| 2 | 글로벌이커머스 | 6건 | ES 클러스터 RED, MySQL slow query, Order API 5xx |

---

## 7. 주요 API 엔드포인트

### 인시던트

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/incident/webhook/zabbix` | Zabbix 웹훅 수신 |
| GET | `/api/v1/incident/dashboard` | 대시보드 집계 |
| GET | `/api/v1/incident/events` | 이벤트 목록 (필터/페이지네이션) |
| GET | `/api/v1/incident/events/{id}` | 이벤트 상세 |
| GET | `/api/v1/incident/events/{id}/analysis` | AI 분석 보고서 |
| POST | `/api/v1/incident/events/{id}/chat` | 이벤트 문맥 채팅 |
| POST | `/api/v1/incident/events/{id}/acknowledge` | 이벤트 확인 |
| POST | `/api/v1/incident/events/{id}/resolve` | 이벤트 해결 |

### 문서 관리

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/documents` | 문서 업로드 |
| GET | `/api/v1/documents` | 문서 목록 |
| GET | `/api/v1/documents/{id}` | 문서 상세 |
| GET | `/api/v1/documents/{id}/download` | 문서 다운로드 |
| POST | `/api/v1/documents/{id}/refined` | 정제 문서 업로드 |

### 고객/인프라

| Method | Path | 설명 |
|--------|------|------|
| POST/GET | `/api/v1/customers` | 고객사 관리 |
| POST/GET | `/api/v1/servers` | 서버 관리 |
| POST/GET | `/api/v1/services` | 서비스 관리 |
| GET | `/api/v1/audit/logs` | 감사 로그 |
| GET | `/health` | 헬스 체크 |

---

## 8. 데이터 모델

```
Customer (고객사)
 ├── Server (서버) ─── Service (서비스)
 ├── Document (문서) ─── DocumentChunk (청크)
 ├── EventOccurrence (이벤트)
 │    ├── EventAssessment (AI 분석)
 │    ├── EventStateHistory (상태 이력)
 │    ├── EventHandlingRecord (조치 기록)
 │    └── MetricLogEvidence (증거)
 └── IncidentCase (인시던트)
      └── SanitizedKnowledge (정제 지식)
```
