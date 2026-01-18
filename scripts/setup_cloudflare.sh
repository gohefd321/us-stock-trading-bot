#!/bin/bash

# Cloudflare Tunnel 설정 스크립트
# 이 스크립트는 Cloudflare Tunnel 사용을 위한 환경 변수를 설정합니다

set -e

echo "==========================================="
echo "  Cloudflare Tunnel 설정"
echo "==========================================="
echo ""

# 도메인 입력 받기
read -p "도메인을 입력하세요 (예: stocking.daechanserver.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo "오류: 도메인을 입력해야 합니다."
    exit 1
fi

# 프로토콜 선택
echo ""
echo "배포 환경을 선택하세요:"
echo "1) 프로덕션 (HTTPS)"
echo "2) 개발 (HTTP)"
read -p "선택 (1 또는 2): " ENV_CHOICE

if [ "$ENV_CHOICE" = "1" ]; then
    PROTOCOL="https"
    echo "프로덕션 모드 (HTTPS) 선택됨"
elif [ "$ENV_CHOICE" = "2" ]; then
    PROTOCOL="http"
    echo "개발 모드 (HTTP) 선택됨"
else
    echo "오류: 1 또는 2를 선택해야 합니다."
    exit 1
fi

# 배포 방식 선택
echo ""
echo "배포 방식을 선택하세요:"
echo "1) 같은 도메인 (권장 - CORS 문제 없음)"
echo "2) 서브도메인 분리"
read -p "선택 (1 또는 2): " DEPLOY_CHOICE

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 백엔드 .env 파일 업데이트
echo ""
echo "백엔드 환경 변수 설정 중..."

BACKEND_ENV="${PROJECT_ROOT}/.env"

# 기존 .env 파일이 없으면 .env.example에서 복사
if [ ! -f "$BACKEND_ENV" ]; then
    cp "${PROJECT_ROOT}/.env.example" "$BACKEND_ENV"
    echo ".env 파일이 생성되었습니다."
fi

# CORS_ORIGINS 업데이트
if [ "$DEPLOY_CHOICE" = "1" ]; then
    # 같은 도메인
    CORS_ORIGINS="${PROTOCOL}://${DOMAIN},http://localhost:5173,http://localhost:3000"

    # 프론트엔드 환경 변수 설정
    echo ""
    echo "프론트엔드 환경 변수 설정 중..."
    FRONTEND_ENV="${PROJECT_ROOT}/frontend/.env"
    cat > "$FRONTEND_ENV" <<EOF
# Backend API URL
# 빈 값 = 상대 URL 사용 (같은 도메인에서 Cloudflare Tunnel 사용 시)
VITE_API_URL=

# 개발 모드 프록시 타겟
VITE_BACKEND_TARGET=http://localhost:8000
EOF

    echo ""
    echo "==========================================="
    echo "  설정 완료!"
    echo "==========================================="
    echo ""
    echo "Cloudflare Tunnel config.yml 예시:"
    echo ""
    echo "ingress:"
    echo "  - hostname: ${DOMAIN}"
    echo "    path: /api/*"
    echo "    service: http://localhost:8000"
    echo "  - hostname: ${DOMAIN}"
    echo "    path: /health"
    echo "    service: http://localhost:8000"
    echo "  - hostname: ${DOMAIN}"
    echo "    path: /docs"
    echo "    service: http://localhost:8000"
    echo "  - hostname: ${DOMAIN}"
    echo "    service: http://localhost:5173"
    echo "  - service: http_status:404"
    echo ""

else
    # 서브도메인 분리
    read -p "백엔드 서브도메인을 입력하세요 (예: api): " SUBDOMAIN
    if [ -z "$SUBDOMAIN" ]; then
        SUBDOMAIN="api"
    fi

    BACKEND_DOMAIN="${SUBDOMAIN}.${DOMAIN}"
    CORS_ORIGINS="${PROTOCOL}://${DOMAIN},http://localhost:5173,http://localhost:3000"

    # 프론트엔드 환경 변수 설정
    echo ""
    echo "프론트엔드 환경 변수 설정 중..."
    FRONTEND_ENV="${PROJECT_ROOT}/frontend/.env"
    cat > "$FRONTEND_ENV" <<EOF
# Backend API URL
VITE_API_URL=${PROTOCOL}://${BACKEND_DOMAIN}

# 개발 모드 프록시 타겟
VITE_BACKEND_TARGET=http://localhost:8000
EOF

    echo ""
    echo "==========================================="
    echo "  설정 완료!"
    echo "==========================================="
    echo ""
    echo "Cloudflare Tunnel config.yml 예시:"
    echo ""
    echo "ingress:"
    echo "  - hostname: ${BACKEND_DOMAIN}"
    echo "    service: http://localhost:8000"
    echo "  - hostname: ${DOMAIN}"
    echo "    service: http://localhost:5173"
    echo "  - service: http_status:404"
    echo ""
fi

# CORS_ORIGINS 업데이트
if grep -q "^CORS_ORIGINS=" "$BACKEND_ENV"; then
    # macOS와 Linux 모두 호환
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|^CORS_ORIGINS=.*|CORS_ORIGINS=${CORS_ORIGINS}|" "$BACKEND_ENV"
    else
        sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=${CORS_ORIGINS}|" "$BACKEND_ENV"
    fi
else
    echo "CORS_ORIGINS=${CORS_ORIGINS}" >> "$BACKEND_ENV"
fi

echo "CORS_ORIGINS=${CORS_ORIGINS}"
echo ""
echo "다음 단계:"
echo "1. Cloudflare Tunnel을 위 설정으로 시작하세요"
echo "2. 개발 서버를 시작하세요: ./scripts/run_dev.sh"
echo "3. 브라우저에서 접속하세요: ${PROTOCOL}://${DOMAIN}"
echo ""
echo "자세한 가이드는 CLOUDFLARE_TUNNEL_SETUP.md 파일을 참조하세요."
