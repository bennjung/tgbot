# 곰빵봇 - Base 체인 USDC 드랍 텔레그램 봇

## 🤖 기능
- **랜덤 드랍**: 채팅 시 확률적으로 USDC 전송
- **지갑 등록**: `/set` 명령어로 Base 체인 지갑 등록
- **신규 사용자 안내**: 처음 참여하는 사용자에게 자동 안내문 전송
- **정기 안내문**: 4시간마다 그룹에 사용법 안내
- **동적 가스 추정**: 실시간 네트워크 상황 반영한 가스 최적화

## 🔧 환경변수 설정

`.env` 파일을 생성하고 다음 설정을 추가하세요:

```env
# 텔레그램 봇 설정
TELEGRAM_BOT_TOKEN=your_bot_token_here
GROUP_CHAT_ID=your_group_chat_id_here

# Base 체인 설정  
RPC_URL=https://base-mainnet.public.blastapi.io
USDC_CONTRACT_ADDRESS=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
PRIVATE_KEY=your_private_key_here

# 봇 설정
DROP_RATE=0.05
MAX_DAILY_AMOUNT=10.0
COOLDOWN_SECONDS=30
ADMIN_USER_ID=your_admin_user_id_here
```

## 🚀 실행 방법

```bash
# 의존성 설치
pip install -r requirements.txt

# 봇 실행
python3 tx_bot.py
```

## 📝 사용법

1. 그룹에 봇 추가
2. `/set 지갑주소` 명령어로 지갑 등록
3. 채팅하면 자동으로 USDC 드랍 기회!

## ⚙️ 주요 특징

- **안전한 가스 추정**: Base 권장값 + 10% 마진
- **쿨타임 시스템**: 스팸 방지 (기본 30초)
- **일일 한도**: 하루 최대 전송량 제한
- **메시지 길이 체크**: 최소 5글자 이상
- **신규 사용자 환영**: 자동 안내문 전송
- **정기 안내**: 4시간마다 사용법 공지
