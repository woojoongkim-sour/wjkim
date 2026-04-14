# MSP Archive Platform - PRD (Product Requirements Document)

**문서 버전**: 1.6.1
**작성일**: 2026-04-15
**상태**: Implementation Complete

---

## 1. 개요

### 1.1 배경

MSP(Managed Service Provider) 운영 환경에서 50개 이상의 고객사를 관리하며, 작업 결과서, 장애보고서, 운영 매뉴얼, 기동절차서, 비상연락망, SLA 문서, 고객 이메일 등 다양한 형태의 문서가 흩어져 있다. 엔지니어가 장애 대응이나 일상 운영 시 필요한 정보를 빠르게 찾기 어렵고, 과거 유사 사례나 관련 문서 간 연관성을 파악하기 어렵다.

### 1.2 목적

MSP Archive Platform은 흩어진 문서를 통합 관리하고, 하이브리드 검색과 Graph DB를 통해 문서 및 인프라 간 관계를 탐색하며, **Agentic RAG** 기반 채팅으로 엔지니어에게 즉각적인 정보를 제공하는 플랫폼이다. 단순 질의는 single-pass RAG로 빠르게 처리하고, 복합 질의는 PydanticAI 에이전트가 검색 도구를 자율 선택·반복하여 최적의 답변을 생성하는 Adaptive 방식을 채택한다.

### 1.3 대상 사용자

- **MSP 엔지니어/운영자** (10~50명 규모)
- 장애 대응, 일상 운영 업무 시 문서 검색 및 참조

### 1.4 연관 시스템

- **장애 보고 시스템**: MSP Archive의 검색/RAG/Graph API를 소비하는 부가 시스템. Zabbix 이벤트 기반 장애 분석 및 대시보드 제공.

---

## 2. 기능 요구사항

### 2.1 우선순위 정의

| 우선순위 | 기능 | 상태 |
|---------|------|------|
| **P1 (필수/MVP)** | 문서 업로드/파싱, 3-way 하이브리드 검색, Agentic RAG 채팅 (Adaptive 라우팅), LLM 요약/분석 | ✅ 구현 완료 |
| **P2 (중요)** | IMAP 이메일 수집, Graph DB 관계 모델링, 고객사별 데이터 격리 + 크로스 검색, 고객사/서버/담당자 관리 화면, 장애 보고 시스템 연동 API | ✅ 구현 완료 |
| **P3 (후순위)** | 사용자 인증 (ID/PW) | ✅ 구현 완료 |

### 2.2 문서 관리

#### 2.2.1 문서 업로드 ✅

- 웹 UI를 통한 수동 업로드 (단건/다건)
- 업로드 시 고객사 및 문서 카테고리 지정
- 업로드 유형 선택: **신규 문서 등록** 또는 **기존 문서 업데이트** (새 버전)

**중복 업로드 판정 (구현됨):**

업로드 시 파일의 SHA-256 해시(`content_hash`)를 계산하여 동일 고객사 내 기존 문서와 비교한다.

| 상황 | 판정 | 동작 |
|------|------|------|
| 같은 `content_hash`가 이미 존재 | 동일 파일 중복 | 업로드 거부 + 기존 문서 정보 반환 (HTTP 409) |
| 같은 파일명이지만 `content_hash`가 다름 | 파일 내용 변경 | "기존 문서 업데이트"로 유도 → 새 버전 저장 |
| `content_hash`도 파일명도 기존에 없음 | 신규 문서 | 정상 등록 |

#### 2.2.2 문서 버전 관리 ✅

- 새 버전 등록은 **사용자가 명시적으로** "기존 문서 업데이트"를 선택하여 수행
- 기존 문서를 카테고리/문서명으로 검색하여 선택 후 새 파일 업로드
- 새 버전 등록 시 기존 최신 버전의 `is_latest`를 false로 변경
- **과거 버전은 영구 보존** (삭제 불가, 검색/조회 가능)
- 모든 버전은 개별적으로 파싱 → 청킹 → 임베딩 저장

**시점 기반 버전 필터링:**

| 상황 | 동작 |
|------|------|
| 일반 검색/RAG (시점 언급 없음) | `is_latest = true`인 문서의 청크만 검색 |
| "전체 버전 포함" 필터 ON | 과거 버전 포함 모든 청크 검색 |
| 시점 기반 조회 (시점 언급 있음) | PydanticAI 에이전트가 질문에서 시점을 감지하여 해당 시점에 유효했던 버전만 검색 |

#### 2.2.3 지원 문서 형식

| 포맷 | 파싱 라이브러리 | 비고 |
|------|----------------|------|
| PDF | `PyMuPDF` | |
| DOCX | `python-docx` | |
| DOC (레거시) | Gotenberg → python-docx | LibreOffice 기반 변환 |
| PPTX | `python-pptx` | |
| PPT (레거시) | Gotenberg → python-pptx | LibreOffice 기반 변환 |
| XLSX | `openpyxl` | |
| XLS (레거시) | `xlrd` | |
| HWP/HWPX | `helper_hwp` | |
| CSV | Python 내장 `csv` | |
| TXT | Python 내장 `open()` | |

