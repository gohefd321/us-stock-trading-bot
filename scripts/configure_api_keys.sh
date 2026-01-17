#!/bin/bash

# API Key Configuration Script
# Interactive setup for US Stock Trading Bot

set -e

echo "================================================"
echo "    미국 주식 자동매매 시스템 - API 키 설정"
echo "================================================"
echo ""

# Check if .env already exists
if [ -f ".env" ]; then
    echo "⚠️  .env 파일이 이미 존재합니다."
    read -p "덮어쓰시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "설정을 취소했습니다."
        exit 0
    fi
fi

# Copy from example
cp .env.example .env
echo "✓ .env 파일 생성 완료"
echo ""

# Function to update .env file
update_env() {
    local key=$1
    local value=$2
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|${key}=.*|${key}=${value}|" .env
    else
        # Linux
        sed -i "s|${key}=.*|${key}=${value}|" .env
    fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  Google Gemini API 키 설정 (필수)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "발급 방법: https://aistudio.google.com/app/apikey"
echo ""
read -p "Gemini API Key를 입력하세요 (AIza...): " gemini_key

if [ -n "$gemini_key" ]; then
    update_env "GEMINI_API_KEY" "$gemini_key"
    echo "✓ Gemini API 키 저장 완료"
else
    echo "⚠️  Gemini API 키를 입력하지 않았습니다. 나중에 설정하세요."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  한국투자증권 API 설정 (필수)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "발급 방법: KIS Developers (https://securities.koreainvestment.com/)"
echo ""
read -p "한투 API Key를 입력하세요 (PS...): " kis_key

if [ -n "$kis_key" ]; then
    update_env "KOREA_INVESTMENT_API_KEY" "$kis_key"
    echo "✓ 한투 API 키 저장 완료"
fi

read -p "한투 API Secret을 입력하세요: " kis_secret

if [ -n "$kis_secret" ]; then
    update_env "KOREA_INVESTMENT_API_SECRET" "$kis_secret"
    echo "✓ 한투 API Secret 저장 완료"
fi

read -p "한투 계좌번호를 입력하세요 (8자리): " kis_account

if [ -n "$kis_account" ]; then
    update_env "KOREA_INVESTMENT_ACCOUNT_NUMBER" "$kis_account"
    echo "✓ 한투 계좌번호 저장 완료"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  Reddit API 설정 (선택사항)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Reddit API 없이도 WallStreetBets 스크래핑은 작동합니다."
read -p "Reddit API를 설정하시겠습니까? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "발급 방법: https://www.reddit.com/prefs/apps"
    echo ""
    read -p "Reddit Client ID를 입력하세요: " reddit_id
    read -p "Reddit Client Secret을 입력하세요: " reddit_secret

    if [ -n "$reddit_id" ]; then
        update_env "REDDIT_CLIENT_ID" "$reddit_id"
        echo "✓ Reddit Client ID 저장 완료"
    fi

    if [ -n "$reddit_secret" ]; then
        update_env "REDDIT_CLIENT_SECRET" "$reddit_secret"
        echo "✓ Reddit Client Secret 저장 완료"
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  초기 자본금 설정"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "현재 설정: 1,000,000 KRW (100만원)"
read -p "초기 자본금을 변경하시겠습니까? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "초기 자본금을 입력하세요 (KRW, 숫자만): " capital
    if [ -n "$capital" ]; then
        update_env "INITIAL_CAPITAL_KRW" "$capital"
        echo "✓ 초기 자본금 설정 완료: ${capital} KRW"
    fi
fi

echo ""
echo "================================================"
echo "✅ API 키 설정 완료!"
echo "================================================"
echo ""
echo ".env 파일에 저장된 설정:"
echo ""
grep -E "^(GEMINI|KOREA|REDDIT|INITIAL_CAPITAL)" .env | while read line; do
    key=$(echo "$line" | cut -d'=' -f1)
    value=$(echo "$line" | cut -d'=' -f2)

    # Mask sensitive values
    if [[ "$value" != "your_"* ]] && [[ -n "$value" ]]; then
        if [[ "$key" == "INITIAL_CAPITAL_KRW" ]]; then
            echo "  ✓ $key = $value"
        else
            masked="${value:0:10}***"
            echo "  ✓ $key = $masked"
        fi
    else
        echo "  ⚠️  $key = (미설정)"
    fi
done

echo ""
echo "다음 단계:"
echo "  1. 백엔드 시작: bash scripts/run_dev.sh"
echo "  2. 브라우저 접속: http://localhost:5173"
echo "  3. 설정 페이지에서 API 키 확인"
echo ""
echo "팁: WebUI에서도 API 키를 추가/수정할 수 있습니다."
echo ""
