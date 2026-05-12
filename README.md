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
| **문서 아카이브** | 운영 문서 업로드 → 텍스트 추출 → 청킹 → 벡터 임베딩 → 검색 가능 상태로 자동 처리 |
| **3-Way 하이브리드 검색** | Dense(의미) + Sparse(어휘) + Keyword(PGroonga) 검색을 RRF로 융합 |
| **Adaptive RAG 채팅** | 쿼리 복잡도를 자동 판단하여 single-pass / multi-step 검색 후 AI 답변 생성 |
| **이벤트 대시보드** | 고객사별 이벤트 현황, 심각도 분포, 위험도 상위 이벤트, 최근 조치 이력 |
| **이벤트 관리** | 이벤트 목록/상세/필터링, 상태 변경(확인/해결), 조치 기록 |
| **AI 분석** | Gemini 기반 이벤트 원인 분석, 위험도/재발 점수, 권장 조치사항 |
| **이벤트 채팅** | 이벤트 문맥을 이해하는 AI 채팅 (관련 문서/인시던트 참조) |
| **Zabbix 웹훅** | Zabbix 알림을 자동 수집하여 이벤트로 변환 |
| **인시던트 관리** | 과거 장애 이력 관리 및 정제된 지식(KB) 생성 |
| **감사 로그** | 모든 API 호출에 대한 감사 추적 |

---

## 2. 기술 스택

### Backend
- **Framework**: FastAPI (Python 3.11)
- **ORM**: SQLAlchemy 2.x (async)
- **Database**: PostgreSQL 16 + pgvector + PGroonga
- **Vector DB**: pgvector (Dense: `vector(1024)`, Sparse: `sparsevec(250002)`)
- **Keyword Search**: PGroonga (한국어 형태소 분석 지원)
- **Object Storage**: MinIO (S3 호환)
- **Task Queue**: Celery + Redis
- **LLM**: Google Gemini 2.5 Flash (OpenAI-compatible API)
- **Embedding**: BGE-m3 via HuggingFace TEI (Text Embeddings Inference)
  - Dense embedding: 1024차원
  - Sparse embedding: 250,002차원 (어휘 크기)
- **문서 파싱**: PyMuPDF (PDF), python-docx (DOCX), python-pptx (PPTX), openpyxl (XLSX)

### Frontend
- **Framework**: React 19 + TypeScript
- **Build**: Vite 8
- **Styling**: TailwindCSS 4
- **State**: TanStack React Query 5
- **Routing**: React Router 7
- **HTTP**: Axios

### Infrastructure
- **Container**: Docker + Docker Compose (8개 서비스)
- **Reverse Proxy**: Nginx (프론트엔드 서빙 + API 프록시)
- **Document Conversion**: Gotenberg (레거시 포맷 변환용)

---

## 3. 프로젝트 구조

