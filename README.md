# DocSearch AI

DocSearch AI는 사내 문서를 업로드하고, 로컬 LLM 기반 RAG로 검색과 질의응답을 제공하는 온프레미스 문서 검색 플랫폼입니다.

`main` 브랜치는 기존 V1 프로토타입을 유지하고, `develop` 브랜치는 새 서비스 아키텍처를 기준으로 재구축을 진행합니다.

현재 기준 서비스 구성은 다음과 같습니다.

- `frontend`: React + TypeScript + Vite + Ant Design 웹 UI
- `gateway`: Nginx 리버스 프록시
- `backend`: FastAPI API 서버
- `worker`: 비동기 인덱싱 워커 경계
- `postgres`: 메타데이터 저장소
- `redis`: 캐시 및 작업 큐
- `qdrant`: 벡터 데이터베이스
- `minio`: 원본 문서 저장소
- `llm`: 로컬 추론 엔드포인트

## 저장소 구조

```text
backend/             FastAPI 서비스
frontend/            React 웹 애플리케이션
infra/compose/       Docker Compose 실행 구성
infra/nginx/         게이트웨이 설정
docs/                설계 및 계획 문서
```

## 빠른 실행

```bash
docker compose -f infra/compose/docker-compose.yml up --build
```

로컬 기본 주소:

- 앱 게이트웨이: `http://localhost:8080`
- 백엔드 문서: `http://localhost:8000/docs`
- 프론트엔드 개발 서버: `http://localhost:5173`
- MinIO 콘솔: `http://localhost:9001`

## 현재 범위

현재 기준선에는 서비스 경계, 상태 확인 엔드포인트, 로컬 실행 설정, CI, API Key 기반 워크스페이스 인증, 그리고 문서 업로드와 원본 저장 경계가 포함되어 있습니다. 인덱싱, 검색, 리랭킹, 출처 포함 답변 흐름은 이후 브랜치에서 순차적으로 추가합니다.
