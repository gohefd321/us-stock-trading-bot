# 원격 서버 google-genai 패키지 설치 방법

## 문제
```
ImportError: cannot import name 'genai' from 'google' (unknown location)
```

원격 서버(`/home/sixseven/us-stock-trading-bot/`)에 `google-genai` 패키지가 설치되지 않음

## 해결 방법

### 1. SSH로 원격 서버 접속
```bash
ssh username@your-server-ip
```

### 2. 프로젝트 디렉토리로 이동
```bash
cd /home/sixseven/us-stock-trading-bot/backend
```

### 3. 가상환경 활성화
```bash
source venv/bin/activate
```

### 4. google-genai 패키지 설치
```bash
pip install -U google-genai
```

### 5. 설치 확인
```bash
python -c "from google import genai; print('✅ Import successful')"
```

### 6. 서비스 재시작
```bash
# systemd 사용 시
sudo systemctl restart trading-bot

# 또는 PM2 사용 시
pm2 restart trading-bot

# 또는 수동 실행 시
pkill -f uvicorn
cd /home/sixseven/us-stock-trading-bot/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 참고
- 로컬 맥북: `/Users/mackbook/Documents/us-stock-trading-bot/`
- 원격 서버: `/home/sixseven/us-stock-trading-bot/`
