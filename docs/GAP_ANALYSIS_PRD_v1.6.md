# GAP Analysis: PRD v1.6 vs Current Implementation

**작성일**: 2026-04-14
**비교 대상**: PRD v1.6 (2026-04-14) vs msp-archive 현재 코드베이스
**목적**: PRD에 명시된 요구사항 대비 현재 구현 상태를 항목별로 비교하고, 미구현/차이 사항을 식별한다.

---

## 1. Executive Summary

### 전체 구현율

| 영역 | PRD 요구사항 | 구현 완료 | 부분 구현 | 미구현 |
|------|-------------|----------|----------|-------|
| 기술 스택 / 인프라 | 8개 컨테이너 | 2 | 2 | 4 |
| 문서 관리 (P1) | 16개 항목 | 3 | 5 | 8 |
| 검색 (P1) | 10개 항목 | 1 | 2 | 7 |
| Agentic RAG 채팅 (P1) | 14개 항목 | 2 | 1 | 11 |
| 이메일 수집 (P2) | 8개 항목 | 0 | 0 | 8 |
| Graph DB (P2) | 6개 항목 | 0 | 1 | 5 |
| 고객사/인프라 관리 (P2) | 7개 항목 | 3 | 1 | 3 |
| 장애 보고 연동 API (P2) | 6개 항목 | 2 | 2 | 2 |
| 사용자 인증 (P3) | 5개 항목 | 0 | 1 | 4 |
| UI/UX | 6개 화면 | 1 | 1 | 4 |
| 데이터 모델 | 16개 테이블 | 6 | 3 | 7 |

---

## 2. 기술 스택 / 인프라 차이

### 2.1 컨테이너 구성

PRD는 8개 컨테이너를 정의한다. 현재는 6개가 존재하며, 핵심 4개가 누락 또는 대체되었다.

| PRD 컨테이너 | PRD 기술 | 현재 상태 | 현재 기술 | 차이 |
|-------------|---------|----------|----------|------|
| next | Next.js (node:22-alpine) | **대체됨** | Vite + React (node:20-alpine + nginx) | 프레임워크 변경 |
| api | FastAPI + PydanticAI | **부분 구현** | FastAPI (PydanticAI 미사용) | PydanticAI 누락 |
| worker | ARQ 비동기 워커 | **대체됨** | Celery 워커 | 워커 프레임워크 변경 |
| redis | Redis 7-alpine | **구현 완료** | Redis 7-alpine | 일치 |
| postgres | PostgreSQL 17 (pgvector + AGE + PGroonga) | **부분 구현** | PostgreSQL 16-alpine (pgvector만) | AGE, PGroonga 누락 |
| embedding | HuggingFace TEI (BGE-m3) | **미구현** | OpenAI API로 대체 | 모델, 서빙 방식 전면 변경 |
| gotenberg | Gotenberg 8 | **미구현** | 없음 | 레거시 포맷 변환 불가 |
| ollama | Ollama (Gemma 4) | **미구현** | 없음 | Local LLM 미지원 |

### 2.2 핵심 기술 스택 차이

| 항목 | PRD v1.6 | 현재 구현 | 영향도 |
|------|---------|----------|-------|
| 프론트엔드 프레임워크 | Next.js (React SSR) | Vite + React (SPA) | **중** - SSR/SEO 불필요하므로 기능적 차이 적음 |
| AI 에이전트 프레임워크 | PydanticAI | 없음 (직접 OpenAI 호출) | **상** - Agentic RAG 핵심 기능 미구현 |
| 비동기 워커 | ARQ (Redis 기반) | Celery (Redis 기반) | **하** - 기능적으로 유사, ARQ가 더 경량 |
| 임베딩 모델 | BGE-m3 (1024차원, self-hosted) | OpenAI text-embedding-3-small (1536차원, API) | **상** - 비용, 차원, 오프라인 가용성 차이 |
| LLM | Ollama (Gemma 4) / AWS Bedrock 택1 | OpenAI GPT-4o 고정 | **중** - LLM 제공자 전환 불가 |
| 전문 검색 | PGroonga (한국어 형태소) | ILIKE (단순 문자열 매칭) | **상** - 한국어 검색 품질 차이 큼 |
| 그래프 DB | Apache AGE (Cypher) | 없음 (mock 응답) | **상** - 관계 탐색 기능 부재 |
| 문서 변환 | Gotenberg (LibreOffice) | 없음 | **중** - .doc, .ppt 레거시 포맷 처리 불가 |
| 파일 저장 | 로컬 디스크 -> NCP Object Storage | MinIO (S3 호환) | **하** - MinIO가 오히려 유연 |
| PostgreSQL 버전 | 17 | 16-alpine | **하** - 기능 차이 미미 |

