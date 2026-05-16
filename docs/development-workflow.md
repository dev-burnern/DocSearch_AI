# DocSearch AI 개발 워크플로우

## 브랜치 모델

- `main`
  - 기존 V1 프로토타입을 보존합니다.
  - 릴리스 기준 브랜치로만 사용합니다.
  - 직접 기능 개발을 진행하지 않습니다.
- `develop`
  - 재구축 작업의 통합 브랜치입니다.
  - 모든 기능 브랜치는 `develop`에서 시작합니다.
  - 리뷰가 끝난 변경 사항은 `develop`으로 병합합니다.

## 브랜치 이름 규칙

작업 브랜치는 항상 타입 접두사를 사용합니다.

- `feat/<scope>`
- `fix/<scope>`
- `chore/<scope>`
- `docs/<scope>`
- `refactor/<scope>`
- `test/<scope>`

예시:

- `chore/workflow`
- `feat/scaffold`
- `feat/auth`
- `feat/ingestion`
- `feat/retrieval`
- `fix/search-filter`

## PR 규칙

- 모든 PR의 대상 브랜치는 `develop`입니다.
- `main`은 검토된 통합 결과만 받습니다.
- 하나의 PR에는 하나의 관심사만 담습니다.
- 한 번에 리뷰할 수 있을 정도로 PR을 작게 유지합니다.
- 다음 작업이 이전 작업에 의존하면 스택형 PR을 선호합니다.

권장 크기:

- 가능하면 변경 라인 400줄 이하
- 가능하면 변경 파일 10개 이하
- 인프라, API, 저장소, UI 변경이 섞이기 시작하면 일찍 분리

## 커밋 규칙

커밋 메시지는 conventional commits 형식을 사용하되, 설명은 한글로 작성합니다.

- `feat(scope): 요약`
- `fix(scope): 요약`
- `chore(scope): 요약`
- `docs(scope): 요약`
- `refactor(scope): 요약`
- `test(scope): 요약`

예시:

- `feat(scaffold): 백엔드 기준선 추가`
- `feat(auth): API Key 검증 추가`
- `chore(infra): 런타임 구조와 CI 재정비`
- `docs(scaffold): 저장소 개요 갱신`

각 커밋은 한 가지 일만 합니다.

1. 실패하는 테스트 추가
2. 최소 구현 추가
3. 동작 변경 없는 리팩터링
4. 동작 변경에 맞춘 문서 또는 설정 갱신

## 병합 규칙

- 기능 브랜치는 리뷰 후 `develop`으로 병합합니다.
- 가능하면 선형 히스토리를 유지합니다.
- 리뷰가 시작된 뒤에는 필요한 경우가 아니면 force push를 피합니다.
- 리뷰가 끝난 내용은 히스토리 재작성보다 후속 커밋으로 보완합니다.

## 리뷰 순서

재구축은 다음 순서로 리뷰합니다.

1. 워크플로우와 계획
2. 스캐폴드와 런타임 경계
3. API Key 인증과 요청 컨텍스트
4. 문서 업로드와 저장소
5. 인덱싱 워커와 큐 추상화
6. 검색과 리랭킹
7. 로컬 LLM 게이트웨이
8. 채팅과 출처 포함 응답
9. 프론트엔드 플로우
10. 관측성과 하드닝

## 초기 브랜치 계획

- `develop`
- `chore/workflow`
- `feat/scaffold`
- `feat/auth`
- `feat/ingestion`
- `feat/indexing-worker`
- `feat/retrieval`
- `feat/llm-gateway`
- `feat/chat-api`
- `feat/frontend-shell`
- `chore/observability`
- `fix/hardening`

## 리뷰 체크리스트

PR 생성 전:

- 브랜치 이름이 타입 규칙을 따르는지 확인합니다.
- 커밋 히스토리가 관심사별로 분리되어 있는지 확인합니다.
- 변경 영역의 테스트를 실행합니다.
- 동작이 바뀌면 문서도 함께 갱신합니다.
- PR 본문에 범위, 제외 범위, 검증 결과를 적습니다.

`develop` 병합 전:

- 관련 없는 파일 변경이 없는지 확인합니다.
- PR 범위를 벗어난 리팩터링이 없는지 확인합니다.
- 후속 작업은 별도 브랜치로 명시적으로 넘깁니다.
