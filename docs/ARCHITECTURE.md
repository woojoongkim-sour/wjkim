# MSP Archive Platform - Architecture Document

**문서 버전**: 1.0
**작성일**: 2026-04-15

---

## 1. 아키텍처 개요

MSP Archive Platform은 마이크로서비스 아키텍처를 채택하지 않고, 모놀리식 구조를 기본으로 하되 비동기 처리를 위해 Celery 워커를 분리한 하이브리드架构이다.

```
┌──────────────────────────────────────────────────────────────────────┐
│                          Docker Compose                               │
│                                                                      │
│  ┌───────────┐   HTTP/SSE   ┌────────────────────┐                   │
│  │  Next.js  │─────────────▶│   FastAPI API       │                  │
│  │  (프론트) │◀─────────────│   + OpenAI GPT-4o  │                  │
│  │  :80      │  streaming   │   :8000             │                  │
│  └───────────┘              └──┬────┬────┬────────┘                  │
│                                │    │    │                           │
│                    ┌───────────┘    │    └───────────┐               │
│                    ▼                ▼                ▼               │
│             ┌──────────┐    ┌────────────┐   ┌─────────────┐        │
│             │  Redis   │    │ PostgreSQL │   │  Embedding  │        │
│             │  :6379   │    │  :5432     │   │  (BGE-m3)   │        │
│             │          │    │            │   │  :8080      │        │
│             │ - 작업 큐 │    │ - pgvector │   │             │        │
│             │ - 캐시   │    │ - PGroonga │   │ HuggingFace │        │
│             └────┬─────┘    │ - Apache AGE│   │ TEI         │        │
│                  │          └─────┬──────┘   └──────┬──────┘        │
│                  ▼                │                  │               │
│          ┌───────────────┐       │                  │               │
│          │  Celery Worker│───────┴──────────────────┘               │
│          │               │                                          │
│          │ - 문서 파싱    │       ┌──────────────┐                   │
│          │ - 임베딩 생성  │──────▶│  Gotenberg   │                   │
│          │ - IMAP 수집   │       │  :3000       │                   │
│          │ - 스케줄러    │       │              │                   │
│          └───────────────┘       │ .doc → .docx │                   │
│                                  └──────────────┘                   │
│                                                                      │
│  ┌──────────────┐                                                    │
│  │  MinIO       │  ← S3 호환 오브젝트 스토리지                        │
│  │  :9000       │                                                    │
│  └──────────────┘                                                    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. 컴포넌트 상세

### 2.1 API Server (FastAPI)

**역할:**
- RESTful API 엔드포인트 제공
- 인증/인가 처리
- SSE (Server-Sent Events) 스트리밍
- 문서 업로드 수신 및 스토리지 연동

**주요 디렉토리:**
```
app/
├── api/                    # API 라우터
│   ├── auth.py            # JWT 인증
│   ├── documents.py       # 문서 CRUD
│   ├── documents_v2.py    # 문서 버전/중복检测
│   ├── hybrid_search.py    # 3-way 검색 API
│   ├── email.py           # IMAP 관리 API
│   ├── chat.py            # 채팅 API
│   ├── events.py          # 이벤트 API
│   └── incident.py        # 장애 보고 API
├── models/                # SQLAlchemy 모델
│   ├── document.py       # Document, DocumentChunk
│   ├── customer.py        # Customer, Server, Service
│   ├── user.py           # User, UserSession
│   ├── email.py          # ImapAccount, CollectedEmail
│   └── event.py          # IncidentCase, EventOccurrence
├── services/              # 비즈니스 로직
│   ├── hybrid_search.py  # 3-way RRF 검색
│   ├── agentic_rag.py    # Adaptive RAG Agent
│   ├── graph_service.py  # Apache AGE 연동
│   ├── email_collector.py # IMAP 수집
│   ├── auth.py           # JWT 인증 서비스
│   └── document_processor.py
├── core/
│   ├── config.py         # 설정 관리
│   ├── database.py       # DB 연결
│   └── storage.py        # S3 스토리지
└── main.py               # FastAPI 앱
```

### 2.2 Celery Worker

**역할:**
- 문서 파싱 (PDF, DOCX, HWP 등)
- 청킹 및 섹션 추출
- 임베딩 생성 (BGE-m3 TEI)
- IMAP 이메일 수집 스케줄러
- 문서 처리 파이프라인 Orchestration

**Task Chain:**
```python
parse_document → chunk_document → embed_chunks → finalize_document
```

### 2.3 PostgreSQL + Extensions

**확장:**
- **pgvector**: Dense + Sparse 벡터 저장 및 유사도 검색
- **PGroonga**: 한국어 전문 검색 (形態素解析)
- **Apache AGE**: 그래프 데이터 처리 (선택적)

**핵심 테이블:**
```sql
documents              -- 문서 메타데이터
document_chunks        -- 청크 + 벡터 (1024차원 dense, sparse)
customers              -- 고객사
servers                -- 서버
services               -- 서비스
users                  -- 사용자
imap_accounts          -- IMAP 계정
collected_emails       -- 수집된 이메일
incident_cases         -- 장애 인시던트
audit_logs             -- 감사 로그
```

### 2.4 BGE-m3 Embedding Service

**모델:** BAAI/bge-m3
- Dense Embedding: 1024차원
- Sparse Embedding: 어휘 가중치
- 최대 입력: 8,192 토큰
- 한국어 지원: Excellent

**API:**
```python
POST /embed
{
  "inputs": ["text1", "text2"],
  "truncate": true
}
Response:
{
  "dense_embeddings": [[...], [...]],
  "sparse_embeddings": [[...], [...]]
}
```

### 2.5 Frontend (React/Next.js)

**구성:**
```
frontend/
├── src/
│   ├── api/
│   │   ├── client.ts        # 기존 incident API
│   │   └── archive-client.ts # 신규 문서/검색 API
│   ├── pages/
│   │   ├── DashboardPage.tsx
│   │   ├── DocumentPage.tsx  # 신규: 문서 관리 UI
│   │   ├── EventListPage.tsx
│   │   └── EventDetailPage.tsx
│   ├── components/
│   │   └── Layout.tsx
│   ├── types/
│   └── App.tsx
├── Dockerfile
└── nginx.conf
```

---

## 3. 데이터 흐름

### 3.1 문서 처리 파이프라인

```
[1] 업로드
    User → Frontend → POST /api/v1/documents
        │
        ├─ SHA-256 해시 계산
        ├─ MinIO에 파일 저장
        ├─ documents 테이블 INSERT (status=PENDING)
        └─ Celery Task 등록

