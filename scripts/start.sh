#!/bin/bash
# ============================================================
# DocSearch AI - 시작 스크립트
# ============================================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║           DocSearch AI - 온프레미스 문서 검색 시스템           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 환경 파일 확인
if [ ! -f .env ]; then
    echo -e "${YELLOW}[!] .env 파일이 없습니다. .env.example에서 복사합니다...${NC}"
    cp .env.example .env
    echo -e "${GREEN}[✓] .env 파일이 생성되었습니다. 필요에 따라 수정하세요.${NC}"
fi

# 필요한 디렉토리 생성
mkdir -p docker/ssl

# 기능 선택
echo ""
echo "실행할 작업을 선택하세요:"
echo "  1) 전체 스택 시작 (Docker Compose)"
echo "  2) 개발 모드로 시작 (로컬)"
echo "  3) LLM 모델 다운로드 (Ollama)"
echo "  4) 데이터베이스 마이그레이션"
echo "  5) 시스템 상태 확인"
echo "  6) 종료"
echo ""
read -p "선택 (1-6): " choice

case $choice in
    1)
        echo -e "\n${BLUE}[*] Docker Compose로 전체 스택을 시작합니다...${NC}\n"
        
        # NVIDIA Docker 런타임 확인
        if ! docker info 2>/dev/null | grep -q "nvidia"; then
            echo -e "${YELLOW}[!] NVIDIA Docker 런타임이 감지되지 않았습니다.${NC}"
            echo -e "${YELLOW}    GPU 가속이 필요하면 nvidia-container-toolkit을 설치하세요.${NC}"
        fi
        
        # 이미지 빌드 및 시작
        docker compose up -d --build
        
        echo -e "\n${GREEN}[✓] 시스템이 시작되었습니다!${NC}"
        echo ""
        echo "접속 주소:"
        echo "  - 프론트엔드: http://localhost:3000"
        echo "  - API: http://localhost:8000"
        echo "  - API 문서: http://localhost:8000/docs"
        echo "  - MinIO 콘솔: http://localhost:9001"
        echo ""
        echo -e "${YELLOW}[!] 첫 실행 시 Ollama 모델을 다운로드하세요 (옵션 3)${NC}"
        ;;
        
    2)
        echo -e "\n${BLUE}[*] 개발 모드로 시작합니다...${NC}\n"
        
        # 의존성 서비스만 시작
        echo -e "${YELLOW}[*] 의존성 서비스 시작 (PostgreSQL, Redis, Qdrant, MinIO, Ollama)...${NC}"
        docker compose up -d postgres redis qdrant minio ollama
        
        # Python 가상환경 확인
        if [ ! -d ".venv" ]; then
            echo -e "${YELLOW}[*] Python 가상환경 생성 중...${NC}"
            python3 -m venv .venv
        fi
        
        source .venv/bin/activate
        
        echo -e "${YELLOW}[*] Python 패키지 설치 중...${NC}"
        pip install -r requirements.txt
        
        echo -e "\n${GREEN}[✓] 개발 환경 준비 완료!${NC}"
        echo ""
        echo "실행 명령어:"
        echo "  API 서버:  python -m uvicorn app.main:app --reload"
        echo "  Worker:    celery -A app.worker worker -l INFO -Q documents,gpu -c 1"
        echo "  Frontend:  cd frontend && npm install && npm run dev"
        ;;
        
    3)
        echo -e "\n${BLUE}[*] Ollama 모델을 다운로드합니다...${NC}\n"
        
        # Ollama 컨테이너 확인
        if ! docker ps | grep -q "docsearch-ollama"; then
            echo -e "${YELLOW}[*] Ollama 컨테이너 시작 중...${NC}"
            docker compose up -d ollama
            sleep 5
        fi
        
        echo -e "${YELLOW}[*] Qwen2.5-7B 모델 다운로드 중 (약 4GB)...${NC}"
        docker exec -it docsearch-ollama ollama pull qwen2.5:7b-instruct-q4_K_M
        
        echo -e "\n${GREEN}[✓] 모델 다운로드 완료!${NC}"
        ;;
        
    4)
        echo -e "\n${BLUE}[*] 데이터베이스 마이그레이션을 실행합니다...${NC}\n"
        
        # 가상환경 활성화
        if [ -d ".venv" ]; then
            source .venv/bin/activate
        fi
        
        # Alembic 마이그레이션
        alembic upgrade head
        
        echo -e "\n${GREEN}[✓] 마이그레이션 완료!${NC}"
        ;;
        
    5)
        echo -e "\n${BLUE}[*] 시스템 상태를 확인합니다...${NC}\n"
        
        # 컨테이너 상태
        echo "Docker 컨테이너 상태:"
        docker compose ps
        
        echo ""
        
        # API 헬스체크
        echo "API 헬스체크:"
        curl -s http://localhost:8000/health/ready 2>/dev/null | python3 -m json.tool || echo "  API에 연결할 수 없습니다"
        
        echo ""
        
        # GPU 상태
        echo "GPU 상태:"
        nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv 2>/dev/null || echo "  GPU를 감지할 수 없습니다"
        ;;
        
    6)
        echo -e "${GREEN}종료합니다.${NC}"
        exit 0
        ;;
        
    *)
        echo -e "${RED}잘못된 선택입니다.${NC}"
        exit 1
        ;;
esac
