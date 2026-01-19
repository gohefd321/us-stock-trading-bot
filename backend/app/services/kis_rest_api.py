"""
Korea Investment Securities REST API Client
Direct implementation without Mojito2 library
Based on official KIS API documentation
"""

import asyncio
import logging
import hashlib
import hmac
import requests
import json
import os
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import aiohttp

logger = logging.getLogger(__name__)


class KISRestAPI:
    """Korea Investment Securities REST API Client"""

    # API Base URLs
    REAL_BASE_URL = "https://openapi.koreainvestment.com:9443"  # 실전투자
    PAPER_BASE_URL = "https://openapivts.koreainvestment.com:29443"  # 모의투자

    def __init__(self, app_key: str, app_secret: str, account_number: str, is_paper: bool = False):
        """
        Initialize KIS REST API client

        Args:
            app_key: App Key (발급받은 App Key)
            app_secret: App Secret (발급받은 App Secret)
            account_number: 계좌번호 (format: 12345678-01)
            is_paper: 모의투자 여부
        """
        self.app_key = app_key
        self.app_secret = app_secret
        self.is_paper = is_paper
        self.base_url = self.PAPER_BASE_URL if is_paper else self.REAL_BASE_URL

        # Parse account number
        if '-' in account_number:
            parts = account_number.split('-')
            if len(parts) == 2:
                self.account_prefix, self.account_suffix = parts
            else:
                logger.error(f"Invalid account number format: {account_number}")
                self.account_prefix = ""
                self.account_suffix = ""
        elif len(account_number) >= 10:
            # Assume last 2 digits are suffix
            self.account_prefix = account_number[:-2]
            self.account_suffix = account_number[-2:]
        else:
            logger.error(f"Invalid account number format: {account_number} (too short)")
            self.account_prefix = ""
            self.account_suffix = ""

        # Access token
        self.access_token = None
        self.token_expired_at = None

        # Token file path (store in data directory)
        from ..config import PROJECT_ROOT
        token_dir = PROJECT_ROOT / "data"
        token_dir.mkdir(exist_ok=True)
        mode_suffix = "paper" if is_paper else "real"
        self.token_file = token_dir / f"kis_token_{mode_suffix}.json"

        logger.info(f"KIS API initialized (paper_mode={is_paper})")
        logger.info(f"Account: {self.account_prefix}-{self.account_suffix}")

    def _get_headers(self, tr_id: str, content_type: str = "application/json; charset=utf-8") -> Dict:
        """
        Get request headers

        Args:
            tr_id: 거래ID (Transaction ID)
            content_type: Content-Type

        Returns:
            Headers dictionary
        """
        headers = {
            "Content-Type": content_type,
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
        }
        return headers

    def _load_token_from_file(self) -> bool:
        """
        Load access token from file if it exists and is valid

        Returns:
            True if token was loaded successfully
        """
        try:
            if not self.token_file.exists():
                return False

            with open(self.token_file, 'r') as f:
                token_data = json.load(f)

            # Check if token is expired
            expired_at_str = token_data.get('expired_at')
            if not expired_at_str:
                return False

            expired_at = datetime.fromisoformat(expired_at_str)

            # Token should have at least 5 minutes remaining
            if datetime.now() >= expired_at - timedelta(minutes=5):
                logger.info("Stored token has expired")
                return False

            self.access_token = token_data.get('access_token')
            self.token_expired_at = expired_at

            logger.info(f"✓ Loaded existing token from file (expires: {self.token_expired_at})")
            return True

        except Exception as e:
            logger.warning(f"Failed to load token from file: {e}")
            return False

    def _save_token_to_file(self):
        """Save access token to file"""
        try:
            token_data = {
                'access_token': self.access_token,
                'expired_at': self.token_expired_at.isoformat(),
                'created_at': datetime.now().isoformat()
            }

            with open(self.token_file, 'w') as f:
                json.dump(token_data, f, indent=2)

            logger.info(f"✓ Token saved to file: {self.token_file}")

        except Exception as e:
            logger.error(f"Failed to save token to file: {e}")

    def get_access_token(self) -> bool:
        """
        Get OAuth2 access token (하루 3회 제한이 있으므로 파일에서 먼저 로드 시도)

        Returns:
            True if successful
        """
        # 먼저 파일에서 토큰 로드 시도
        if self._load_token_from_file():
            return True

        # 파일에 없거나 만료되었으면 새로 발급
        logger.info("Requesting new access token from KIS API...")

        url = f"{self.base_url}/oauth2/tokenP"

        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }

        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()

            result = response.json()

            if "access_token" in result:
                self.access_token = result["access_token"]
                expires_in = int(result.get("expires_in", 86400))  # Default 24 hours
                self.token_expired_at = datetime.now() + timedelta(seconds=expires_in)

                logger.info(f"✓ New access token obtained, expires at: {self.token_expired_at}")

                # 파일에 저장
                self._save_token_to_file()

                return True
            else:
                logger.error(f"Failed to get access token: {result}")
                return False

        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            return False

    def is_token_valid(self) -> bool:
        """Check if access token is still valid"""
        if not self.access_token or not self.token_expired_at:
            return False
        return datetime.now() < self.token_expired_at - timedelta(minutes=5)

    def ensure_token(self):
        """Ensure access token is valid, refresh if needed"""
        if not self.is_token_valid():
            logger.info("Token expired or missing, getting new token...")
            return self.get_access_token()
        return True

    async def get_balance(self) -> Dict:
        """
        주식 잔고 조회 (국내)

        Returns:
            잔고 정보 딕셔너리
        """
        if not self.ensure_token():
            raise RuntimeError("Failed to get access token")

        # TR_ID: TTTC8434R (실전투자) / VTTC8434R (모의투자)
        tr_id = "VTTC8434R" if self.is_paper else "TTTC8434R"

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"

        headers = self._get_headers(tr_id)

        params = {
            "CANO": self.account_prefix,
            "ACNT_PRDT_CD": self.account_suffix,
            "AFHR_FLPR_YN": "N",  # 시간외단일가여부
            "OFL_YN": "",  # 오프라인여부
            "INQR_DVSN": "01",  # 조회구분(01:대출일별, 02:종목별)
            "UNPR_DVSN": "01",  # 단가구분
            "FUND_STTL_ICLD_YN": "N",  # 펀드결제분포함여부
            "FNCG_AMT_AUTO_RDPT_YN": "N",  # 융자금액자동상환여부
            "PRCS_DVSN": "00",  # 처리구분(00:전일매매포함, 01:전일매매미포함)
            "CTX_AREA_FK100": "",  # 연속조회검색조건100
            "CTX_AREA_NK100": ""  # 연속조회키100
        }

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(url, headers=headers, params=params)
            )
            response.raise_for_status()

            result = response.json()

            # Extract balance information
            if result.get("rt_cd") == "0":  # Success
                output1 = result.get("output1", [])
                output2 = result.get("output2", [{}])[0]

                # 예수금 (현금)
                cash_balance = float(output2.get("dnca_tot_amt", 0))
                # 총 평가금액
                total_value = float(output2.get("tot_evlu_amt", 0))
                # 보유 종목 평가금액
                holdings_value = float(output2.get("scts_evlu_amt", 0))

                return {
                    "cash_balance": cash_balance,
                    "total_value": total_value,
                    "holdings_value": holdings_value,
                    "positions": output1,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.error(f"Balance API error: {result.get('msg1')}")
                return {
                    "cash_balance": 0,
                    "total_value": 0,
                    "holdings_value": 0,
                    "positions": [],
                    "error": result.get("msg1", "Unknown error"),
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return {
                "cash_balance": 0,
                "total_value": 0,
                "holdings_value": 0,
                "positions": [],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def get_us_balance(self) -> Dict:
        """
        해외주식 잔고 조회 (미국)

        Returns:
            잔고 정보 딕셔너리
        """
        if not self.ensure_token():
            raise RuntimeError("Failed to get access token")

        # TR_ID: TTTS3012R (실전투자) / VTTS3012R (모의투자)
        tr_id = "VTTS3012R" if self.is_paper else "TTTS3012R"

        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"

        headers = self._get_headers(tr_id)

        params = {
            "CANO": self.account_prefix,
            "ACNT_PRDT_CD": self.account_suffix,
            "OVRS_EXCG_CD": "NASD",  # 해외거래소코드(NASD:나스닥, NYSE:뉴욕, AMEX:아멕스)
            "TR_CRCY_CD": "USD",  # 거래통화코드
            "CTX_AREA_FK200": "",  # 연속조회검색조건200
            "CTX_AREA_NK200": ""  # 연속조회키200
        }

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(url, headers=headers, params=params)
            )
            response.raise_for_status()

            result = response.json()

            if result.get("rt_cd") == "0":
                output1 = result.get("output1", [])
                output2 = result.get("output2", [{}])[0]

                # USD 기준
                cash_balance = float(output2.get("frcr_pchs_amt1", 0))  # 외화매입금액
                total_value = float(output2.get("tot_evlu_pfls_amt", 0))  # 총평가손익금액
                holdings_value = float(output2.get("ovrs_tot_pfls", 0))  # 해외총손익

                return {
                    "cash_balance": cash_balance,
                    "total_value": total_value,
                    "holdings_value": holdings_value,
                    "positions": output1,
                    "currency": "USD",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.error(f"US Balance API error: {result.get('msg1')}")
                return {
                    "cash_balance": 0,
                    "total_value": 0,
                    "holdings_value": 0,
                    "positions": [],
                    "currency": "USD",
                    "error": result.get("msg1", "Unknown error"),
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Failed to get US balance: {e}")
            return {
                "cash_balance": 0,
                "total_value": 0,
                "holdings_value": 0,
                "positions": [],
                "currency": "USD",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def get_us_stock_price(self, ticker: str, exchange: str = "NASD") -> Optional[float]:
        """
        해외주식 현재가 조회

        Args:
            ticker: 종목코드 (예: AAPL)
            exchange: 거래소코드 (NASD, NYSE, AMEX)

        Returns:
            현재가 (USD)
        """
        if not self.ensure_token():
            return None

        # TR_ID: HHDFS00000300 (해외주식 현재가 상세)
        tr_id = "HHDFS00000300"

        url = f"{self.base_url}/uapi/overseas-price/v1/quotations/price"

        headers = self._get_headers(tr_id)

        params = {
            "AUTH": "",
            "EXCD": exchange,
            "SYMB": ticker
        }

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(url, headers=headers, params=params)
            )
            response.raise_for_status()

            result = response.json()

            if result.get("rt_cd") == "0":
                output = result.get("output", {})
                # 현재가
                current_price = float(output.get("last", 0))
                return current_price if current_price > 0 else None
            else:
                logger.error(f"Price API error: {result.get('msg1')}")
                return None

        except Exception as e:
            logger.error(f"Failed to get stock price for {ticker}: {e}")
            return None

    async def buy_us_stock(self, ticker: str, quantity: int, price: float = 0, order_type: str = "market") -> Dict:
        """
        해외주식 매수

        Args:
            ticker: 종목코드
            quantity: 수량
            price: 지정가 (order_type='limit'일 때 사용)
            order_type: 주문유형 ('market' or 'limit')

        Returns:
            주문 결과
        """
        if not self.ensure_token():
            raise RuntimeError("Failed to get access token")

        # TR_ID: TTTT1002U (실전투자 매수) / VTTT1002U (모의투자 매수)
        tr_id = "VTTT1002U" if self.is_paper else "TTTT1002U"

        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"

        headers = self._get_headers(tr_id)

        # 주문유형코드: 00(지정가), 01(시장가)
        ord_dv = "01" if order_type == "market" else "00"

        data = {
            "CANO": self.account_prefix,
            "ACNT_PRDT_CD": self.account_suffix,
            "OVRS_EXCG_CD": "NASD",  # 거래소코드
            "PDNO": ticker,  # 종목코드
            "ORD_QTY": str(quantity),  # 주문수량
            "OVRS_ORD_UNPR": str(price) if order_type == "limit" else "0",  # 해외주문단가
            "ORD_SVR_DVSN_CD": "0",  # 주문서버구분코드
            "ORD_DVSN": ord_dv,  # 주문구분(00:지정가, 01:시장가)
        }

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(url, headers=headers, json=data)
            )
            response.raise_for_status()

            result = response.json()

            if result.get("rt_cd") == "0":
                output = result.get("output", {})
                return {
                    "success": True,
                    "order_number": output.get("ODNO"),  # 주문번호
                    "message": result.get("msg1", "Order placed successfully")
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg1", "Unknown error")
                }

        except Exception as e:
            logger.error(f"Failed to buy {ticker}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def sell_us_stock(self, ticker: str, quantity: int, price: float = 0, order_type: str = "market") -> Dict:
        """
        해외주식 매도

        Args:
            ticker: 종목코드
            quantity: 수량
            price: 지정가 (order_type='limit'일 때 사용)
            order_type: 주문유형 ('market' or 'limit')

        Returns:
            주문 결과
        """
        if not self.ensure_token():
            raise RuntimeError("Failed to get access token")

        # TR_ID: TTTT1006U (실전투자 매도) / VTTT1001U (모의투자 매도)
        tr_id = "VTTT1001U" if self.is_paper else "TTTT1006U"

        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"

        headers = self._get_headers(tr_id)

        # 주문유형코드: 00(지정가), 01(시장가)
        ord_dv = "01" if order_type == "market" else "00"

        data = {
            "CANO": self.account_prefix,
            "ACNT_PRDT_CD": self.account_suffix,
            "OVRS_EXCG_CD": "NASD",
            "PDNO": ticker,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": str(price) if order_type == "limit" else "0",
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": ord_dv,
        }

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(url, headers=headers, json=data)
            )
            response.raise_for_status()

            result = response.json()

            if result.get("rt_cd") == "0":
                output = result.get("output", {})
                return {
                    "success": True,
                    "order_number": output.get("ODNO"),
                    "message": result.get("msg1", "Order placed successfully")
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg1", "Unknown error")
                }

        except Exception as e:
            logger.error(f"Failed to sell {ticker}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