[2] 파싱 (Celery)
    Task: parse_document
        │
        ├─ 파일 형식 감지
        ├─ 레거시 포맷 → Gotenberg 변환
        ├─ 암호화 감지 → 메타만 저장 후 종료
        ├─ 본문 텍스트 추출
        └─ documents.status = PARSED

[3] 청킹 (Celery)
    Task: chunk_document
        │
        ├─ 문단/문장 단위 분할
        ├─ 섹션 제목 추출
        ├─ 1,000자 청크 + 200자 overlap
        ├─ 이메일 → 정규화 해시 생성
        └─ document_chunks 테이블 INSERT

[4] 임베딩 (Celery)
    Task: embed_chunks
        │
        ├─ [문서제목] [섹션제목] 청크내용 조합
        ├─ BGE-m3 TEI API 호출
        ├─ dense + sparse 벡터 저장
        └─ documents.status = INDEXED

[5] Graph 동기화 (선택적)
    Task: sync_to_graph
        │
        ├─ Apache AGE에 노드/관계 생성
        └─ documents.status = COMPLETED
```

### 3.2 검색 파이프라인

```
[1] 질의 분석
    User → Frontend → POST /api/v1/search/rag
        │
        └─ AdaptiveRAGOrchestrator
            │
            ├─ 복잡도 판별 (GPT-4o)
            │   ├─ Simple → Single-pass
            │   └─ Complex → Multi-step
            │
            └─ Single-pass 모드:
                │
                ├─ [2] 3-way 검색
                └─ [3] LLM 응답

[2] 3-way Hybrid Search
    HybridSearchService
        │
        ├─ Dense 검색 (pgvector)
        │   └─ EmbeddingService.encode() → BGE-m3
        │
        ├─ Sparse 검색 (pgvector)
        │   └─ BGE-m3 sparse 가중치
        │
        ├─ Keyword 검색 (PGroonga)
        │   └─ 한국어 형태소 분석
        │
        └─ RRF Fusion
            └─ final = 0.5×dense + 0.3×sparse + 0.2×keyword