---

## 3. 데이터 모델 차이

### 3.1 PRD에 정의되었으나 현재 없는 테이블

| 테이블 | PRD 용도 | 현재 상태 |
|--------|---------|----------|
| `customer_aliases` | 고객사 별칭 관리 (이메일 자동 분류용) | **미구현** |
| `email_customer_mappings` | 이메일주소/도메인 → 고객사 매핑 | **미구현** |
| `document_categories` | 문서 카테고리 별도 테이블 관리 | **미구현** - enum으로 대체 |
| `emails` | 이메일 저장 (IMAP 수집) | **미구현** |
| `email_attachments` | 이메일 첨부파일 추적 | **미구현** |
| `imap_configs` | IMAP 서버 설정 관리 | **미구현** |
| `conversations` | 채팅 대화 세션 관리 | **미구현** |
| `messages` | 채팅 메시지 이력 저장 | **미구현** |
| `persons` | 담당자 정보 관리 | **미구현** |
| `person_customers` | 담당자-고객사 다대다 매핑 | **미구현** |
| `users` | 사용자 인증 관리 | **미구현** |
| `llm_configs` | LLM 제공자 설정 (Ollama/Bedrock 전환) | **미구현** |
| `job_logs` | 비동기 작업 로그 추적 | **미구현** - processing_attempts로 부분 대체 |

### 3.2 현재 존재하지만 PRD에 없는 테이블

| 테이블 | 현재 용도 | 비고 |
|--------|---------|------|
| `manual_refined_documents` | 수동 정제본 관리 | PRD v1.8에서 유입된 개념 |
| `document_processing_attempts` | 문서 처리 시도 이력 | job_logs와 유사한 역할 |
| `document_relations` | 문서 간 관계 | Graph DB 대체 역할 |
| `metric_log_evidence` | 메트릭/로그 증거 | PRD v1.8에서 유입 |
| `sanitized_knowledge` | 비식별화 공통 지식 | PRD v1.8에서 유입 |
| `incident_cases` | 장애 사례 구조화 | PRD의 `incidents`와 유사하나 스키마 다름 |

### 3.3 공통 테이블의 스키마 차이

#### `documents` 테이블

| PRD 컬럼 | 현재 상태 | 비고 |
|---------|----------|------|
| `content_hash` (SHA-256) | `file_hash` | 이름 다름, 용도 동일 |
| `source_type` ("upload" / "imap") | 없음 | 이메일 수집 미구현으로 불필요 |
| `parsed_status` (7단계) | `processing_status` (11단계) | 현재가 더 세분화 (PRD v1.8 기준) |
| `meta_only` (boolean) | 없음 | protection_type으로 유추 가능 |
| `version_group_id` (UUID) | 없음 | 버전 그룹핑 미구현 |
| `version` (integer) | `version` (integer) | 존재하나 group_id 없이 단독 |
| `is_latest` (boolean) | 없음 | 버전 필터링 미구현 |
| `category_id` (FK) | `document_type` (enum) | 별도 테이블 vs enum |
| `original_filename` | `file_name` | 이름만 다름 |

#### `chunks` 테이블

| PRD 컬럼 | 현재 상태 | 비고 |
|---------|----------|------|
| `customer_id` (비정규화) | 없음 | 검색 시 JOIN 필요 |
| `document_title` (비정규화) | 없음 | PGroonga 검색용 - 미구현 |
| `section_title` | 없음 | 의미 기반 청킹 미구현 |
| `token_count` | 없음 | LLM 컨텍스트 관리 불가 |
| `content_hash` (이메일 중복 제거) | 없음 | 이메일 기능 미구현 |
| `dense_vector` VECTOR(1024) | `embedding` LargeBinary | 타입/차원 다름 (1024 vs 1536) |
| `sparse_vector` SPARSEVEC | 없음 | Sparse 검색 미구현 |

