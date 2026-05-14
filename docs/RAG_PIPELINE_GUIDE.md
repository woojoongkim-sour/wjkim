# RAG 파이프라인 가이드

> 작성일: 2026-05-14  
> 문서 업로드 → 청킹 → 임베딩 → 검색 → AI 답변 전체 흐름을 알기 쉽게 설명합니다.

---

## 개요

이 시스템은 **"문서를 AI가 읽을 수 있게 가공해놓고, 나중에 질문하면 관련 부분만 찾아서 답변해주는"** 구조입니다.  
도서관에 비유하면 이해하기 쉽습니다.

---

## 1단계: 문서 업로드 — "도서관에 책 입고"

```
사용자가 PDF/DOCX/PPTX 등을 업로드
         │
         ▼
   MinIO(S3)에 원본 파일 저장
   + DB에 문서 레코드 생성
   + Celery 백그라운드 작업 큐잉
```

> **비유**: 새 책이 도서관에 도착한 것. 아직 서가에 꽂기 전, 창고에 원본 보관.

**담당 코드**: `app/api/documents.py` → `app/workers/tasks.py`

---

## 2단계: 텍스트 추출 — "책 내용을 텍스트로 옮기기"

```
백그라운드에서 자동 시작
         │
         ▼
   PDF → PyMuPDF로 텍스트 추출
   DOCX → python-docx로 추출
   PPTX → python-pptx로 추출
```

> **비유**: 책을 스캔해서 디지털 텍스트로 변환하는 과정. 암호가 걸린 책은 "수동 정제 필요" 상태로 표시.

**담당 코드**: `app/services/document_processor.py`

---

## 3단계: 청킹 (Chunking) — "책을 카드 크기로 잘라서 색인 카드 만들기"

```
추출된 텍스트 (예: 3000자)
         │
         ▼
   1000자씩 자르되, 200자는 겹치게

   Chunk 0: [0 ~ 1000자]
   Chunk 1: [800 ~ 1800자]    ← 200자 겹침!
   Chunk 2: [1600 ~ 2600자]   ← 200자 겹침!
   Chunk 3: [2400 ~ 3000자]
```

> **비유**: 두꺼운 책을 A5 크기 색인 카드로 분리. 카드끼리 앞뒤 내용이 살짝 겹치게 해서 **문맥이 끊기지 않도록** 함.
>
> **왜 겹치게?**: "장애 원인은..." 으로 끝나는 카드와 "...네트워크 장비 고장이었다" 로 시작하는 다음 카드가 따로 놀면 의미 파악이 안 되니까, 200자를 겹쳐서 연결성을 유지.

**담당 코드**: `app/services/document_processor.py` → `_chunk_content()`

**설정값** (`.env` 또는 `app/core/config.py`):
- `CHUNK_SIZE`: 1000 (청크 크기, 문자 수)
- `CHUNK_OVERLAP`: 200 (오버랩 크기, 문자 수)

---

## 4단계: 벡터 임베딩 — "각 카드에 좌표를 찍기"

```
각 청크 텍스트
         │
         ▼
   BGE-m3 모델(HuggingFace TEI)에 전송
         │
         ├── Dense Vector (1024차원)  → "의미의 좌표"
         └── Sparse Vector (250,002차원) → "단어 출현 빈도"
         │
         ▼
   PostgreSQL(pgvector)에 벡터와 함께 저장
   문서 상태 → READY_FOR_SEARCH
```

> **비유**: 색인 카드마다 **"의미 좌표"** 를 매긴 것.
>
> - **Dense 벡터**: "이 카드는 의미적으로 어디에 위치하는가?"를 1024개 숫자로 표현. "PostgreSQL 장애"와 "DB 문제"가 **비슷한 좌표**를 가짐 → **의미 검색** 가능
> - **Sparse 벡터**: "이 카드에 어떤 단어가 얼마나 나오는가?"를 기록 → **정확한 키워드 매칭** 가능
>
> 이 두 벡터 덕분에 "DB가 안 돼요"라고 검색해도 "PostgreSQL 장애 복구"가 포함된 카드를 찾을 수 있음.

**담당 코드**: `app/services/document_processor.py` → `_create_chunks_with_embeddings()`, `app/services/embedding.py`

**임베딩 서비스 설정** (`.env` 또는 `app/core/config.py`):
- `EMBEDDING_API_URL`: `http://localhost:8080` (BGE-m3 TEI 서비스 주소)
- `EMBEDDING_DIMENSION`: 1024 (Dense 벡터 차원)

---

## 5단계: 3-Way 하이브리드 검색 — "세 명의 사서가 동시에 찾기"

```
사용자: "PostgreSQL 장애 대응 방법?"
         │
         ▼
   쿼리도 임베딩 변환 (같은 BGE-m3 모델)
         │
         ▼
   3가지 검색을 동시에 실행:

   Dense 검색 (가중치 50%): 의미가 비슷한 카드 찾기
   Sparse 검색 (가중치 30%): 단어 구성이 비슷한 카드 찾기
   Keyword 검색 (가중치 20%): 정확히 그 단어가 있는 카드 찾기
         │
         ▼
   RRF(순위 융합)로 3개 결과를 합산 → 최종 랭킹
```