```
msp-archive/
├── app/                              # Backend (FastAPI)
│   ├── main.py                       # FastAPI 앱 초기화, 라우터 등록, 미들웨어
│   ├── api/                          # API 엔드포인트 (라우터)
│   │   ├── customers.py              # 고객사/서버/서비스 CRUD
│   │   ├── documents.py              # 문서 업로드/조회/다운로드 (V1)
│   │   ├── documents_v2.py           # 문서 업로드 V2 (보호감지, 재처리, 감사로그)
│   │   ├── hybrid_search.py          # 하이브리드 검색, 버전 검색, 크로스 검색, RAG
│   │   ├── chat.py                   # AI 채팅 (문서 기반)
│   │   ├── events.py                 # 이벤트 관리 (상태, 이력, 조치)
│   │   ├── incident.py               # 인시던트 대시보드/이벤트/분석/채팅
│   │   ├── email.py                  # 이메일 수집
│   │   ├── auth.py                   # 인증 (JWT)
│   │   ├── search.py                 # 레거시 검색
│   │   └── audit.py                  # 감사 로그 조회
│   ├── services/                     # 비즈니스 로직 계층
│   │   ├── document_processor.py     # 문서 처리 파이프라인 (S3 다운로드→텍스트 추출→청킹→임베딩)
│   │   ├── embedding.py              # TEI 기반 BGE-m3 임베딩 서비스 (Dense + Sparse)
│   │   ├── hybrid_search.py          # 3-Way 하이브리드 검색 (Dense+Sparse+Keyword → RRF 융합)
│   │   ├── search_service.py         # 검색 서비스 (HybridSearchService 레거시 호환)
│   │   ├── agentic_rag.py            # Adaptive RAG 에이전트 (복잡도 판단→멀티스텝 검색→응답 생성)
│   │   ├── chat_agent.py             # 문서 기반 AI 채팅 에이전트
│   │   ├── analysis_service.py       # AI 기반 이벤트 분석/보고서 생성
│   │   ├── event_chat_service.py     # 이벤트 문맥 채팅 서비스
│   │   └── zabbix_service.py         # Zabbix 웹훅 처리 및 이벤트 변환
│   ├── models/                       # SQLAlchemy ORM 모델
│   │   ├── document.py               # Document, DocumentChunk(pgvector), DocumentRelation
│   │   ├── customer.py               # Customer, Server, Service
│   │   ├── event.py                  # EventOccurrence, Assessment, IncidentCase
│   │   ├── audit.py                  # AuditLog, SanitizedKnowledge
│   │   ├── enums.py                  # 열거형 (EventSeverity, ProcessingStatus 등)
│   │   └── associations.py           # 다대다 관계 테이블
│   ├── schemas/                      # Pydantic 요청/응답 스키마
│   │   ├── document.py               # 문서 관련 스키마
│   │   ├── search.py                 # 검색 요청/응답 (HybridSearchRequest/Response)
│   │   ├── ai.py                     # AI 채팅 관련 스키마
│   │   ├── incident.py               # 인시던트/이벤트 스키마
│   │   └── customer.py               # 고객사 스키마
│   ├── core/                         # 공통 인프라
│   │   ├── config.py                 # 환경 설정 (Pydantic Settings)
│   │   ├── database.py               # DB 엔진/세션 팩토리
│   │   ├── storage.py                # S3/MinIO 스토리지 클라이언트
│   │   └── audit.py                  # 감사 로깅
│   └── workers/                      # Celery 비동기 작업
│       ├── celery_app.py             # Celery 설정
│       └── tasks.py                  # 문서 처리, 이벤트 분석 태스크
├── frontend/                         # Frontend (React + Vite)
│   ├── src/
│   │   ├── App.tsx                   # 라우팅 정의
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx     # 대시보드 (KPI, 위험도 순위, 최근 활동)
│   │   │   ├── DocumentPage.tsx      # 문서 관리 (검색/채팅/업로드/목록)
│   │   │   ├── EventListPage.tsx     # 이벤트 목록 (필터, 페이지네이션)
│   │   │   └── EventDetailPage.tsx   # 이벤트 상세 (분석, 이력, 채팅)
│   │   ├── api/
│   │   │   ├── client.ts             # Axios API 클라이언트 (인시던트)
│   │   │   └── archive-client.ts     # 문서/검색/RAG API 클라이언트
│   │   ├── components/Layout.tsx     # 사이드바 + 헤더 레이아웃
│   │   └── types/incident.ts         # TypeScript 타입 정의
│   ├── nginx.conf                    # Nginx 설정 (SPA + API 프록시)
│   └── Dockerfile                    # 멀티스테이지 빌드 (Node→Nginx)
├── samples/                          # 시연용 샘플 PDF 문서 (5건)
├── scripts/
│   ├── init_db.py                    # DB 테이블 생성 스크립트
│   ├── seed_data.sql                 # 시연용 시드 데이터
│   ├── seed_minio.py                 # MinIO 초기화
│   ├── generate_sample_pdfs.py       # 샘플 PDF 생성 스크립트
│   └── run.sh                        # 실행 스크립트
├── docs/                             # 프로젝트 문서
│   ├── PRD.md                        # 제품 요구사항 문서
│   ├── ARCHITECTURE.md               # 아키텍처 문서
│   ├── EXECUTION_GUIDE.md            # 실행 가이드
│   └── GAP_ANALYSIS_PRD_v1.6.md      # PRD vs 구현 갭 분석
├── docker-compose.yml                # 8개 서비스 오케스트레이션
├── Dockerfile                        # Backend Docker 이미지
├── pyproject.toml                    # Python 의존성 (Poetry)
└── requirements.txt                  # Python 의존성 (pip)
```