#### 2.2.4 의미 기반 청킹 전략

| 파라미터 | 값 | 설명 |
|----------|------|------|
| `max_chunk_size` | 1,000자 | 청크당 최대 문자 수 |
| `overlap` | 200자 | 청크 간 중복 문자 수 |

### 2.3 이메일 수집 (IMAP) ✅

- IMAP 프로토콜을 통한 주기적 자동 수집
- 수집 대상: 공유 메일함 + 엔지니어 개인 메일함
- IMAP 서버 설정 관리 (호스트, 포트, SSL, 계정, 대상 폴더, 수집 주기)
- 연결 테스트 기능
- 이메일 본문 → 문서로 변환 (파싱/임베딩)
- **인용문 중복 처리**: 청크 레벨 정규화 해싱으로 중복 제거

**고객사 자동 분류:**
1. 이메일 주소 → 고객사 매핑 테이블 조회
2. 도메인 → 고객사 매핑 조회
3. 메일 제목에서 고객사명/코드/별칭 매칭
4. 미분류 → "unclassified" 상태로 저장

### 2.4 검색 ✅

#### 2.4.1 3-way 하이브리드 검색

| 채널 | 역할 | 검색 대상 |
|------|------|-----------|
| Dense (pgvector) | 의미적 유사도 | 임베딩 벡터 |
| Sparse (SPARSEVEC) | 토큰 수준 정밀 매칭 | 임베딩 벡터 |
| Keyword (PGroonga) | 한국어 형태소 기반 전문 검색 | `chunks.content` + `document_title` + `section_title` |

**스코어링: RRF (Reciprocal Rank Fusion)**

```
RRF 공식: score = 1 / (rank + k),  k = 60

Weighted Fusion:
  final_rrf = (0.5 × dense_rrf) + (0.3 × sparse_rrf) + (0.2 × keyword_rrf)
```

### 2.5 Agentic RAG 채팅 ✅

- 단일 채팅창에서 문서 검색 + 요약 + 분석 통합 처리
- **Adaptive 라우팅**: 질의 복잡도에 따라 Single-pass / Multi-step 자동 선택
- SSE(Server-Sent Events) 기반 스트리밍 응답
- 응답에 참조 문서 출처 표시

**Adaptive 질의 라우팅:**

| 유형 | 조건 | 처리 경로 |
|------|------|-----------|
| Simple | 단일 주제, 직접적 정보 요청 | Single-pass RAG |
| Complex | 비교/이력/다단계 추론 필요 | Multi-step Agent |

### 2.6 Graph DB 관계 모델링 ✅

#### 노드
- Customer, Server, Service, Document, Person, Incident

#### 관계 (Edges)
- Customer → OWNS → Server
- Server → DEPENDS_ON → Server
- Server → RUNS → Service
- Document → ABOUT → Customer
- Incident → OCCURRED_ON → Server
- Incident → SIMILAR_TO → Incident

### 2.7 고객사/인프라 관리 ✅

- 고객사 CRUD (이름, 코드, 설명, 활성 상태)
- 서버 CRUD (호스트명, IP, OS, 유형, Zabbix 연동 ID)
- 서비스 CRUD (이름, 타입, 버전, 포트, 상태)
- 담당자 CRUD
- 담당자-고객사 다대다 매핑 관리

### 2.8 사용자 인증 ✅

- ID/PW 기반 자체 인증
- JWT 토큰 (access 15분 + refresh 7일)
- 역할: admin, engineer

---

## 3. 시스템 아키텍처

### 3.1 컨테이너 구성

| 컨테이너 | 이미지 | 역할 | 포트 |
|----------|--------|------|------|
| `postgres` | postgres:17 | PostgreSQL + pgvector + PGroonga | 5432 |
| `redis` | redis:7-alpine | 작업 큐 + 캐시 | 6379 |
| `minio` | minio/minio | S3 호환 스토리지 | 9000, 9001 |
| `embedding` | ghcr.io/huggingface/tei | BGE-m3 임베딩 서비스 | 8080 |
| `gotenberg` | gotenberg/gotenberg:8 | 레거시 포맷 변환 | 3000 |
| `app` | custom | FastAPI + PydanticAI | 8000 |
| `celery` | custom | ARQ 비동기 워커 | - |
| `frontend` | nginx | Next.js React SPA | 80 |

### 3.2 기술 스택