#### `customers` 테이블

| PRD 컬럼 | 현재 상태 | 비고 |
|---------|----------|------|
| `code` (UNIQUE) | `code` | 일치 |
| `name` | `name` | 일치 |
| `description` | `description` | 일치 |
| `is_active` | `is_active` | 일치 |

#### `servers` 테이블

| PRD 컬럼 | 현재 상태 | 비고 |
|---------|----------|------|
| `hostname` | `hostname` | 일치 |
| `ip_address` | `ip_address` | 일치 |
| `os` | `os_type` | 이름 다름 |
| `type` (physical/vm/container) | 없음 | 서버 유형 구분 미구현 |
| `zabbix_host_id` | 없음 | 모니터링 연동 ID 미구현 |
| `status` (active/inactive/decommissioned) | `is_active` (boolean) | 3상태 vs 2상태 |

#### `incidents` (PRD) vs `incident_cases` (현재)

| PRD 컬럼 | 현재 상태 | 비고 |
|---------|----------|------|
| `server_id` (FK) | 없음 | 서버 직접 연결 없음 |
| `assigned_to` (FK → persons) | 없음 | 담당자 지정 미구현 |
| `source_event_id` | `related_event_ids` (ARRAY) | 단일 FK vs 배열 |
| `sla_deadline` | 없음 | SLA 기한 미구현 |
| `resolution` (TEXT) | `resolution_summary` | 이름 다름 |

---

## 4. 기능별 GAP 분석

### 4.1 문서 관리 (P1)

#### 4.1.1 문서 업로드

| PRD 요구사항 | 현재 상태 | 상세 |
|-------------|----------|------|
| 웹 UI 수동 업로드 (단건/다건) | **미구현** | 프론트엔드에 문서 업로드 페이지 없음 |
| 업로드 시 고객사/카테고리 지정 | **부분 구현** | API에서 customer_id 지정 가능, 카테고리는 enum |
| 신규 등록 / 기존 문서 업데이트 선택 | **미구현** | 버전 관리 UI/로직 없음 |
| SHA-256 중복 판정 (content_hash) | **부분 구현** | file_hash 존재하나 중복 업로드 거부 로직 미확인 |
| 같은 hash → HTTP 409 거부 | **미구현** | 중복 판정 API 레벨 처리 없음 |
| 같은 파일명 + 다른 hash → 업데이트 유도 | **미구현** | |

#### 4.1.2 문서 버전 관리

| PRD 요구사항 | 현재 상태 | 상세 |
|-------------|----------|------|
| version_group_id로 버전 그룹핑 | **미구현** | version 필드만 존재 |
| is_latest 플래그 | **미구현** | |
| 과거 버전 영구 보존 | **미구현** | 삭제 방식 불명 |
| 모든 버전 개별 파싱/청킹/임베딩 | **미구현** | |
| 검색 시 is_latest 필터링 | **미구현** | |
| 시점 기반 버전 필터링 | **미구현** | PydanticAI 에이전트가 시점 감지 필요 |

#### 4.1.3 문서 파싱

| PRD 지원 포맷 | 현재 상태 | 비고 |
|--------------|----------|------|
| PDF (PyMuPDF) | **부분 구현** | PyPDF2 사용 (PyMuPDF 아님) |
| DOCX (python-docx) | **구현 완료** | python-docx 의존성 존재 |
| DOC (Gotenberg 변환) | **미구현** | Gotenberg 컨테이너 없음 |
| PPTX (python-pptx) | **미구현** | 의존성 없음 |
| PPT (Gotenberg 변환) | **미구현** | Gotenberg 컨테이너 없음 |
| XLSX (openpyxl) | **미구현** | 의존성 없음 |
| XLS (xlrd) | **미구현** | 의존성 없음 |
| HWP/HWPX (helper_hwp) | **미구현** | 의존성 없음 |
| CSV (내장) | **미구현** | |
| TXT (내장) | **미구현** | |
| EML (mail-parser) | **미구현** | 이메일 수집 기능 없음 |