> **비유**:
> - **Dense 사서**: "고객님, '장애 대응'이라고 하셨는데 '트러블슈팅', '복구 절차' 같은 것도 포함해서 찾을게요" (의미 이해)
> - **Sparse 사서**: "장애, 대응, PostgreSQL 이 단어가 많이 나오는 카드 위주로 찾을게요" (단어 빈도)
> - **Keyword 사서**: "정확히 'PostgreSQL 장애 대응' 이 문구가 들어간 카드 찾을게요" (정확 매칭, 한국어 형태소 분석)
>
> 세 사서의 결과를 가중치로 합산해서 **가장 관련 높은 카드들을 선별**.

**담당 코드**: `app/services/hybrid_search.py` → `HybridSearchService.search()`

**RRF 설정** (`app/services/hybrid_search.py` 상단 상수):
- `RRF_K = 60`
- `DENSE_WEIGHT = 0.5`, `SPARSE_WEIGHT = 0.3`, `KEYWORD_WEIGHT = 0.2`
- `DENSE_SCORE_THRESHOLD = 0.4` (이 점수 미만이면 multi-step으로 전환)

---

## 6단계: Adaptive RAG → AI 답변 생성 — "찾은 카드를 AI에게 주고 대답하게 하기"

```
검색된 상위 청크들
         │
         ▼
   복잡도 자동 판단 (Gemini LLM)
         │
   ┌─────┴─────┐
   │            │
 간단한 질문   복잡한 질문
   │            │
   ▼            ▼
 검색 1회     쿼리 분해 → 여러 번 검색
   │            │
   └─────┬─────┘
         │
         ▼
   Gemini에게 전달:
   "당신은 MSP 운영 전문가입니다.
    아래 문서를 참고하여 답변하세요:
    [청크1] [청크2] [청크3]...

    질문: PostgreSQL 장애 대응 방법?"
         │
         ▼
   근거 문서를 인용한 한국어 답변 반환
```

> **비유**:
> - **간단한 질문** ("김 대리 전화번호?"): 한 번 찾아서 바로 답변
> - **복잡한 질문** ("지난 3개월 DB 장애 패턴 비교"): 질문을 쪼개서 → "DB 장애 유형", "대응 절차", "복구 명령어" 각각 검색 → 결과 종합 → 답변
>
> AI(Gemini)는 **자기 지식이 아니라, 검색된 문서 내용을 근거로** 답변함. 그래서 답변에 "출처: PostgreSQL 운영 가이드 3페이지" 같은 근거가 붙음.

**담당 코드**: `app/services/agentic_rag.py` → `AdaptiveRAGOrchestrator.process()`

**Gemini LLM 설정** (`.env` 또는 `app/core/config.py`):
- `GEMINI_API_KEY`: Google Gemini API 키
- `GEMINI_MODEL`: `gemini-2.5-flash`
- `GEMINI_BASE_URL`: `https://generativelanguage.googleapis.com/v1beta/openai/`
- `AGENT_MAX_TOOL_CALLS`: 5 (최대 검색 횟수)

---

## 전체 흐름 한 줄 요약

```
📄 문서 업로드 → ✂️ 1000자씩 자르기 → 📐 벡터 좌표 매기기 → 💾 DB 저장
                                                                    ↓
🙋 질문 → 🔍 세 가지 방법으로 관련 조각 찾기 → 🤖 AI가 조각 읽고 답변 생성 → 💬 답변
```

**핵심 포인트**: AI가 "아는 척"하는 게 아니라, **실제로 우리 문서에서 찾은 내용**을 기반으로 답변하기 때문에 할루시네이션(거짓 답변)이 줄어들고, 출처를 명시할 수 있습니다. 이것이 RAG(Retrieval-Augmented Generation)의 핵심 가치입니다.

---

## 데이터 저장 위치 요약

| 데이터 | 저장 위치 | 설명 |
|--------|-----------|------|
| 원본 파일 (PDF 등) | **MinIO** (S3 호환 오브젝트 스토리지) | 경로: `customers/{id}/original/{filename}` |
| 문서 메타데이터 | **PostgreSQL** `documents` 테이블 | 제목, 상태, 해시 등 |
| 청크 텍스트 | **PostgreSQL** `document_chunks.content` | 1000자 단위 텍스트 |
| Dense 벡터 | **PostgreSQL** `document_chunks.dense_vector` | pgvector `Vector(1024)` 타입 |
| Sparse 벡터 | **PostgreSQL** `document_chunks.sparse_vector` | pgvector `SPARSEVEC(250002)` 타입 |

> Gemini LLM은 DB에 직접 접근하지 않습니다.  
> 앱이 DB에서 검색 결과를 가져온 뒤, API 호출 시 **프롬프트의 컨텍스트로 텍스트를 전달**합니다.