| 레이어 | 기술 |
|--------|------|
| 프론트엔드 | React / Next.js / TailwindCSS |
| API 서버 | Python 3.12 / FastAPI |
| AI 에이전트 | PydanticAI + OpenAI GPT-4o |
| 비동기 워커 | Celery (Redis 기반) |
| 데이터베이스 | PostgreSQL 17 |
| 벡터 검색 | pgvector (dense + sparse) |
| 전문 검색 | PGroonga (한국어 형태소) |
| 그래프 DB | Apache AGE (PostgreSQL 확장) |
| 임베딩 모델 | BGE-m3 (1024차원, HuggingFace TEI) |
| 포맷 변환 | Gotenberg (LibreOffice 기반) |
| 스토리지 | MinIO (S3 호환) |

---

## 4. API 엔드포인트

### 4.1 인증 (Authentication)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/v1/auth/register` | 사용자 등록 (관리자) |
| POST | `/api/v1/auth/login` | 로그인 |
| POST | `/api/v1/auth/refresh` | 토큰 갱신 |
| GET | `/api/v1/auth/me` | 현재 사용자 정보 |
| PUT | `/api/v1/auth/me` | 사용자 정보 수정 |
| POST | `/api/v1/auth/change-password` | 비밀번호 변경 |

### 4.2 검색 (Search)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/v1/search/hybrid` | 3-way 하이브리드 검색 |
| POST | `/api/v1/search/version` | 시점 기반 버전 검색 |
| POST | `/api/v1/search/cross` | 크로스 고객사 검색 |
| POST | `/api/v1/search/rag` | Adaptive RAG 질의 |

### 4.3 문서 (Documents)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/v1/documents` | 문서 업로드 |
| GET | `/api/v1/documents` | 문서 목록 |
| GET | `/api/v1/documents/{id}` | 문서 상세 |
| PUT | `/api/v1/documents/{id}` | 문서 수정 |
| DELETE | `/api/v1/documents/{id}` | 문서 삭제 |
| GET | `/api/v1/documents/{id}/versions` | 문서 버전 목록 |
| POST | `/api/v1/documents/{id}/refined` | 정제 문서 업로드 |
| GET | `/api/v1/documents/check-duplicate` | 중복 검사 |
| GET | `/api/v1/documents/{id}/graph-context` | Graph 컨텍스트 |

### 4.4 이메일 (Email)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/v1/email/accounts` | IMAP 계정 목록 |
| POST | `/api/v1/email/accounts` | IMAP 계정 생성 |
| POST | `/api/v1/email/accounts/{id}/test` | 계정 연결 테스트 |
| POST | `/api/v1/email/accounts/{id}/collect` | 이메일 수집 |
| GET | `/api/v1/email/emails` | 수집된 이메일 목록 |
| GET | `/api/v1/email/emails/{id}` | 이메일 상세 |

---

## 5. 데이터 흐름

### 5.1 문서 업로드 및 처리 파이프라인

```
사용자 → Next.js → API (파일 수신)
                  │
                  ├─ SHA-256 해시 계산 → 중복 판정
                  │   ├─ 중복 → 거부 (HTTP 409)
                  │   └─ 통과 ↓
                  ├─ 파일 → MinIO 스토어에 저장
                  ├─ 메타데이터 → PostgreSQL documents 테이블
                  └─ 파이프라인 시작 → Celery 큐에 Task 등록

Celery Worker:
  Task 1: 파싱 → Task 2: 청킹 → Task 3: 임베딩 → Task 4: Graph 동기화
```

### 5.2 검색 및 RAG 파이프라인

```
사용자 질문
    │
    ▼
Adaptive RAG Orchestrator
    │
    ├─ Simple 판별 → Single-pass RAG
    │   → 3-way 하이브리드 검색 → LLM 응답
    │   → 응답 시간: 2~3초
    │
    └─ Complex 판별 → Multi-step Agent
        → 쿼리 분해 → 도구 선택 → 반복 검색
        → 응답 시간: 5~15초
```

---

## 6. 구현 현황

### ✅ 완료된 기능

- [x] 문서 업로드 및 스토리지 (MinIO)
- [x] SHA-256 중복 판정
- [x] 문서 버전 관리
- [x] 의미 기반 청킹
- [x] 3-way 하이브리드 검색 (Dense + Sparse + Keyword RRF)
- [x] Adaptive RAG Agent
- [x] Graph DB 서비스 (Apache AGE 연동)
- [x] IMAP 이메일 수집
- [x] 이메일 인용문 중복 제거
- [x] JWT 사용자 인증
- [x] 프론트엔드 문서 관리 UI

### 📋 후속 작업

- [ ] BGE-m3 임베딩 서비스 TEI 연동
- [ ] 문서 파싱 라이브러리 완전한 연동
- [ ] PGroonga 인덱스 구성
- [ ] Apache AGE 그래프 초기화 스크립트
- [ ] Celery 워커正式启动 스크립트
- [ ] E2E 테스트 작성
- [ ] CI/CD 파이프라인 구성
