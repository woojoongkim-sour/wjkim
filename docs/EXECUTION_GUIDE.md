# MSP Archive Platform - 실행 가이드

**문서 버전**: 1.0
**작성일**: 2026-04-15

---

## 1. Prerequisites (사전 요구사항)

### 1.1 필수 소프트웨어

| 소프트웨어 | 최소 버전 | 권장 버전 |
|-----------|----------|----------|
| Docker | 24.0+ | Latest |
| Docker Compose | 2.20+ | Latest |
| Git | 2.40+ | Latest |

### 1.2 선택적 소프트웨어

| 소프트웨어 | 용도 |
|-----------|------|
| Python 3.12+ | 로컬 개발 |
| Node.js 20+ | 프론트엔드 개발 |
| Poetry | Python 의존성 관리 |

---

## 2. 빠른 시작 (Quick Start)

### 2.1 저장소 클론

```bash
git clone https://github.com/your-org/msp-archive.git
cd msp-archive
```

### 2.2 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 편집하여 필요한 값을 설정합니다:

```bash
# 필수: OpenAI API Key
OPENAI_API_KEY=sk-your-openai-api-key

# 선택: 외부 서비스 사용 시
# AWS Bedrock (OpenAI 대신)
# AWS_ACCESS_KEY_ID=xxx
# AWS_SECRET_ACCESS_KEY=xxx
# AWS_REGION=ap-northeast-2
```

### 2.3 Docker Compose로 실행

```bash
# 모든 서비스 시작 (백그라운드)
docker-compose up -d

# 서비스 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f app
```

### 2.4 초기 데이터 시딩

```bash
# 데이터베이스 초기화 및 시딩 데이터 로드
docker-compose exec postgres psql -U postgres -d msp_archive -f /docker-entrypoint-initdb.d/01-init.sql

# MinIO 버킷 생성 및 샘플 데이터 업로드
docker-compose exec app python scripts/seed_minio.py
```

### 2.5 접속

| 서비스 | URL |
|--------|-----|
| 프론트엔드 | http://localhost:3000 |
| API 문서 | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |

**기본 계정:**
- Username: `admin`
- Password: `admin123` (실제 환경에서는 변경 필요)

---

## 3. 서비스 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Network                          │
│                                                              │
│  ┌──────────────┐                                           │
│  │   frontend   │  :3000 (or :80)                          │
│  │   (nginx)    │                                           │
│  └──────┬───────┘                                           │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────┐                                           │
│  │     app      │  :8000                                    │
│  │   (FastAPI)  │◀──────▶ OpenAI API                       │
│  └──────┬───────┘                                           │
│         │                                                   │
│  ┌──────┴───────┬───────────────┬───────────────┐            │
│  ▼              ▼               ▼               ▼            │
│ ┌────────┐  ┌────────┐   ┌──────────┐  ┌────────┐         │
│ │postgres │  │ redis  │   │  minio   │  │embedding│         │
│ │ :5432   │  │ :6379  │   │ :9000/9001│  │ :8080  │         │
│ └────────┘  └────────┘   └──────────┘  └────────┘         │
│                     │                                       │
│              ┌───────┴───────┐                               │
│              ▼               ▼                               │
│         ┌────────┐     ┌──────────┐                         │
│         │celery  │     │gotenberg │                         │
│         │worker  │     │  :3000   │                         │
│         └────────┘     └──────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 서비스별 상세 설정

### 4.1 PostgreSQL

**포트:** 5432
**기본 데이터베이스:** msp_archive

**확장:**
- `pgvector`: 벡터 저장 및 검색
- `pgroonga`: 한국어 전문 검색

**초기화 스크립트:**
```bash
# /docker/postgres/init.sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgroonga;
```

**pgroonga 인덱스 생성:**
```sql
-- PostgreSQL 재시작 후 실행
CREATE EXTENSION pgroonga;

-- document_chunks에 PGroonga 인덱스 생성
CREATE INDEX idx_chunks_pgroonga ON document_chunks 
USING pgroonga (content, document_title, section_title);
```

### 4.2 Redis

**포트:** 6379
**용도:**
- Celery 브로커 (`redis://redis:6379/1`)
- Celery 결과 백엔드 (`redis://redis:6379/2`)
- 캐시 (`redis://redis:6379/0`)

### 4.3 MinIO

**포트:**
- API: 9000
- Console: 9001

**기본 자격 증명:**
- Access Key: `minioadmin`
- Secret Key: `minioadmin`

**버킷:** `msp-archive` (자동 생성)

### 4.4 BGE-m3 Embedding Service

**포트:** 8080
**모델:** BAAI/bge-m3
**차원:** 1024 (dense), 250002 (sparse)

**상태 확인:**
```bash
curl http://localhost:8080/health
```

### 4.5 Gotenberg

**포트:** 3000
**용도:** 레거시 문서 포맷 변환
- `.doc` → `.docx`
- `.ppt` → `.pptx`

---

## 5. 개발 환경 설정

### 5.1 로컬 Python 환경

