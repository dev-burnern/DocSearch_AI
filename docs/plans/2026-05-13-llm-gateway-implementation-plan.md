# LLM 게이트웨이 구현 계획

## 1단계: 테스트 기준선

- 기본 vLLM 모델 프로필이 환경 변수 기본값을 반영하는지 테스트합니다.
- 환경 변수 오버라이드가 프로필에 반영되는지 테스트합니다.
- OpenAI 호환 채팅 요청 페이로드가 올바르게 전송되는지 테스트합니다.
- HTTP 실패와 비정상 응답이 `LLMProviderError`로 변환되는지 테스트합니다.

## 2단계: 내부 계약 추가

- `ChatMessage`, `LLMRequest`, `LLMResponse`를 정의합니다.
- LLM 클라이언트 구현체가 따라야 할 `LLMClient` 프로토콜을 정의합니다.
- 공급자 오류를 나타내는 `LLMProviderError`를 정의합니다.

## 3단계: vLLM 클라이언트 구현

- `httpx` 기반 동기 클라이언트를 사용합니다.
- API Key가 있으면 `Authorization: Bearer` 헤더를 붙입니다.
- 요청별 `max_tokens`, `temperature`가 있으면 프로필 기본값보다 우선합니다.
- 응답 `choices`, `message.content`, `usage`를 검증합니다.

## 4단계: 문서와 환경 예시 갱신

- `.env.example`에 LLM 런타임 설정을 추가합니다.
- README 현재 범위에 vLLM 게이트웨이를 반영합니다.
- 개발 워크플로우 문서를 한글 기준으로 정리합니다.