[3] LLM 응답 생성
    OpenAI GPT-4o
        │
        ├─ 시스템 프롬프트 (출처 명시 규칙)
        ├─ 검색 결과 컨텍스트
        └─ 구조화된 응답 + 출처 인용
```

### 3.3 이메일 수집 파이프라인

```
[1] 스케줄러 (Celery Beat)
    │
    └─ 15분마다 IMAP 계정 순회

[2] IMAP 수집
    ImapCollector
        │
        ├─ IMAP4_SSL 연결
        ├─邮件 ID 가져오기
        └─ RFC822 파싱

[3] 고객사 분류
    │
    ├─ 이메일 주소 → EmailCustomerMapping
    ├─ 도메인 → EmailCustomerMapping
    ├─ 제목 내 별칭 → CustomerAlias
    └─ 미분류 → unclassified

[4] 중복 제거
    │
    └─ 정규화 SHA-256 해시
        └─ ON CONFLICT DO NOTHING

[5] Graph 동기화
    │
    └─ Apache AGE 노드 생성
```

---

## 4. 보안

### 4.1 인증

```
JWT Access Token (15분)
    └─ user_id, username, role, customer_id

JWT Refresh Token (7일)
    └─ user_id, session_id
```

### 4.2 인가

| 역할 | 권한 |
|------|------|
| admin | 모든 CRUD, 사용자 관리, 시스템 설정 |
| engineer | 문서 CRUD, 검색, 채팅, 이벤트 관리 |
| viewer | 읽기 전용 |

### 4.3 데이터 격리

- 고객사별 데이터 완전히 분리
- 크로스 검색은 명시적 옵션 필요
- Audit Log로 모든 접근 기록

---

## 5. 확장성

### 5.1 수평 확장

| 컴포넌트 | 확장 방식 |
|----------|----------|
| API Server | Kubernetes HPA (CPU/메모리 기반) |
| Celery Worker | Kubernetes HPA (큐 길이 기반) |
| PostgreSQL | 읽기 복제본 추가 |
| Redis | Sentinel 또는 Cluster |

### 5.2 수직 확장

| 컴포넌트 | 현재 사양 | 권장 사양 |
|----------|----------|----------|
| PostgreSQL | 4GB RAM | 16GB+ RAM (벡터 연산) |
| Redis | 512MB | 2GB+ |
| BGE-m3 TEI | CPU | GPU (대량 임베딩 시) |

---

## 6. 모니터링

### 6.1 메트릭

- API 응답 시간 (p50, p95, p99)
- 검색 latency
- 문서 처리 성공/실패율
- Celery Task 소요 시간
- 벡터 검색 품질 점수

### 6.2 로깅

- 구조화된 JSON 로그
- 요청 ID 추적
- 에러 스택 트레이스
- Audit Log (민감操作)

---

## 7. 백업 및 복구

### 7.1 백업 전략

| 데이터 | 주기 | 방법 |
|--------|------|------|
| PostgreSQL | 일별 | pg_dump |
| MinIO | 일별 | mc mirror |
| Redis | 매시 | RDB 스냅샷 |

### 7.2 복구 절차

1. PostgreSQL: `pg_restore`
2. MinIO: `mc cp`
3. Redis: `redis-cli LOADING`

---

## 8. 네트워크 아키텍처

```
Internet
    │
    ├─ :80 (Frontend) ─── :8000 (API)
    │                        │
    │                   ┌────┴────┐
    │                   │         │
    │              :5432      :6379
    │           PostgreSQL    Redis
    │                │
    │           :9000 (MinIO)
    │           :8080 (BGE-m3)
    │           :3000 (Gotenberg)
    │
    └─ :9001 (MinIO Console)
```

---

## 9. 환경 변수

| 변수 | 설명 | 예시 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL 연결 | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis 연결 | `redis://localhost:6379/0` |
| `S3_ENDPOINT_URL` | MinIO endpoint | `http://localhost:9000` |
| `S3_ACCESS_KEY` | MinIO Access Key | `minioadmin` |
| `S3_SECRET_KEY` | MinIO Secret Key | `minioadmin` |
| `EMBEDDING_API_URL` | BGE-m3 TEI | `http://localhost:8080` |
| `OPENAI_API_KEY` | OpenAI API Key | `sk-...` |
| `SECRET_KEY` | JWT Secret | `dev-secret-...` |