#### 4.1.4 청킹 전략

| PRD 요구사항 | 현재 상태 | 상세 |
|-------------|----------|------|
| 의미 기반 청킹 (hierarchical) | **미구현** | placeholder 텍스트 추출 (더미 구현) |
| max_chunk_size: 1000자, overlap: 200자 | **부분 구현** | 설정값은 일치 (CHUNK_SIZE=1000, CHUNK_OVERLAP=200) |
| 문단 → 문장 계층적 분할 | **미구현** | |
| 섹션 제목 추출 (포맷별) | **미구현** | section_title 컬럼 자체가 없음 |
| 임베딩 입력: [문서제목] [섹션제목] 청크내용 | **미구현** | 청크 content만 임베딩 |
| MAX_TEXT_LENGTH: 5000자 기반 재분할 | **미구현** | |
| 암호화 감지 흐름 | **구현 완료** | ProtectionDetector 구현됨 |

#### 4.1.5 문서 처리 파이프라인

| PRD 요구사항 | 현재 상태 | 상세 |
|-------------|----------|------|
| 4단계 체인 (parse → chunk → embed → finalize) | **부분 구현** | 단일 태스크로 처리 (단계 분리 안 됨) |
| 단계별 독립 ARQ task | **미구현** | Celery 단일 태스크 |
| 단계별 롤백 정책 | **미구현** | |
| 3회 자동 재시도 | **미구현** | |
| 처리 진행률 SSE (Redis Pub/Sub) | **미구현** | |
| parsed_status 단계별 업데이트 | **부분 구현** | 상태 업데이트는 하나 단계가 다름 |

### 4.2 검색 (P1)

| PRD 요구사항 | 현재 상태 | 상세 |
|-------------|----------|------|
| Dense 검색 (pgvector, cosine) | **구현 완료** | VectorSearchService에서 cosine similarity 사용 |
| Sparse 검색 (SPARSEVEC, BGE-m3) | **미구현** | BGE-m3 미사용, sparse_vector 컬럼 없음 |
| Keyword 검색 (PGroonga, 한국어 형태소) | **미구현** | ILIKE 기반 단순 문자열 매칭으로 대체 |
| RRF (Reciprocal Rank Fusion) 스코어링 | **미구현** | |
| Fusion 가중치 (Dense 0.5, Sparse 0.3, Keyword 0.2) | **미구현** | |
| Final Score 0~1 정규화 | **미구현** | |
| 고객사별 데이터 격리 (단일 검색) | **구현 완료** | customer_id 기반 필터링 |
| 크로스 검색 모드 (전체 고객사) | **부분 구현** | search_service에 크로스 로직 존재하나 API 분리 안 됨 |
| 필터 (카테고리, 파일형식, 기간) | **부분 구현** | 일부 필터 존재 |
| 필터 정제 (Sanitization) | **미구현** | |
| Recency Score (tie-breaker) | **미구현** | |

### 4.3 Agentic RAG 채팅 (P1)

| PRD 요구사항 | 현재 상태 | 상세 |
|-------------|----------|------|
| PydanticAI 에이전트 기반 | **미구현** | 직접 OpenAI 호출 |
| Adaptive 라우팅 (Simple/Complex 자동 판별) | **미구현** | |
| Single-pass RAG (Simple 경로) | **부분 구현** | 기본 RAG는 동작하나 PRD 수준 아님 |
| Multi-step Agent (Complex 경로) | **미구현** | |
| 에이전트 도구: hybrid_search | **미구현** | |
| 에이전트 도구: graph_traverse | **미구현** | |
| 에이전트 도구: version_search | **미구현** | |
| 에이전트 도구: cross_search | **미구현** | |
| SSE 스트리밍 응답 | **미구현** | 표준 HTTP POST 응답 |
| SSE agent_step 진행 이벤트 | **미구현** | |
| 대화 이력 관리 (conversations/messages 테이블) | **미구현** | 테이블 없음, 프론트 인메모리만 |
| 응답 피드백 (thumbs up/down) | **미구현** | |
| 응답 재생성 | **미구현** | |
| 생성 취소 | **미구현** | |
| 에스컬레이션 임계값 (Dense Score < 0.5) | **미구현** | |
| 검색 실패 복구 전략 (5단계) | **미구현** | |
| RAG 컨텍스트 포맷 ([출처N]) | **부분 구현** | evidence 형태로 출처 반환 |
| LLM 시스템 프롬프트 (근거 기반 응답 규칙) | **구현 완료** | chat_agent.py에 시스템 프롬프트 존재 |