---

## 4. 실행 방법

### 사전 요구사항

- Docker & Docker Compose (v1.25+ 또는 Docker Compose V2)
- Gemini API Key (AI 분석/채팅 기능용)

### 환경 설정

```bash
# 1. 저장소 클론
git clone https://github.com/woojoongkim-sour/wjkim.git
cd wjkim

# 2. .env 파일 생성
cp .env.example .env

# 3. .env 파일에서 Gemini API Key 설정
vi .env
# GEMINI_API_KEY=your-gemini-api-key-here
```

#### .env 주요 설정값

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `GEMINI_API_KEY` | (필수) | Google Gemini API 키 |
| `GEMINI_MODEL` | `gemini-2.0-flash` | 사용할 Gemini 모델 |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL 접속 URL |
| `S3_ENDPOINT_URL` | `http://localhost:9000` | MinIO 접속 URL |
| `EMBEDDING_API_URL` | `http://localhost:8080` | BGE-m3 TEI 서비스 URL |
| `CHUNK_SIZE` | `1000` | 문서 청크 크기 (문자 수) |
| `CHUNK_OVERLAP` | `200` | 청크 간 오버랩 (문자 수) |

### 실행

```bash
# 전체 서비스 빌드 및 실행 (8개 서비스)
docker-compose up --build -d

# 서비스 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f app
```

### Docker Compose 서비스 구성 (8개)

| 서비스 | 이미지 | 포트 | 역할 |
|--------|--------|------|------|
| `postgres` | PostgreSQL 16 + pgvector + PGroonga | 5432 | 메인 DB + 벡터 DB + 전문 검색 |
| `minio` | MinIO | 9000, 9001 | 파일 스토리지 (S3 호환) |
| `redis` | Redis 7 | 6379 | 캐시 + Celery 브로커 |
| `embedding` | HuggingFace TEI (BGE-m3) | 8080 | 임베딩 서비스 (Dense + Sparse) |
| `gotenberg` | Gotenberg 8 | 3001 | 문서 포맷 변환 |
| `app` | FastAPI | 8000 | 백엔드 API 서버 |
| `celery` | Celery Worker | - | 비동기 문서 처리 |
| `frontend` | React + Nginx | 3000 | 프론트엔드 UI |

### 접속

| 서비스 | URL | 설명 |
|--------|-----|------|
| Frontend | http://localhost:3000 | 메인 UI |
| Backend API | http://localhost:8000 | FastAPI 서버 |
| API 문서 (Swagger) | http://localhost:8000/docs | API 테스트 |
| MinIO Console | http://localhost:9001 | 오브젝트 스토리지 관리 (minioadmin/minioadmin) |

### 시드 데이터 적용 (선택)

```bash
# 시드 데이터 삽입 (2개 고객사, 13대 서버, 18개 이벤트 등)
docker cp scripts/seed_data.sql msp-archive_postgres_1:/tmp/seed_data.sql
docker exec msp-archive_postgres_1 psql -U postgres -d msp_archive -f /tmp/seed_data.sql
```

---

## 5. 기능 상세 설명

### 5.1 문서 관리

- **업로드**: PDF, DOCX, DOC, TXT, PPTX, XLSX, HWP 등 지원 (최대 100MB)
- **보호 문서 감지**: 암호/DRM 보호 문서 자동 감지, 수동 정제(Refined) 업로드 지원
- **버전 관리**: 동일 문서의 버전 이력 관리 (`version_group_id` 기반)
- **중복 감지**: SHA-256 해시 기반 파일 중복 체크
- **재처리**: 실패한 문서 재처리 요청

### 5.2 3-Way 하이브리드 검색

세 가지 검색 채널을 병렬 실행하고 RRF(Reciprocal Rank Fusion)로 융합합니다:

