#!/usr/bin/env python3
"""
Base 체인 USDC 드랍 텔레그램 봇
기능:
1. 지갑 등록: /set "wallet_address" 인라인 처리
2. 랜덤 드랍: 채팅시 일정 확률로 USDC 전송
3. 신규 사용자 안내문 자동 전송
4. 정기 안내문 (4시간마다)
"""

import os
import json
import logging
import random
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import telebot
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from apscheduler.schedulers.background import BackgroundScheduler

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tx_bot.log'),
        logging.StreamHandler()
    ]
)

class WalletManager:
    """지갑 주소 관리 클래스"""
    
    def __init__(self, wallet_file: str = "wallets.json", users_file: str = "users.json"):
        self.wallet_file = wallet_file
        self.users_file = users_file
        self.wallets = self._load_wallets()
        self.known_users = self._load_known_users()
    
    """지갑 데이터 로드"""
    def _load_wallets(self) -> Dict[str, str]:
        
        try:
            if os.path.exists(self.wallet_file):
                with open(self.wallet_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logging.error(f"지갑 데이터 로드 실패: {e}")
            return {}
    
    """사용자 목록 로드"""
    def _load_known_users(self) -> set:
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    user_list = json.load(f)
                    return set(user_list)
            return set()
        except Exception as e:
            logging.error(f"사용자 데이터 로드 실패: {e}")
            return set()
    
    """지갑 데이터 저장"""
    def _save_wallets(self) -> bool:
        
        try:
            with open(self.wallet_file, 'w', encoding='utf-8') as f:
                json.dump(self.wallets, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logging.error(f"지갑 데이터 저장 실패: {e}")
            return False
    
    """사용자 목록 저장"""
    def _save_known_users(self) -> bool:
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.known_users), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logging.error(f"사용자 데이터 저장 실패: {e}")
            return False
    
    """신규 사용자 확인 및 등록"""
    def is_new_user(self, user_id: str) -> bool:
        if user_id not in self.known_users:
            self.known_users.add(user_id)
            self._save_known_users()
            return True
        return False
    
    """지갑 주소 유효성 검사"""
    def is_valid_address(self, address: str) -> bool:
        
        try:
            # 이더리움 주소 형식 검사 (0x + 40자리 hex)
            pattern = r'^0x[a-fA-F0-9]{40}$'
            if not re.match(pattern, address):
                return False
            
            # Web3를 통한 체크섬 검증
            return Web3.is_address(address)
        except Exception:
            return False
    """지갑 주소 등록"""
    def set_wallet(self, user_id: str, wallet_address: str) -> bool:
       
        if not self.is_valid_address(wallet_address):
            return False
        
        # 체크섬 주소로 변환
        checksum_address = Web3.to_checksum_address(wallet_address)
        self.wallets[user_id] = checksum_address
        
        return self._save_wallets()
    """지갑 주소 조회"""
    def get_wallet(self, user_id: str) -> Optional[str]:
        
        return self.wallets.get(user_id)
    """지갑 주소 삭제"""
    def remove_wallet(self, user_id: str) -> bool:
        
        if user_id in self.wallets:
            del self.wallets[user_id]
            return self._save_wallets()
        return False
    """모든 지갑 주소 조회"""
    def get_all_wallets(self) -> Dict[str, str]:
        return self.wallets.copy()

class TransactionManager:
    """Base 체인 트랜잭션 관리 클래스"""
    
    def __init__(self, rpc_url: str, usdc_contract_address: str, private_key: str):
        self.rpc_url = rpc_url
        self.usdc_contract_address = Web3.to_checksum_address(usdc_contract_address)
        self.private_key = private_key
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # USDC 컨트랙트 ABI (transfer 함수만)
        self.usdc_abi = [
            {
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }
        ]
        
        self.usdc_contract = self.w3.eth.contract(
            address=self.usdc_contract_address,
            abi=self.usdc_abi
        )
        
        # 지갑 계정 설정
        self.account = Account.from_key(private_key)
        
    def is_connected(self) -> bool:
        """Base 체인 연결 상태 확인"""
        try:
            return self.w3.is_connected()
        except Exception as e:
            logging.error(f"Base 체인 연결 실패: {e}")
            return False
    
    def should_drop(self, drop_rate: float) -> bool:
        """랜덤 드랍 여부 결정"""
        return random.random() < drop_rate
    
    def get_usdc_balance(self, address: str) -> float:
        """USDC 잔고 조회"""
        try:
            balance_wei = self.usdc_contract.functions.balanceOf(
                Web3.to_checksum_address(address)
            ).call()
            # USDC는 6자리 소수점
            return balance_wei / (10 ** 6)
        except Exception as e:
            logging.error(f"USDC 잔고 조회 실패: {e}")
            return 0.0
    
    def get_optimal_gas_estimate(self, to_address: str, amount: float) -> dict:
        """실제 전송 전 동적 가스 추정"""
        try:
            to_checksum = Web3.to_checksum_address(to_address)
            amount_wei = int(amount * (10 ** 6))  # USDC 6자리 소수점
            
            # 현재 네트워크 상황으로 가스 추정
            estimated_gas = self.usdc_contract.functions.transfer(
                to_checksum, amount_wei
            ).estimate_gas({
                'from': self.account.address
            })
            
            # Base 공식 문서 기준: ERC-20 전송은 ~65,000 gas
            base_recommended = 65000
            
            # 추정값과 권장값 중 높은 값에 안전 마진 추가
            optimal_gas = max(estimated_gas, base_recommended)
            safe_gas = int(optimal_gas * 1.1)  # 10% 안전 마진
            
            # 최대 한도 설정 (과도한 가스 방지)
            max_gas = 100000
            final_gas = min(safe_gas, max_gas)
            
            logging.info(f"가스 추정 결과: 추정={estimated_gas:,}, 권장={base_recommended:,}, 최종={final_gas:,}")
            
            return {
                'estimated': estimated_gas,
                'recommended': base_recommended,
                'final': final_gas,
                'margin': f"{((final_gas - estimated_gas) / estimated_gas * 100):.1f}%"
            }
            
        except Exception as e:
            logging.warning(f"동적 가스 추정 실패, 기본값 사용: {e}")
            # 추정 실패시 Base 권장값 + 마진
            return {
                'estimated': 0,
                'recommended': 65000,
                'final': 71500,  # 65000 * 1.1
                'margin': '10.0%'
            }

    def send_usdc(self, to_address: str, amount: float, retry_count: int = 0) -> Optional[str]:
        """USDC 전송 (동적 가스 추정)"""
        try:
            to_checksum = Web3.to_checksum_address(to_address)
            amount_wei = int(amount * (10 ** 6))  # USDC 6자리 소수점
            
            # 1단계: 현재 상황에 최적화된 가스 추정
            gas_info = self.get_optimal_gas_estimate(to_address, amount)
            optimal_gas = gas_info['final']
            
            # 2단계: 가스 가격 동적 조정 (재시도시 증가)
            base_gas_price = 0.1
            gas_price = base_gas_price + (retry_count * 0.05)
            
            # 3단계: 트랜잭션 구성 (가스 한도 명시적 설정)
            transaction_params = {
                'from': self.account.address,
                'gasPrice': self.w3.to_wei(str(gas_price), 'gwei'),
                'gas': optimal_gas,  # 동적으로 계산된 최적 가스
                'nonce': self.w3.eth.get_transaction_count(self.account.address, 'pending'),
            }

            # 4단계: 트랜잭션 빌드 및 전송
            transaction = self.usdc_contract.functions.transfer(
                to_checksum, amount_wei
            ).build_transaction(transaction_params)
            
            # 트랜잭션 서명 및 전송
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logging.info(f"USDC 전송 성공: {amount} USDC를 {to_address}로")
            logging.info(f"가스 정보: {gas_info['margin']} 마진, 한도 {optimal_gas:,}, 해시: {tx_hash.hex()}")
            return tx_hash.hex()
            
        except Exception as e:
            error_msg = str(e)
            
            # underpriced 오류 처리
            if "underpriced" in error_msg.lower() and retry_count < 3:
                logging.warning(f"Underpriced 오류, 재시도 {retry_count + 1}/3")
                import time
                time.sleep(2)
                return self.send_usdc(to_address, amount, retry_count + 1)
            
            logging.error(f"USDC 전송 실패 (재시도 {retry_count}회): {e}")
            return None

class USDCDropBot:
    """USDC 드랍 텔레그램 봇"""
    
    def __init__(self):
        # 환경변수 로드
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.base_rpc = os.getenv('RPC_URL', 'https://base-mainnet.public.blastapi.io')
        self.usdc_contract = os.getenv('USDC_CONTRACT_ADDRESS')
        self.private_key = os.getenv('PRIVATE_KEY')
        self.drop_rate = float(os.getenv('DROP_RATE', '0.05'))  # 5%
        self.max_daily_amount = float(os.getenv('MAX_DAILY_AMOUNT', '10.0'))  # Alter 10 USDC
        self.admin_user_id = os.getenv('ADMIN_USER_ID')
        self.group_chat_id = os.getenv('GROUP_CHAT_ID')  # 정기 안내문을 보낼 그룹 채팅 ID
        
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN이 설정되지 않았습니다.")
        
        # 봇 초기화
        self.bot = telebot.TeleBot(self.bot_token)
        self.wallet_manager = WalletManager()
        
        # 트랜잭션 매니저 초기화 (private_key가 있을 때만)
        if self.private_key:
            self.tx_manager = TransactionManager(
                self.base_rpc, 
                self.usdc_contract, 
                self.private_key
            )
        else:
            self.tx_manager = None
            logging.warning("PRIVATE_KEY가 설정되지 않았습니다.")
        
        # 일일 전송량 추적
        self.daily_sent = {}
        
        # 전송 쿨타임 관리
        self.last_transaction_time = {}
        self.cooldown_seconds = float(os.getenv('COOLDOWN_SECONDS', '30'))
        
        # APScheduler 초기화
        self.scheduler = BackgroundScheduler()
        
        # 핸들러 설정
        self.setup_handlers()
        
        # 정기 안내문 스케줄 설정
        self.setup_periodic_guide()
    
    def get_guide_message(self) -> str:
        """안내문 메시지 반환"""
        return f"""🎯 곰빵봇 사용 안내

🤖 곰빵봇은 채팅 시 랜덤으로 USDC를 드랍해주는 Base 체인 기반 텔레그램 봇입니다!

📝 지갑 등록 방법:
아래 예시 명령어를 입력해서 지갑을 등록해주세요

/set 등록할지갑주소

✨ 지갑 등록 후 채팅하면 USDC 드랍 기회를 얻을 수 있습니다! (단 최소 5글자 이상)
🌐 Base Network을 사용합니다."""
    
    def send_guide_to_user(self, chat_id: str, user_name: str = "Unknown"):
        """그룹 입장시 안내문 전송 (멘션 없음)"""
        try:
            guide_message = self.get_guide_message()
            welcome_text = f"{user_name}님 환영합니다! 🎉\n\n{guide_message}"
            
            self.bot.send_message(chat_id, welcome_text)
            logging.info(f"그룹 입장 안내문 전송: {user_name}")
        except Exception as e:
            logging.error(f"그룹 안내문 전송 실패: {user_name} - {e}")
    
    def send_periodic_guide(self):
        """정기 안내문 전송 (그룹 채팅)"""
        if not self.group_chat_id:
            logging.warning("GROUP_CHAT_ID가 설정되지 않아 정기 안내문을 보낼 수 없습니다.")
            return
        
        try:
            guide_message = self.get_guide_message()
            self.bot.send_message(self.group_chat_id, guide_message)
            logging.info(f"정기 안내문 전송 완료: {self.group_chat_id}")
        except Exception as e:
            logging.error(f"정기 안내문 전송 실패: {e}")
    
    def setup_periodic_guide(self):
        """정기 안내문 스케줄 설정 (4시간마다)"""
        try:
            self.scheduler.add_job(
                func=self.send_periodic_guide,
                trigger="interval",
                hours=4,
                id="periodic_guide",
                name="정기 안내문 전송",
                replace_existing=True
            )
            logging.info("정기 안내문 스케줄 설정 완료 (4시간마다)")
        except Exception as e:
            logging.error(f"정기 안내문 스케줄 설정 실패: {e}")

    def setup_handlers(self):
        """메시지 핸들러 설정"""
        
        @self.bot.message_handler(commands=['start'])
        def handle_start(message):
            """시작 명령어"""
            welcome_text = f"""
🎯 USDC 드랍 봇에 오신 것을 환영합니다!

💰 기능:
- 지갑 등록: /set wallet_address
- 현재 설정: /info
- 내 지갑: /wallet

🎲 랜덤 드랍:
- 채팅시 {self.drop_rate*100:.1f}% 확률로 USDC 드랍!
- 하루 최대 {self.max_daily_amount} USDC
            """
            self.bot.reply_to(message, welcome_text)
        
        @self.bot.message_handler(commands=['set'])
        def handle_set_wallet(message):
            """지갑 주소 설정 (인라인 처리)"""
            user_id = str(message.from_user.id)
            user_name = message.from_user.first_name or message.from_user.username or "Unknown"
            
            # 지갑 주소 추출
            wallet_address = self.parse_set_command(message.text)
            
            if not wallet_address:
                self.bot.reply_to(message, "❌ 사용법: /set 0x1234...")
                return
            
            # 인라인 처리: 즉시 검증 및 저장
            if self.wallet_manager.set_wallet(user_id, wallet_address):
                success_text = "✅ 등록완료했습니다!"  # [modify] 메시지 간소화
                self.bot.reply_to(message, success_text)
                logging.info(f"지갑 등록 성공: {user_name} ({user_id}) -> {wallet_address}")
            else:
                self.bot.reply_to(message, "❌ 유효하지 않은 지갑 주소입니다. Base 체인 주소를 확인해주세요.")
        
        @self.bot.message_handler(commands=['wallet'])
        def handle_wallet_info(message):
            """내 지갑 정보 조회"""
            user_id = str(message.from_user.id)
            wallet = self.wallet_manager.get_wallet(user_id)
            
            if wallet:
                self.bot.reply_to(message, f"💳 등록된 지갑: {wallet}")
            else:
                self.bot.reply_to(message, "❌ 등록된 지갑이 없습니다. /set 명령어로 지갑을 등록해주세요.")
        
        @self.bot.message_handler(commands=['info'])
        def handle_info(message):
            """관리자에게 채팅 ID 정보 전송"""
            # 관리자에게 현재 채팅 ID 정보 전송
            if self.admin_user_id:
                try:
                    current_chat_id = message.chat.id
                    chat_type = "개인 채팅" if current_chat_id > 0 else "그룹 채팅"
                    chat_title = getattr(message.chat, 'title', '제목 없음')
                    today = datetime.now().date().isoformat()
                    today_sent = self.daily_sent.get(today, 0)
                    
                    admin_message = f"""
🔧 관리자 정보

📍 현재 채팅 정보:
🆔 채팅 ID: {current_chat_id}
📋 채팅 유형: {chat_type}
📝 채팅 제목: {chat_title}

📊 봇 설정 정보:
🎲 드랍 확률: {self.drop_rate*100:.1f}%
💰 하루 최대: {self.max_daily_amount} USDC
📈 오늘 전송: {today_sent:.2f} USDC
👥 등록 지갑: {len(self.wallet_manager.get_all_wallets())}개
⏰ 전송 쿨타임: {self.cooldown_seconds}초

💡 .env 파일에 추가할 내용:
GROUP_CHAT_ID={current_chat_id}
                    """
                    
                    self.bot.send_message(self.admin_user_id, admin_message)
                    logging.info(f"관리자에게 채팅 ID 정보 전송: {current_chat_id}")
                except Exception as e:
                    logging.error(f"관리자에게 채팅 ID 전송 실패: {e}")
            else:
                logging.warning("ADMIN_USER_ID가 설정되지 않아 채팅 ID를 전송할 수 없습니다.")
        
        @self.bot.message_handler(content_types=['new_chat_members'])
        def handle_new_members(message):
            """새로운 멤버 입장시 안내문 전송"""
            chat_id = str(message.chat.id)
            
            for new_member in message.new_chat_members:
                # 봇 자신은 제외
                if new_member.is_bot:
                    continue
                    
                user_name = new_member.first_name or new_member.username or "Unknown"
                user_id = str(new_member.id)
                
                # 입장 안내문 전송
                self.send_guide_to_user(chat_id, user_name)
                logging.info(f"새 멤버 입장: {user_name} ({user_id})")
        
        @self.bot.message_handler(func=lambda message: True)
        def handle_all_messages(message):
            """모든 메시지 처리 - 랜덤 드랍 트리거"""
            if message.from_user:
                user_id = str(message.from_user.id)
                user_name = message.from_user.first_name or message.from_user.username or "Unknown"
                
                # 메시지가 명령어인 경우 무시
                if message.text and message.text.startswith('/'):
                    return
                
                # 랜덤 드랍 처리
                self.process_message_drop(message, user_id, user_name)
    
    @staticmethod
    def parse_set_command(command_text: str) -> Optional[str]:
        """지갑 설정 명령어 파싱"""
        if not command_text:
            return None
        
        # /set 다음에 오는 주소 추출 (공백으로 구분)
        parts = command_text.strip().split()
        if len(parts) >= 2 and parts[0] == '/set':
            # /set 다음의 모든 부분을 주소로 간주
            wallet_address = ' '.join(parts[1:]).strip()
            # 쌍따옴표가 있다면 제거
            if wallet_address.startswith('"') and wallet_address.endswith('"'):
                wallet_address = wallet_address[1:-1]
            return wallet_address
        
        return None
    
    def process_message_drop(self, message, user_id: str, user_name: str):
        """메시지별 드랍 처리"""
        # [modify] 메시지 길이 체크 (5글자 이상)
        if not message.text or len(message.text) < 5:
            return  # 5글자 미만시 드랍 없음
        
        # 지갑이 등록되어 있는지 확인
        wallet_address = self.wallet_manager.get_wallet(user_id)
        if not wallet_address:
            return  # 지갑 미등록시 드랍 없음
        
        # [modify] 쿨타임 체크 (새로 추가)
        now = datetime.now()  # [modify]
        last_tx_time = self.last_transaction_time.get(user_id)  # [modify]
        if last_tx_time:  # [modify]
            time_diff = (now - last_tx_time).total_seconds()  # [modify]
            if time_diff < self.cooldown_seconds:  # [modify]
                logging.info(f"쿨타임: {user_name} ({user_id}) - {self.cooldown_seconds - time_diff:.1f}초 남음")  # [modify]
                return  # [modify] 쿨타임 중
        
        # 일일 한도 확인
        today = datetime.now().date().isoformat()
        today_sent = self.daily_sent.get(today, 0)
        
        if today_sent >= self.max_daily_amount:
            return  # 일일 한도 초과
        
        # 랜덤 드랍 여부 결정
        if not (self.tx_manager and self.tx_manager.should_drop(self.drop_rate)):
            return  # 드랍 안함
        
        # 드랍 금액 (0.005 ~ 0.01 USDC)
        drop_amount = round(random.uniform(0.005, 0.01), 3)
        
        # 일일 한도 체크
        if today_sent + drop_amount > self.max_daily_amount:
            drop_amount = self.max_daily_amount - today_sent
            if drop_amount < 0.005:
                return  # 너무 적으면 드랍 안함
        
        # USDC 전송
        tx_hash = self.tx_manager.send_usdc(
            wallet_address, 
            drop_amount
        )
        
        if tx_hash:
            # 일일 전송량 업데이트
            self.daily_sent[today] = today_sent + drop_amount
            
            # [modify] 쿨타임 업데이트 (새로 추가)
            self.last_transaction_time[user_id] = now  # [modify]
            
            # 드랍 알림
            drop_text = f"""
💸 USDC 드랍! 🎉

👤 {user_name}
💰 {drop_amount} USDC
💳 {wallet_address[:10]}...{wallet_address[-10:]}
🔗 TX: {tx_hash[:10]}...{tx_hash[-10:]}
            """  # [modify] 쿨타임 정보 제거
            
            self.bot.reply_to(message, drop_text)
            logging.info(f"드랍 성공: {user_name} ({user_id}) -> {drop_amount} USDC (쿨타임 {self.cooldown_seconds}초 시작)")  # [modify]
    
    def run(self):
        """봇 실행"""
        logging.info("USDC 드랍 봇 시작")
        logging.info(f"드랍 확률: {self.drop_rate*100:.1f}%, 일일 한도: {self.max_daily_amount} USDC")
        
        try:
            # 스케줄러 시작
            self.scheduler.start()
            logging.info("APScheduler 시작 완료")
            
            # 봇 시작
            self.bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            logging.error(f"봇 실행 오류: {e}")
        finally:
            # 스케줄러 종료
            try:
                self.scheduler.shutdown()
                logging.info("APScheduler 종료 완료")
            except Exception as e:
                logging.error(f"APScheduler 종료 오류: {e}")
            
            logging.info("USDC 드랍 봇 종료")

def main():
    """메인 함수"""
    try:
        bot = USDCDropBot()
        bot.run()
    except Exception as e:
        logging.error(f"메인 함수 오류: {e}")

if __name__ == "__main__":
    main() 