#!/bin/bash
# 원격 서버 배포 스크립트

echo "🚀 원격 서버 배포 시작..."

# 서버 정보 (사용자가 수정해야 함)
SERVER_USER="sixseven"
SERVER_HOST="your-server-ip"  # 실제 서버 IP 또는 도메인으로 변경
SERVER_PATH="/home/sixseven/us-stock-trading-bot"

echo "📦 변경된 파일 확인 중..."
git status

echo ""
echo "📤 원격 서버로 코드 전송 중..."
rsync -avz --exclude 'venv/' --exclude '__pycache__/' --exclude '*.pyc' --exclude '.git/' \
    . ${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/

echo ""
echo "📥 원격 서버에서 패키지 설치 중..."
ssh ${SERVER_USER}@${SERVER_HOST} << 'EOF'
cd /home/sixseven/us-stock-trading-bot/backend
source venv/bin/activate
pip install -U google-genai
pip install -r requirements.txt
echo "✅ 패키지 설치 완료"
EOF

echo ""
echo "🔄 서비스 재시작 중..."
ssh ${SERVER_USER}@${SERVER_HOST} << 'EOF'
# systemd 사용 시
# sudo systemctl restart trading-bot

# PM2 사용 시
# pm2 restart trading-bot

# 또는 수동 재시작
echo "서비스 재시작은 수동으로 진행해주세요:"
echo "  sudo systemctl restart trading-bot"
echo "  또는"
echo "  pm2 restart trading-bot"
EOF

echo ""
echo "✅ 배포 완료!"
echo ""
echo "다음 단계:"
echo "1. 원격 서버에 SSH 접속"
echo "2. 서비스 재시작 확인"
echo "3. 로그 확인: tail -f /var/log/trading-bot.log"