| 채널 | 모델/엔진 | 가중치 | 특성 |
|------|-----------|--------|------|
| **Dense** | BGE-m3 (1024d) via pgvector | 0.5 | 의미적 유사도 (코사인 거리) |
| **Sparse** | BGE-m3 (250k vocab) via pgvector sparsevec | 0.3 | 어휘적 유사도 (BM25 대안) |
| **Keyword** | PGroonga | 0.2 | 정확 키워드 매칭 (한국어 형태소 분석) |

- **RRF K=60**: `score = 0.5/(rank_dense+60) + 0.3/(rank_sparse+60) + 0.2/(rank_keyword+60)`
- **Dense Threshold**: Dense 스코어 0.4 미만 시 escalation 트리거
- **버전 검색**: 특정 시점 기준으로 유효했던 문서 버전만 검색
- **크로스 검색**: 모든 고객사 문서에서 유사 사례 검색

### 5.3 Adaptive RAG (Agentic 검색)

쿼리 복잡도에 따라 검색 전략을 자동 선택합니다:

```
Simple Query ("김 대리 전화번호?")
 → single-pass 검색 → 즉시 답변

Complex Query ("지난 3개월간 DB 장애 패턴과 대응 방법 비교")
 → 쿼리 분해 → multi-step 검색 → 결과 통합 → AI 답변 생성
```

- **복잡도 분석**: Gemini가 쿼리를 분석하여 simple/complex 판정
- **쿼리 분해**: 복잡 쿼리를 검색 친화적인 서브쿼리로 분해
- **Fallback**: 초기 검색 결과 불충분 시 자동으로 cross-search 시도
- **최대 Tool Call**: 5회 (설정 가능)

### 5.4 AI 채팅

- **문서 기반 채팅**: 검색된 문서 컨텍스트를 포함한 AI 답변
- **이벤트 문맥 채팅**: 이벤트 정보 + 관련 문서 + 과거 인시던트를 참조하는 채팅
- **근거 표시**: 답변에 사용된 문서/인시던트 출처 표시
- **보호 문서 제한 안내**: 보호된 문서는 메타데이터만 활용됨을 명시

### 5.5 이벤트/인시던트 관리

- **Zabbix 웹훅**: Zabbix 알림을 자동 수집하여 이벤트로 변환
- **AI 분석**: 재발 패턴 분석, 위험도 평가, 추정 원인, 권장 조치사항
- **상태 관리**: OPEN → ACKNOWLEDGED → RESOLVED 워크플로
- **인시던트 연계**: 고위험 이벤트의 인시던트 전환 자동 제안

---

## 6. 업무 로직 및 플로우

### 6.1 전체 아키텍처

```
┌────────────────────────────────────────────────────────────────┐
│                      Docker Compose (8 services)               │
│                                                                │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ Frontend │───▶│    Nginx     │───▶│     FastAPI App      │  │
│  │ React/TS │    │  (port 3000) │    │     (port 8000)      │  │
│  └──────────┘    └──────────────┘    └──────────┬───────────┘  │
│                        /api/*                   │              │
│                       프록시                     │              │
│                                                 │              │
│  ┌──────────┐    ┌──────────────┐    ┌──────────▼───────────┐  │
│  │  Celery  │◀──▶│    Redis     │    │    PostgreSQL 16     │  │
│  │  Worker  │    │  (port 6379) │    │    + pgvector        │  │
│  └────┬─────┘    └──────────────┘    │    + PGroonga        │  │
│       │                              │    (port 5432)       │  │
│       │                              └──────────────────────┘  │
│       │                                                        │
│       │          ┌──────────────┐    ┌──────────────────────┐  │
│       └─────────▶│    MinIO     │    │   HuggingFace TEI    │  │
│                  │ (port 9000)  │    │   BGE-m3 Embedding   │  │
│                  └──────────────┘    │   (port 8080)        │  │
│                                      └──────────────────────┘  │
│                  ┌──────────────┐                               │
│                  │  Gotenberg   │                               │
│                  │ (port 3001)  │                               │
│                  └──────────────┘                               │
└────────────────────────────────────────────────────────────────┘
         ▲                              ▲
         │ Webhook (POST)               │ Dense + Sparse Embedding
┌────────┴────────┐              ┌──────┴──────────┐
│  Zabbix Server  │              │  Gemini API     │
│  (이벤트 수집)   │              │  (LLM 분석/채팅) │
└─────────────────┘              └─────────────────┘
```