### 4.4 이메일 수집 (P2)

| PRD 요구사항 | 현재 상태 |
|-------------|----------|
| IMAP 주기적 자동 수집 | **미구현** |
| 수집 대상: 공유 + 개인 메일함 | **미구현** |
| IMAP 서버 설정 관리 UI | **미구현** |
| 연결 테스트 기능 | **미구현** |
| 이메일 본문 → 문서 변환 | **미구현** |
| 첨부파일 개별 문서 저장 | **미구현** |
| 스레드 그룹핑 | **미구현** |
| 4단계 고객사 자동 분류 | **미구현** |
| 인용문 청크 중복 제거 (정규화 해싱) | **미구현** |
| 수동 즉시 수집 트리거 | **미구현** |

### 4.5 Graph DB 관계 모델링 (P2)

| PRD 요구사항 | 현재 상태 | 상세 |
|-------------|----------|------|
| Apache AGE 그래프 DB | **미구현** | AGE 확장 미설치 |
| 6종 노드 (Customer, Server, Service, Document, Person, Incident) | **미구현** | |
| 11종 관계 (OWNS, DEPENDS_ON, RUNS 등) | **미구현** | |
| PostgreSQL 트리거 기반 자동 동기화 | **미구현** | |
| Graph 탐색 API (영향 범위, 의존성 등) | **mock 구현** | search.py에 graph_context 엔드포인트 있으나 mock 데이터 반환 |
| Cypher 쿼리 | **미구현** | |

### 4.6 고객사/인프라 관리 (P2)

| PRD 요구사항 | 현재 상태 | 상세 |
|-------------|----------|------|
| 고객사 CRUD | **구현 완료** | customers API |
| 서버 CRUD | **구현 완료** | servers API |
| 서비스 CRUD | **구현 완료** | services API |
| 담당자 CRUD | **미구현** | persons 테이블/API 없음 |
| 담당자-고객사 매핑 | **미구현** | person_customers 없음 |
| Graph 관계 관리 UI | **미구현** | |
| 문서 카테고리 관리 (CRUD) | **미구현** | enum으로 하드코딩 |

### 4.7 장애 보고 시스템 연동 API (P2)

| PRD 요구사항 | 현재 상태 | 상세 |
|-------------|----------|------|
| API Key 기반 인증 | **미구현** | X-API-Key 인증 없음 |
| 검색 API (단일/크로스) | **구현 완료** | search API |
| RAG 질의 API (비스트리밍) | **구현 완료** | chat API |
| Graph 탐색 API | **mock 구현** | mock 데이터 |
| SLA 정보 조회 API | **미구현** | SLA 데이터 모델 없음 |
| 인시던트 CRUD API | **부분 구현** | incident API (생성/조회 있으나 CRUD 불완전) |
| Webhook 등록/관리 | **미구현** | Zabbix webhook 수신만 있음, 발행 없음 |

### 4.8 사용자 인증 (P3)

| PRD 요구사항 | 현재 상태 | 상세 |
|-------------|----------|------|
| ID/PW 자체 인증 | **미구현** | 의존성(python-jose, passlib) 존재하나 구현 없음 |
| JWT (access 15분 + refresh 7일) | **미구현** | config에 SECRET_KEY, ALGORITHM 설정만 |
| 역할 (admin, engineer) | **미구현** | |
| 비밀번호 변경 | **미구현** | |
| users 테이블 | **미구현** | |

---

## 5. API 엔드포인트 GAP

### 5.1 PRD에 정의되었으나 미구현된 API

