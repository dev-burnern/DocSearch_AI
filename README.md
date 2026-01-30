# DocSearch AI - 온프레미스 문서 검색 RAG 서버

온프레미스(사내망) 환경을 위한 문서 검색 RAG(Retrieval-Augmented Generation) 서버입니다.
외부 API 호출 없이 완전한 로컬 환경에서 동작하며, 강력한 보안과 한국어 최적화를 제공합니다.

## 📋 주요 기능

- **다양한 문서 형식 지원**: PDF, DOCX, XLSX, PPTX, TXT, MD, HWP, 이미지
- **하이브리드 검색**: Dense + Sparse 벡터 결합으로 정확한 검색
- **RAG 채팅**: 문서 기반 질의응답 (출처 표시)
- **한국어 최적화**: Kiwi 형태소 분석기, BGE-M3 다국어 임베딩
- **보안**: JWT 인증, RBAC 권한 관리, 감사 로그, 데이터 암호화
- **OCR**: 스캔 문서 및 이미지에서 텍스트 추출

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                        │
├─────────────────────────────────────────────────────────────────┤
│                           Nginx                                 │
├─────────────────────────────────────────────────────────────────┤
│                    FastAPI Backend                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐     │
│  │  Auth   │  │ Search  │  │  Chat   │  │ Document Upload │     │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘     │
├─────────────────────────────────────────────────────────────────┤
│                     Celery Workers (GPU)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Embedding  │  │  Reranking  │  │  Text Extraction + OCR  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│ PostgreSQL │  Redis  │  Qdrant   │  MinIO  │     Ollama         │
│ (Metadata) │ (Cache) │ (Vectors) │ (Files) │ (LLM: Qwen2.5)     │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 기술 스택

| 컴포넌트 | 기술 | 용도 |
|---------|------|------|
| Backend | FastAPI | REST API 서버 |
| Database | PostgreSQL 16 | 메타데이터, 권한, 감사 로그 |
| Vector DB | Qdrant | 벡터 저장 및 하이브리드 검색 |
| Cache | Redis 7 | 캐시, 작업 큐 브로커 |
| Storage | MinIO | 문서 파일 저장 |
| Embedding | BGE-M3 | 다국어 Dense + Sparse 임베딩 |
| Reranker | BGE-Reranker-v2-m3 | 검색 결과 재순위화 |
| LLM | Ollama + Qwen2.5-7B | 응답 생성 |
| Worker | Celery | 비동기 문서 처리 |
| Frontend | React + TypeScript + Ant Design | 사용자 인터페이스 |

## 💻 시스템 요구사항

### 최소 사양
- **CPU**: 8코어 이상
- **RAM**: 32GB
- **GPU**: NVIDIA RTX 3080 (10GB VRAM) 이상
- **Storage**: SSD 500GB
- **OS**: Ubuntu 22.04 LTS

### 권장 사양
- **CPU**: 16코어 이상
- **RAM**: 64GB
- **GPU**: NVIDIA RTX 4090 (24GB VRAM)
- **Storage**: NVMe SSD 1TB
- **OS**: Ubuntu 22.04/24.04 LTS

## 🚀 빠른 시작

### 1. 저장소 클론
```bash
git clone https://github.com/dev-burnern/docsearch-ai.git
cd docsearch-ai
```

### 2. 환경 설정
```bash
cp .env.example .env
# .env 파일에서 비밀번호 등을 수정하세요
```

### 3. Docker Compose로 실행
```bash
# 시작 스크립트 실행
chmod +x scripts/start.sh
./scripts/start.sh

# 또는 직접 Docker Compose 실행
docker-compose up -d
```

### 4. LLM 모델 다운로드
```bash
docker exec -it docsearch-ollama ollama pull qwen2.5:7b-instruct-q4_K_M
```

### 5. 접속
- **프론트엔드**: http://localhost:3000
- **API 문서**: http://localhost:8000/docs
- **MinIO 콘솔**: http://localhost:9001

## 📁 프로젝트 구조

```
docsearch-ai/
├── app/
│   ├── core/           # 설정, 보안
│   ├── db/             # 데이터베이스 모델
│   ├── routers/        # API 엔드포인트
│   ├── services/       # 비즈니스 로직
│   ├── extraction/     # 텍스트 추출
│   ├── chunking/       # 텍스트 청킹
│   ├── search/         # 검색 파이프라인
│   ├── llm/            # LLM 서비스
│   ├── worker/         # Celery 작업
│   └── main.py         # FastAPI 앱
├── frontend/
│   ├── src/
│   │   ├── api/        # API 클라이언트
│   │   ├── stores/     # 상태 관리
│   │   ├── pages/      # 페이지 컴포넌트
│   │   └── layouts/    # 레이아웃
│   └── package.json
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   ├── nginx.conf
│   └── init-db.sql
├── scripts/
│   └── start.sh
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 🔒 보안 기능

- **JWT 인증**: Access Token + Refresh Token
- **RBAC 권한 관리**: Admin, Manager, User, Viewer 역할
- **문서 보안등급**: Public, Internal, Confidential, Restricted
- **감사 로그**: 모든 사용자 활동 기록
- **데이터 암호화**: MinIO 서버측 암호화

## 📊 성능 지표

| 메트릭 | 목표 | 비고 |
|--------|------|------|
| 검색 응답 시간 | < 500ms | 10만 청크 기준 |
| RAG 응답 시간 | < 5초 | LLM 생성 포함 |
| 문서 처리 속도 | 10페이지/분 | GPU 사용 시 |
| 동시 사용자 | 1-2명 | 권장 설정 기준 |

## 🛠️ 개발 모드

```bash
# 의존성 서비스 시작
docker-compose up -d postgres redis qdrant minio ollama

# Python 환경 설정
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# API 서버 실행 (개발 모드)
uvicorn app.main:app --reload

# Celery 워커 실행
celery -A app.worker worker -l INFO -Q documents,gpu -c 1

# 프론트엔드 실행
cd frontend
npm install
npm run dev
```

## 📝 API 예시

### 문서 업로드
```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf" \
  -F "classification=internal"
```

### 검색
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "프로젝트 일정", "top_n": 5}'
```

### RAG 채팅
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "계약서의 주요 조건은?", "use_rerank": true}'
```

## 📄 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

## 🤝 기여

이슈와 PR을 환영합니다!

---

© 2024 DocSearch AI Team