### 6.2 문서 업로드 → 임베딩/청킹 저장 → 검색 → 답변 전체 플로우

이 플랫폼의 핵심 워크플로입니다. 문서가 업로드되면 자동으로 검색 가능한 상태까지 처리됩니다.

#### Phase 1: 문서 업로드

```
사용자 (Frontend DocumentPage)
  │
  ▼
POST /api/v1/documents
  │  title, document_type, customer_id, file (multipart/form-data)
  │
  ▼
[documents.py] upload_document()
  ├── 1. 파일 내용 읽기 (await file.read())
  ├── 2. SHA-256 해시 계산 (중복 감지용)
  ├── 3. MinIO에 원본 파일 저장
  │      └── S3Storage.upload_file() → "customers/{id}/original/{filename}"
  ├── 4. Document 레코드 생성 (DB)
  │      ├── processing_status = UPLOADED
  │      ├── protection_type = NONE
  │      └── 메타데이터 저장 (파일명, 크기, MIME, 해시 등)
  └── 5. 백그라운드 처리 태스크 큐잉
         └── BackgroundTasks.add_task(_process_document_background)
             또는 Celery: process_document_task.delay(document_id)
```

#### Phase 2: 텍스트 추출 (백그라운드)

```
[document_processor.py] DocumentProcessor.process(document_id)
  │
  ├── 1. DB에서 Document 조회
  ├── 2. 수동 정제본(ManualRefinedDocument) 존재 여부 확인
  │      └── 있으면 → status=REFINED_UPLOADED, 종료
  │
  ├── 3. S3에서 원본 파일 다운로드
  │      └── S3Storage.download_file(document.file_path)
  │
  └── 4. MIME 타입에 따른 텍스트 추출
         ├── PDF  → _extract_pdf()  : PyMuPDF(fitz) 페이지별 텍스트 추출
         ├── DOCX → _extract_docx() : python-docx 패러그래프 추출
         ├── TXT  → _extract_text() : UTF-8/EUC-KR/CP949 자동 감지
         └── 기타 → 텍스트 디코딩 시도
         
         텍스트 추출 실패 시:
         └── status = AWAITING_MANUAL_REFINEMENT (수동 정제 필요)
```

#### Phase 3: 청킹 (Chunking)

```
[document_processor.py] _chunk_content(content)
  │
  ├── chunk_size = 1000자 (설정: CHUNK_SIZE)
  ├── overlap = 200자 (설정: CHUNK_OVERLAP)
  │
  └── 슬라이딩 윈도우 방식으로 분할:
      
      원본 텍스트 (3000자):
      ├── Chunk 0: [0 ~ 1000]      (1000자)
      ├── Chunk 1: [800 ~ 1800]    (1000자, 200자 오버랩)
      ├── Chunk 2: [1600 ~ 2600]   (1000자, 200자 오버랩)
      └── Chunk 3: [2400 ~ 3000]   (600자, 나머지)
      
      → 문맥 연속성을 위해 200자씩 겹침
```

#### Phase 4: 벡터 임베딩 생성 및 저장

```
[document_processor.py] _create_chunks_with_embeddings()
  │
  ├── 배치 처리 (batch_size = 32)
  │
  └── 각 배치에 대해:
      │
      ├── [embedding.py 또는 _get_embeddings()]
      │   │
      │   ├── Dense Embedding 요청
      │   │   POST http://embedding:8080/embed
      │   │   Body: {"inputs": ["chunk text 1", "chunk text 2", ...], "truncate": true}
      │   │   Response: [[0.012, -0.034, ...], ...]  (1024차원 벡터)
      │   │
      │   └── Sparse Embedding 요청
      │       POST http://embedding:8080/embed_sparse
      │       Body: {"inputs": ["chunk text 1", ...], "truncate": true}
      │       Response: [[{"index": 1234, "value": 0.56}, ...], ...]
      │       → SPARSEVEC 형식으로 변환: "{1234:0.56, 5678:0.34}/250002"
      │
      └── DocumentChunk 레코드 생성 (DB)
          ├── document_id, customer_id (비정규화)
          ├── document_title (PGroonga 검색용 비정규화)
          ├── content (청크 텍스트)
          ├── chunk_index (순서)
          ├── dense_vector  → Vector(1024)     : pgvector 컬럼
          └── sparse_vector → SPARSEVEC(250002) : pgvector 컬럼

처리 완료:
  └── Document.processing_status = READY_FOR_SEARCH
```