```bash
# Poetry 설치
curl -sSL https://install.python-poetry.org | python3 -

# 의존성 설치
poetry install

# 가상 환경 활성화
poetry shell

# 환경 변수 복사
cp .env.example .env
# .env 편집 (필수 값 설정)

# 데이터베이스 마이그레이션
poetry run alembic upgrade head

# 서버 실행
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5.2 로컬 프론트엔드 개발

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev

# 프로덕션 빌드
npm run build
```

### 5.3 Celery Worker 실행

```bash
# 백그라운드 실행
poetry run celery -A app.workers.celery_app worker --loglevel=info

# Beat (스케줄러) 실행
poetry run celery -A app.workers.celery_app beat --loglevel=info
```

---

## 6. 주요 워크플로우

### 6.1 문서 업로드 및 검색

```
[1] 문서 업로드
    ┌─────────────────────────────────────────────────────────────┐
    │ 프론트엔드 → POST /api/v1/documents                        │
    │                                                             │
    │ 응답: Document { id, title, processing_status: "PENDING" } │
    └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
    [2] 백그라운드 처리
        ┌─────────────────────────────────────────────────────────┐
        │ Task: parse_document                                   │
        │   - 파일 형식 감지                                     │
        │   - 본문 텍스트 추출                                  │
        │   → status: "PARSED"                                  │
        └─────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────────────────────┐
        │ Task: chunk_document                                    │
        │   - 의미 기반 청킹 (1,000자 + 200자 overlap)          │
        │   - 섹션 제목 추출                                     │
        │   → status: "CHUNKED"                                  │
        └─────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────────────────────┐
        │ Task: embed_chunks                                      │
        │   - BGE-m3 임베딩 생성 (dense + sparse)                │
        │   - PostgreSQL 벡터 컬럼 저장                           │
        │   → status: "INDEXED"                                  │
        └─────────────────────────────────────────────────────────┘

[3] 문서 검색
    ┌─────────────────────────────────────────────────────────────┐
    │ 프론트엔드 → POST /api/v1/search/hybrid                     │
    │                                                             │
    │ Body: { query, customer_id, filters }                      │
    │                                                             │
    │ 응답: {                                                     │
    │   results: [{                                              │
    │     document_title,                                        │
    │     content (스니펫),                                      │
    │     score (RRF fusion score),                               │
    │     dense_score, sparse_score, keyword_score               │
    │   }],                                                      │
    │   total,                                                   │
    │   search_mode: "single-pass" | "multi-step"                 │
    │ }                                                          │
    └─────────────────────────────────────────────────────────────┘
```

### 6.2 AI 채팅 (Adaptive RAG)

```
[1] 질문 제출
    ┌─────────────────────────────────────────────────────────────┐
    │ 프론트엔드 → POST /api/v1/search/rag                       │
    │                                                             │
    │ Params: query, customer_id, cross_search                  │
    │                                                             │
    │ 응답: {                                                     │
    │   mode: "single-pass" | "multi-step",                      │
    │   response: "생성된 응답 텍스트",                          │
    │   tool_results: [...]                                      │
    │ }                                                          │
    └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
    [2] 복잡도 판별
        ┌─────────────────────────────────────────────────────────┐
        │ GPT-4o가 질문 분석                                      │
        │                                                         │
        │ Simple: 단일 주제, 직접적 질문                          │
        │ Complex: 다단계 추론, 비교, 이력 필요                    │
        └─────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
    ┌───────────────────┐           ┌───────────────────┐
    │ Single-pass       │           │ Multi-step        │
    │                   │           │                   │
    │ 1. 3-way 검색    │           │ 1. 쿼리 분해      │
    │ 2. LLM 응답      │           │ 2. 도구 선택      │
    │                   │           │ 3. 반복 검색      │
    │ Latency: 2-3초   │           │ 4. 결과 종합      │
    │                   │           │                   │
    │                   │           │ Latency: 5-15초   │
    └───────────────────┘           └───────────────────┘
```

### 6.3 이메일 수집

```
[1] IMAP 계정 등록
    ┌─────────────────────────────────────────────────────────────┐
    │ 관리자 → POST /api/v1/email/accounts                       │
    │                                                             │
    │ Body: {                                                    │
    │   email_address: "support@company.com",                    │
    │   imap_host: "imap.gmail.com",                             │
    │   username: "support@company.com",                         │
    │   password: "app-password"                                 │
    │ }                                                          │
    └─────────────────────────────────────────────────────────────┘

[2] 연결 테스트
    ┌─────────────────────────────────────────────────────────────┐
    │ POST /api/v1/email/accounts/{id}/test                      │
    │                                                             │
    │ 응답: { status: "success" | "error", message }            │
    └─────────────────────────────────────────────────────────────┘

[3] 이메일 수집
    ┌─────────────────────────────────────────────────────────────┐
    │ Celery 스케줄러 (15분마다) 또는                             │
    │ POST /api/v1/email/accounts/{id}/collect (수동)           │
    │                                                             │
    │ 처리:                                                      │
    │ 1. IMAP 서버에서邮件 가져오기                              │
    │ 2. 고객사 자동 분류                                        │
    │ 3. 인용문 중복 제거 (정규화 SHA-256)                       │
    │ 4. 이메일 본문 → 청킹 → 임베딩                             │
    │ 5. Apache AGE에 Graph 노드 생성                            │
    └─────────────────────────────────────────────────────────────┘
```