| API 그룹 | 엔드포인트 | 현재 상태 |
|---------|-----------|----------|
| **인증** | POST /auth/login | 미구현 |
| | POST /auth/refresh | 미구현 |
| | POST /auth/logout | 미구현 |
| | GET /auth/me | 미구현 |
| | PUT /auth/me/password | 미구현 |
| **문서** | POST /documents/upload/batch | 미구현 (다건 업로드) |
| | GET /documents/{id}/chunks | 미구현 |
| | GET /documents/{id}/status/stream | 미구현 (SSE) |
| **검색** | POST /search/cross | 미구현 (크로스 검색 별도 엔드포인트) |
| **Graph** | GET /graph/impact/{server_id} | mock |
| | GET /graph/dependencies/{server_id} | 미구현 |
| | GET /graph/related-docs/{entity_type}/{id} | 미구현 |
| | GET /graph/contacts/{server_id} | 미구현 |
| | GET /graph/incident-history/{server_id} | 미구현 |
| | GET /graph/path | 미구현 |
| | POST, DELETE /graph/relationships | 미구현 |
| **채팅** | POST /chat/conversations | 미구현 |
| | GET /chat/conversations | 미구현 |
| | GET /chat/conversations/{id} | 미구현 |
| | PATCH /chat/conversations/{id} | 미구현 |
| | DELETE /chat/conversations/{id} | 미구현 |
| | POST /chat/conversations/{id}/messages (SSE) | 미구현 |
| | POST /chat/messages/{id}/feedback | 미구현 |
| | POST .../regenerate | 미구현 |
| | POST .../cancel | 미구현 |
| **이메일** | 전체 (/emails, /imap-configs) | 미구현 |
| **관리** | /persons CRUD | 미구현 |
| | /document-categories CRUD | 미구현 |
| **시스템** | GET /system/health | 미구현 (/ health 기본만) |
| | GET /system/stats | 미구현 |
| | GET, PUT /system/llm-config | 미구현 |
| | GET /system/jobs, POST .../retry, .../cancel | 미구현 |
| | CRUD /system/users | 미구현 |
| | CRUD /system/api-keys | 미구현 |
| **연동** | 전체 /integration/* | 미구현 (별도 인증 체계) |

### 5.2 PRD에 없지만 현재 구현된 API

| 엔드포인트 | 현재 용도 | 비고 |
|-----------|---------|------|
| POST /documents/{id}/refined | 수동 정제본 업로드 | PRD v1.8 기능 |
| GET /documents/{id}/refined | 정제본 목록 | PRD v1.8 기능 |
| POST /documents/v2/ | 보호 감지 포함 업로드 | PRD v1.8 기능 |
| POST /chat/enrich-event | 이벤트 보강 | PRD v1.8 기능 |
| POST /events/ | 이벤트 직접 생성 | PRD v1.6에선 webhook으로만 |
| GET /audit/logs | 감사 로그 조회 | PRD v1.6 /system 하위 아님 |
| GET /audit/logs/stats | 감사 통계 | PRD v1.6에 없음 |

---

## 6. UI/UX GAP

### 6.1 화면 구현 현황

| PRD 화면 | 현재 상태 | 상세 |
|---------|----------|------|
| 전체 레이아웃 (Header + Sidebar + Main + StatusBar) | **부분 구현** | Layout 컴포넌트 (Sidebar + Main). StatusBar 없음 |
| 문서 관리 페이지 | **미구현** | 문서 목록/업로드/상태 UI 없음 |
| 검색 페이지 | **미구현** | 전용 검색 페이지 없음 |
| Agentic RAG 채팅 페이지 | **미구현** | 전용 채팅 페이지 없음 (이벤트 상세 내 채팅만) |
| 이메일 페이지 | **미구현** | |
| 인프라 관리 페이지 | **미구현** | 서버/서비스/담당자 관리 UI 없음 |
| 설정 페이지 | **미구현** | LLM, 사용자, API Key 관리 없음 |
| **대시보드** | **구현 완료** | 통계, 심각도 분포, 상위 위험 이벤트, 최근 활동 |
| **이벤트 목록** | **구현 완료** | 필터, 검색, 페이지네이션 |
| **이벤트 상세** | **구현 완료** | 분석, 이력, 조치, 관련 문서, 채팅 |

### 6.2 UI 기능 차이

| PRD 기능 | 현재 상태 | 상세 |
|---------|----------|------|
| 고객사 셀렉터 (Header) | **미구현** | 고객사 전환 UI 없음 |
| SSE 스트리밍 채팅 | **미구현** | HTTP POST 응답 |
| 에이전트 진행 상황 표시 | **미구현** | |
| 출처 카드 (문서명, 스코어, 스니펫, 도구 경로) | **부분 구현** | evidence 표시 있으나 도구 경로 없음 |
| 출처 카드 → 문서 상세 이동 | **미구현** | 문서 상세 페이지 자체 없음 |
| 검색 결과 배지 (metadata only, refined, vector indexed 등) | **미구현** | |
| 문서 처리 진행률 표시 | **미구현** | |
| 의존성 그래프 시각화 | **미구현** | |

---

## 7. 인덱스 전략 GAP

| PRD 인덱스 | 현재 상태 | 비고 |
|-----------|----------|------|
| HNSW (dense_vector, vector_cosine_ops) | **미구현** | pgvector 의존성은 있으나 인덱스 미생성 |
| HNSW (sparse_vector, sparsevec_cosine_ops) | **미구현** | sparse_vector 컬럼 없음 |
| PGroonga (content, document_title, section_title) | **미구현** | PGroonga 미설치 |
| PGroonga (documents.title) | **미구현** | |
| PGroonga (emails.subject) | **미구현** | |
| customer_id 인덱스 (chunks, documents, emails) | **미구현** | |
| UNIQUE (customer_id, content_hash) WHERE NOT NULL | **미구현** | 이메일 중복 제거 |
| parsed_status, content_hash, incidents.status 인덱스 | **미구현** | |

---

## 8. 비기능 요구사항 GAP

### 8.1 성능

| PRD 목표 | 현재 상태 | 비고 |
|---------|----------|------|
| 하이브리드 검색 < 2초 | **미확인** | 3-way 하이브리드 자체가 미구현 |
| RAG 첫 토큰 < 3초 (Simple) | **미확인** | SSE 미구현으로 측정 불가 |
| RAG 첫 토큰 < 15초 (Complex) | **해당 없음** | Multi-step 미구현 |
| 라우팅 판별 < 500ms | **해당 없음** | Adaptive 라우팅 미구현 |
| 문서 파싱+임베딩 < 30초 | **미확인** | |
| Graph 탐색 < 1초 | **해당 없음** | Graph DB 미구현 |
| 동시 접속자 50명 | **미확인** | |

### 8.2 보안

| PRD 요구사항 | 현재 상태 |
|-------------|----------|
| JWT 인증 | 미구현 |
| bcrypt 비밀번호 해싱 | 의존성만 존재 |
| IMAP 비밀번호 AES-256 암호화 | 미구현 |
| API Key SHA-256 해싱 | 미구현 |
| CORS Next.js 도메인 제한 | 미확인 |
| 파일 업로드 확장자 화이트리스트 100MB | 설정만 존재 |
| SQLAlchemy ORM 바인딩 | 구현 완료 |
| CSP 헤더 | 미구현 |

### 8.3 안정성

| PRD 요구사항 | 현재 상태 |
|-------------|----------|
| 파싱 3회 재시도 → failed → 수동 재시도 | 미구현 |
| Redis 큐 작업 보존 | Celery 기본 동작 |
| pg_dump 일 1회 백업 | 미구현 |
| LLM 타임아웃 30초 | 미확인 |
| 디스크 80% 경고 | 미구현 |

---

## 9. PRD v1.8과의 교차 구현 사항

현재 코드베이스에는 PRD v1.6에 없지만 이전 PRD v1.8(통합 PRD)에서 유래한 기능이 다수 포함되어 있다.

| 기능 | PRD v1.6 | PRD v1.8 | 현재 구현 |
|------|---------|---------|----------|
| ManualRefinedDocument | 없음 | 있음 | **구현됨** |
| ProtectionDetector | 없음 | 있음 | **구현됨** |
| ProcessingCapability 분류 | 없음 | 있음 | **구현됨** |
| SanitizedKnowledge | 없음 | 있음 | **구현됨** |
| MetricLogEvidence | 없음 | 있음 | **구현됨** |
| DocumentProcessingAttempt | 없음 | 있음 | **구현됨** |
| DocumentRelation | 없음 | 있음 | **구현됨** |
| 감사 로그 (AuditLog) | /system 하위 | 별도 PRD | **구현됨** (별도 /audit) |
| 이벤트 채팅 (EventChatService) | 없음 | 있음 | **구현됨** |
| 이벤트 분석 보고 (AnalysisService) | 없음 | 있음 | **구현됨** |
| Zabbix Webhook 수신 | /integration 하위 | 있음 | **구현됨** (/incident/webhook/zabbix) |

---

## 10. 구현 우선순위 권장

PRD v1.6 기준으로 미구현 항목을 우선순위별로 정리한다.

### Phase 1: P1 필수 기능 보완 (Critical)

| # | 항목 | 예상 규모 | 이유 |
|---|------|---------|------|
| 1 | 의미 기반 청킹 + 섹션 제목 추출 실제 구현 | L | 현재 텍스트 추출이 placeholder |
| 2 | 문서 파싱 라이브러리 확충 (PyMuPDF, openpyxl, python-pptx, helper_hwp) | M | PDF 외 포맷 파싱 불가 |
| 3 | PGroonga 설치 + 한국어 전문 검색 | L | 검색 품질 핵심 |
| 4 | 3-way 하이브리드 검색 + RRF 구현 | L | PRD 검색 아키텍처 핵심 |
| 5 | PydanticAI 기반 Agentic RAG 구현 | XL | PRD 채팅 아키텍처 핵심 |
| 6 | SSE 스트리밍 응답 | M | 채팅 UX 핵심 |
| 7 | 대화 이력 관리 (conversations/messages) | M | 채팅 지속성 |
| 8 | 문서 관리 UI (목록, 업로드, 상태) | L | 사용자 진입점 |
| 9 | 검색 UI | M | 핵심 사용자 기능 |
| 10 | 채팅 전용 UI | M | 핵심 사용자 기능 |

### Phase 2: P2 중요 기능 (Important)

| # | 항목 | 예상 규모 |
|---|------|---------|
| 11 | BGE-m3 임베딩 서비스 (HuggingFace TEI) 전환 | L |
| 12 | Apache AGE 설치 + Graph 관계 모델링 | XL |
| 13 | Gotenberg 컨테이너 추가 + 레거시 포맷 변환 | M |
| 14 | IMAP 이메일 수집 | XL |
| 15 | 문서 버전 관리 (version_group_id, is_latest) | L |
| 16 | 담당자 관리 (persons 테이블 + API + UI) | M |
| 17 | 문서 카테고리 별도 테이블 관리 | S |
| 18 | 인프라 관리 UI | L |
| 19 | 장애 보고 시스템 연동 API (/integration) | L |
| 20 | Sparse 벡터 (SPARSEVEC) 추가 | M |

### Phase 3: P3 후순위 (Nice to have)

| # | 항목 | 예상 규모 |
|---|------|---------|
| 21 | 사용자 인증 (JWT, users 테이블) | M |
| 22 | Ollama / AWS Bedrock LLM 전환 | M |
| 23 | LLM 설정 UI (/system/llm-config) | S |
| 24 | API Key 관리 | S |
| 25 | 시스템 헬스체크/통계 대시보드 | M |

---

## 부록: 파일 구조 비교

```
PRD v1.6 아키텍처             현재 구현
─────────────────             ────────────
Next.js (프론트)              Vite + React (프론트)
FastAPI + PydanticAI          FastAPI (PydanticAI 없음)
ARQ Worker                    Celery Worker
Redis                         Redis
PostgreSQL 17                 PostgreSQL 16
  + pgvector                    + pgvector
  + Apache AGE                  (없음)
  + PGroonga                    (없음)
BGE-m3 (TEI)                  OpenAI Embedding API
Gotenberg                     (없음)
Ollama (Gemma 4)              OpenAI GPT-4o
로컬 디스크                    MinIO S3
```