#### Phase 5: 하이브리드 검색

```
사용자 검색 요청
  │
  ▼
POST /api/v1/search/hybrid
  │  {"query": "PostgreSQL 장애 대응", "customer_id": 1}
  │
  ▼
[hybrid_search.py] HybridSearchService.search()
  │
  ├── 1. 유효 문서 ID 필터링
  │      ├── customer_id 기준
  │      ├── is_active = True
  │      └── is_latest = True (버전 관리)
  │
  ├── 2. 쿼리 임베딩 생성
  │      └── EmbeddingService.encode(["PostgreSQL 장애 대응"])
  │          → dense_vector (1024d) + sparse_vector (250002d)
  │
  ├── 3. 3-Way 병렬 검색 실행
  │      │
  │      ├── [Dense Search] (pgvector cosine distance)
  │      │   SELECT id, (dense_vector <=> query_vector::vector) AS score
  │      │   FROM document_chunks
  │      │   WHERE document_id = ANY(valid_ids)
  │      │   ORDER BY score LIMIT 100
  │      │
  │      ├── [Sparse Search] (pgvector sparsevec distance)
  │      │   SELECT id, (sparse_vector <=> query_sparse::sparsevec) AS score
  │      │   FROM document_chunks
  │      │   WHERE document_id = ANY(valid_ids)
  │      │   ORDER BY score LIMIT 100
  │      │
  │      └── [Keyword Search] (PGroonga full-text)
  │          SELECT id, pgroonga_score() AS score
  │          FROM document_chunks
  │          WHERE content &@~ 'PostgreSQL 장애 대응'
  │          ORDER BY score LIMIT 100
  │
  ├── 4. RRF (Reciprocal Rank Fusion) 융합
  │      각 채널에서 chunk의 순위(rank)를 추출하고 가중 RRF 계산:
  │      final_score = 0.5/(rank_dense+60) + 0.3/(rank_sparse+60) + 0.2/(rank_keyword+60)
  │
  ├── 5. 결과 정렬 및 반환
  │      ├── final_score 내림차순 정렬
  │      ├── Dense score < 0.4 → escalation_triggered = true
  │      └── 상위 N개 결과 반환 (기본 20개)
  │
  └── Response:
      {
        "results": [
          {
            "chunk_id": 42,
            "document_id": 5,
            "document_title": "PostgreSQL 운영 가이드",
            "content": "장애 발생 시 먼저 pg_stat_activity를 확인하여...",
            "score": 0.0125,
            "dense_score": 0.82,
            "sparse_score": 0.45,
            "keyword_score": 3.2
          }, ...
        ],
        "total": 15,
        "search_mode": "single-pass",
        "escalation_triggered": false
      }
```

#### Phase 6: Adaptive RAG → AI 답변 생성