---

## 7. 장애 처리

### 7.1 서비스 상태 확인

```bash
# 전체 서비스 상태
docker-compose ps

# 특정 서비스 로그
docker-compose logs -f postgres
docker-compose logs -f app
docker-compose logs -f celery

# 헬스체크
curl http://localhost:8000/health
curl http://localhost:8080/health  # BGE-m3
```

### 7.2 일반적인 문제

#### 문서가 처리되지 않을 때

```bash
# Celery Worker 로그 확인
docker-compose logs celery | grep -i error

# Pending Task 확인
docker-compose exec redis redis-cli LLEN celery

# 수동으로 Task 재시작 (구현 필요 시)
```

#### 검색 결과가 없을 때

```bash
# 청크 생성 확인
docker-compose exec postgres psql -U postgres -d msp_archive -c \
  "SELECT COUNT(*) FROM document_chunks;"

# 임베딩 존재 확인
docker-compose exec postgres psql -U postgres -d msp_archive -c \
  "SELECT COUNT(*) FROM document_chunks WHERE dense_vector IS NOT NULL;"
```

#### BGE-m3 임베딩 서비스 오류

```bash
# 서비스 상태
curl http://localhost:8080/health

# 로그 확인
docker-compose logs embedding

# 컨테이너 재시작
docker-compose restart embedding
```

### 7.3 데이터 복구

```bash
# PostgreSQL 덤프
docker-compose exec postgres pg_dump -U postgres msp_archive > backup.sql

# MinIO 버킷 동기화
docker-compose exec minio mc mirror local/msp-archive /data/msp-archive-backup
```

---

## 8. 설정 레퍼런스

### 8.1 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 연결 문자열 | `postgresql+asyncpg://postgres:postgres@postgres:5432/msp_archive` |
| `REDIS_URL` | Redis 연결 문자열 | `redis://redis:6379/0` |
| `S3_ENDPOINT_URL` | MinIO endpoint | `http://minio:9000` |
| `S3_ACCESS_KEY` | MinIO Access Key | `minioadmin` |
| `S3_SECRET_KEY` | MinIO Secret Key | `minioadmin` |
| `S3_BUCKET_NAME` | 버킷 이름 | `msp-archive` |
| `EMBEDDING_API_URL` | BGE-m3 TEI URL | `http://embedding:8080` |
| `OPENAI_API_KEY` | OpenAI API Key | (필수) |
| `SECRET_KEY` | JWT 서명 키 | `dev-secret-...` |
| `LOG_LEVEL` | 로그 레벨 | `INFO` |

### 8.2 API 기본 URL

| 환경 | URL |
|------|-----|
| 로컬 | `http://localhost:8000` |
| Docker | `http://app:8000` (컨테이너 내부) |

---

## 9. 보안 체크리스트

- [ ] `SECRET_KEY` 프로덕션용으로 변경
- [ ] `OPENAI_API_KEY` 환경 변수로 설정
- [ ] MinIO 기본 비밀번호 변경
- [ ] PostgreSQL 비밀번호 변경
- [ ] CORS 설정 (`allow_origins`) 프로덕션 도메인 제한
- [ ] SSL/TLS 적용 (Nginx 리버스 프록시)
- [ ] 방화벽规则 설정
- [ ] 정기적인 보안 업데이트

---

## 10. 프로덕션 배포 고려사항

### 10.1 Kubernetes 배포

```yaml
# 예시: app Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: msp-archive-api
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: msp-archive/api:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: msp-archive-secrets
              key: database-url
```

### 10.2 모니터링

- **Prometheus**: 메트릭 수집
- **Grafana**: 대시보드
- **ELK Stack**: 로그 중앙화

### 10.3 CI/CD

```yaml
# GitHub Actions 예시
name: Deploy
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker-compose build
      - run: docker-compose push
```

---

## 11. API 사용 예제

### 11.1 인증

```bash
# 로그인
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 응답
# {"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer"}

# Bearer Token 사용
export TOKEN="eyJ..."
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

### 11.2 문서 업로드

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf" \
  -F "title=비상연락망" \
  -F "document_type=EMERGENCY_CONTACT" \
  -F "customer_id=1" \
  -F "tags=연락처,긴급"
```

### 11.3 하이브리드 검색

```bash
curl -X POST http://localhost:8000/api/v1/search/hybrid \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "김담당 연락처",
    "customer_id": 1,
    "limit": 10
  }'
```

### 11.4 Adaptive RAG 채팅

```bash
curl -X POST "http://localhost:8000/api/v1/search/rag?query=서버%20장애%20조치%20방법&customer_id=1" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 12. 지원

- **이슈 리포트:** https://github.com/your-org/msp-archive/issues
- **문서:** https://docs.msp-archive.example.com
- **이메일:** support@msp-archive.example.com
