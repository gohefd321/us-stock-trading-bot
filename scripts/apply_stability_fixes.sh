#!/bin/bash

# 안정화 수정사항 적용 스크립트
# 이 스크립트는 개선된 파일들을 원본 파일로 교체합니다

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==========================================="
echo "  안정화 수정사항 적용"
echo "==========================================="
echo ""
echo "프로젝트 경로: $PROJECT_ROOT"
echo ""

# 백업 디렉토리 생성
BACKUP_DIR="${PROJECT_ROOT}/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR/frontend/src/pages"
mkdir -p "$BACKUP_DIR/backend/app/services"

echo "백업 디렉토리: $BACKUP_DIR"
echo ""

# 프론트엔드 파일 백업 및 교체
echo "1. 프론트엔드 파일 교체 중..."
echo ""

if [ -f "${PROJECT_ROOT}/frontend/src/pages/Dashboard.tsx" ]; then
    echo "   - Dashboard.tsx 백업 중..."
    cp "${PROJECT_ROOT}/frontend/src/pages/Dashboard.tsx" "$BACKUP_DIR/frontend/src/pages/Dashboard.tsx"

    if [ -f "${PROJECT_ROOT}/frontend/src/pages/Dashboard_Improved.tsx" ]; then
        echo "   - Dashboard.tsx 교체 중..."
        cp "${PROJECT_ROOT}/frontend/src/pages/Dashboard_Improved.tsx" "${PROJECT_ROOT}/frontend/src/pages/Dashboard.tsx"
        echo "   ✓ Dashboard.tsx 교체 완료"
    else
        echo "   ⚠ Dashboard_Improved.tsx 파일이 없습니다"
    fi
else
    echo "   ⚠ 원본 Dashboard.tsx 파일이 없습니다"
fi

echo ""

if [ -f "${PROJECT_ROOT}/frontend/src/pages/Settings.tsx" ]; then
    echo "   - Settings.tsx 백업 중..."
    cp "${PROJECT_ROOT}/frontend/src/pages/Settings.tsx" "$BACKUP_DIR/frontend/src/pages/Settings.tsx"

    if [ -f "${PROJECT_ROOT}/frontend/src/pages/Settings_Improved.tsx" ]; then
        echo "   - Settings.tsx 교체 중..."
        cp "${PROJECT_ROOT}/frontend/src/pages/Settings_Improved.tsx" "${PROJECT_ROOT}/frontend/src/pages/Settings.tsx"
        echo "   ✓ Settings.tsx 교체 완료"
    else
        echo "   ⚠ Settings_Improved.tsx 파일이 없습니다"
    fi
else
    echo "   ⚠ 원본 Settings.tsx 파일이 없습니다"
fi

echo ""
echo "2. 백엔드 파일 교체 중..."
echo ""

if [ -f "${PROJECT_ROOT}/backend/app/services/portfolio_manager.py" ]; then
    echo "   - portfolio_manager.py 백업 중..."
    cp "${PROJECT_ROOT}/backend/app/services/portfolio_manager.py" "$BACKUP_DIR/backend/app/services/portfolio_manager.py"

    if [ -f "${PROJECT_ROOT}/backend/app/services/portfolio_manager_improved.py" ]; then
        echo "   - portfolio_manager.py 교체 중..."
        cp "${PROJECT_ROOT}/backend/app/services/portfolio_manager_improved.py" "${PROJECT_ROOT}/backend/app/services/portfolio_manager.py"
        echo "   ✓ portfolio_manager.py 교체 완료"
    else
        echo "   ⚠ portfolio_manager_improved.py 파일이 없습니다"
    fi
else
    echo "   ⚠ 원본 portfolio_manager.py 파일이 없습니다"
fi

echo ""
echo "==========================================="
echo "  적용 완료!"
echo "==========================================="
echo ""
echo "백업 위치: $BACKUP_DIR"
echo ""
echo "다음 단계:"
echo "1. 서버 재시작: ./scripts/run_dev.sh"
echo "2. 브라우저에서 테스트"
echo ""
echo "문제가 발생하면 다음 명령으로 롤백:"
echo "  cp $BACKUP_DIR/frontend/src/pages/Dashboard.tsx frontend/src/pages/Dashboard.tsx"
echo "  cp $BACKUP_DIR/frontend/src/pages/Settings.tsx frontend/src/pages/Settings.tsx"
echo "  cp $BACKUP_DIR/backend/app/services/portfolio_manager.py backend/app/services/portfolio_manager.py"
echo ""