```
사용자 질문
  │
  ▼
POST /api/v1/search/rag
  │  query="PostgreSQL 장애 대응 절차 알려줘", customer_id=1
  │
  ▼
[agentic_rag.py] AdaptiveRAGOrchestrator.process()
  │
  ├── 1. 복잡도 분석 (Gemini LLM)
  │      └── analyze_complexity(query)
  │          → "simple" (단일 검색으로 충분) 또는 "complex" (멀티스텝 필요)
  │
  ├── [Simple Path]
  │   ├── 2a. single_pass_search()
  │   │       └── HybridSearchService.search(query, customer_id)
  │   │
  │   ├── 3a. Dense score >= 0.4 → 충분한 결과
  │   │       └── 검색 결과를 컨텍스트로 Gemini에 전달 → 답변 생성
  │   │
  │   └── 3b. Dense score < 0.4 → 불충분 → multi-step으로 전환
  │
  ├── [Complex Path]
  │   ├── 2b. 쿼리 분해 (_decompose_query)
  │   │       "PostgreSQL 장애 대응 절차 알려줘"
  │   │       → ["PostgreSQL 장애 유형", "장애 대응 절차", "복구 명령어"]
  │   │
  │   ├── 3b. 각 서브쿼리로 hybrid_search 실행 (최대 5회)
  │   │       ├── Search 1: "PostgreSQL 장애 유형" → 결과 수집
  │   │       ├── Search 2: "장애 대응 절차" → 결과 수집
  │   │       └── Search 3: "복구 명령어" → 결과 수집
  │   │
  │   ├── 4b. 결과 불충분 시 Fallback
  │   │       └── cross_search (전체 고객사 대상 검색)
  │   │
  │   └── 5b. 수집된 모든 컨텍스트로 최종 답변 생성
  │
  └── 6. Gemini LLM 최종 응답 생성
         ├── System: MSP 운영 전문가 역할
         ├── Context: 검색된 문서 청크들 (제목, 내용)
         ├── User: 원래 질문
         └── Response: 근거 문서를 인용한 한국어 답변
```

#### 전체 End-to-End 요약

```
[업로드]                    [처리]                      [검색/답변]
                                                        
사용자가 PDF 업로드         백그라운드 자동 처리          사용자가 질문 입력
    │                          │                            │
    ▼                          ▼                            ▼
MinIO에 원본 저장 ──────▶ PyMuPDF로 텍스트 추출     쿼리 임베딩 생성 (BGE-m3)
    │                          │                            │
    ▼                          ▼                            ▼
Document 레코드 생성      1000자 단위 청킹           3-Way 병렬 검색
    │                    (200자 오버랩)              (Dense+Sparse+Keyword)
    ▼                          │                            │
Celery 태스크 큐잉             ▼                            ▼
                         BGE-m3 임베딩 생성           RRF 융합 (가중 순위 합산)
                         (Dense 1024d +                     │
                          Sparse 250Kd)                     ▼
                               │                    Adaptive RAG 판단
                               ▼                    (simple/complex)
                         DocumentChunk 저장                  │
                         (pgvector 컬럼)                     ▼
                               │                    Gemini LLM 답변 생성
                               ▼                    (검색 컨텍스트 + 질문)
                         READY_FOR_SEARCH                   │
                                                            ▼
                                                    근거 기반 한국어 답변 반환
```

### 6.3 이벤트 처리 워크플로

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

4. AI 분석 요청
   └─▶ GET /api/v1/incident/events/{id}/analysis
       ├─ 재발 패턴 분석 (7일/30일 집계 → recurrence_score)
       ├─ 유사 인시던트/문서 검색
       ├─ Gemini 기반 원인 분석 (JSON 구조화 응답)
       ├─ 위험도 평가 (risk_score 0-100)
       └─ 권장 조치사항 생성

5. 이벤트 문맥 채팅
   └─▶ POST /api/v1/incident/events/{id}/chat
       ├─ 이벤트 정보 + 관련 문서 + 과거 인시던트 + 정제 지식 참조
       ├─ Gemini 기반 답변 생성
       └─ 근거 문서/인시던트 인용 (evidence)

6. 상태 변경 및 조치 기록
   ├─ POST /events/{id}/acknowledge (확인)
   └─ POST /events/{id}/resolve (해결 + 메모)
```

---

## 7. 주요 API 엔드포인트

### 검색/RAG

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/search/hybrid` | 3-Way 하이브리드 검색 |
| POST | `/api/v1/search/version` | 특정 시점 기준 버전 검색 |
| POST | `/api/v1/search/cross` | 전체 고객사 대상 크로스 검색 |
| POST | `/api/v1/search/rag` | Adaptive RAG (복잡도 기반 라우팅 → AI 답변) |
| GET | `/api/v1/search/health` | 검색 서비스 헬스체크 |

### 문서 관리

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/documents` | 문서 업로드 (자동 처리 시작) |
| GET | `/api/v1/documents` | 문서 목록 (필터/페이지네이션) |
| GET | `/api/v1/documents/{id}` | 문서 상세 |
| PUT | `/api/v1/documents/{id}` | 문서 수정 |
| DELETE | `/api/v1/documents/{id}` | 문서 삭제 (soft delete) |
| GET | `/api/v1/documents/{id}/download` | 문서 다운로드 (presigned URL) |
| POST | `/api/v1/documents/{id}/refined` | 수동 정제 문서 업로드 |
| GET | `/api/v1/documents/{id}/refined` | 정제 문서 목록 |
| POST | `/api/v1/documents-v2/{id}/reprocess` | 문서 재처리 요청 |

### 인시던트/이벤트

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/incident/webhook/zabbix` | Zabbix 웹훅 수신 |
| GET | `/api/v1/incident/dashboard` | 대시보드 집계 |
| GET | `/api/v1/incident/events` | 이벤트 목록 |
| GET | `/api/v1/incident/events/{id}` | 이벤트 상세 |
| GET | `/api/v1/incident/events/{id}/analysis` | AI 분석 보고서 |
| POST | `/api/v1/incident/events/{id}/chat` | 이벤트 문맥 채팅 |
| POST | `/api/v1/incident/events/{id}/acknowledge` | 이벤트 확인 |
| POST | `/api/v1/incident/events/{id}/resolve` | 이벤트 해결 |

### 기타

| Method | Path | 설명 |
|--------|------|------|
| POST/GET | `/api/v1/customers` | 고객사 관리 |
| POST/GET | `/api/v1/servers` | 서버 관리 |
| GET | `/api/v1/audit/logs` | 감사 로그 |
| GET | `/health` | 헬스 체크 |

---

## 8. 데이터 모델

```
Customer (고객사)
 ├── Server (서버) ─── Service (서비스)
 ├── Document (문서)
 │    ├── DocumentChunk (청크)
 │    │    ├── dense_vector  : Vector(1024)      ← BGE-m3 Dense
 │    │    └── sparse_vector : SPARSEVEC(250002) ← BGE-m3 Sparse
 │    ├── ManualRefinedDocument (수동 정제본)
 │    ├── DocumentProcessingAttempt (처리 이력)
 │    └── DocumentRelation (문서 관계)
 ├── EventOccurrence (이벤트)
 │    ├── EventAssessment (AI 분석)
 │    ├── EventStateHistory (상태 이력)
 │    ├── EventHandlingRecord (조치 기록)
 │    └── MetricLogEvidence (증거)
 └── IncidentCase (인시던트)
      └── SanitizedKnowledge (정제 지식)

DocumentCategory (문서 카테고리) ─── Document
```

---

## 9. 테스트 방법

### API 테스트 (curl)

```bash
# 헬스 체크
curl http://localhost:8000/health

# 문서 업로드
curl -X POST http://localhost:8000/api/v1/documents \
  -F "title=PostgreSQL 운영 가이드" \
  -F "document_type=operation_manual" \
  -F "customer_id=1" \
  -F "file=@samples/03_PostgreSQL_운영_가이드.pdf"

# 하이브리드 검색
curl -X POST http://localhost:8000/api/v1/search/hybrid \
  -H "Content-Type: application/json" \
  -d '{"query": "PostgreSQL 장애 대응", "customer_id": 1}'

# RAG 채팅
curl -X POST "http://localhost:8000/api/v1/search/rag?query=PostgreSQL+장애+대응+절차&customer_id=1"

# 대시보드 조회
curl "http://localhost:8000/api/v1/incident/dashboard?customer_id=1"

# 이벤트 목록
curl "http://localhost:8000/api/v1/incident/events?customer_id=1&page=1&page_size=10"
```

### 프론트엔드 시연

1. **문서 업로드**: http://localhost:3000/documents → 업로드 탭
2. **문서 검색**: http://localhost:3000/documents → 검색 & 채팅 탭
3. **AI 채팅**: 같은 페이지에서 질문 입력 → RAG 기반 답변 확인
4. **대시보드**: http://localhost:3000/dashboard
5. **이벤트 관리**: http://localhost:3000/events
