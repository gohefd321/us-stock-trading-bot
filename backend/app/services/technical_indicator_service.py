"""
Technical Indicator Service

기술적 지표 계산 서비스
- pandas-ta 라이브러리 활용
- SMA, EMA, RSI, MACD, Bollinger Bands, ATR, VWAP, Stochastic, ADX
- 여러 timeframe 지원
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
import pandas_ta as ta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.dialects.sqlite import insert
import asyncio

from ..models.technical_indicator import TechnicalIndicator
from ..models.realtime_price import OHLCV

logger = logging.getLogger(__name__)


class TechnicalIndicatorService:
    """기술적 지표 계산 및 관리 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db

        # 지원하는 timeframes
        self.timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']

        # 지표 파라미터
        self.params = {
            'sma_periods': [10, 20, 50, 100, 200],
            'ema_periods': [10, 20, 50, 100, 200],
            'rsi_period': 14,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bb_period': 20,
            'bb_std': 2,
            'atr_period': 14,
            'stoch_k': 14,
            'stoch_d': 3,
            'adx_period': 14,
            'volume_sma': 20,
        }

    async def calculate_indicators(
        self,
        ticker: str,
        timeframe: str = '1h',
        lookback_periods: int = 200
    ) -> Dict:
        """
        특정 종목의 기술적 지표 계산

        Args:
            ticker: 종목 코드
            timeframe: 시간 프레임
            lookback_periods: 과거 캔들 수 (최소 200개 권장)

        Returns:
            계산 결과 (저장된 지표 수, 최신 지표값 등)
        """
        try:
            logger.info(f"📊 Calculating indicators for {ticker} ({timeframe})...")

            # 1. OHLCV 데이터 가져오기
            ohlcv_data = await self._fetch_ohlcv_data(ticker, timeframe, lookback_periods)

            if ohlcv_data.empty:
                logger.warning(f"No OHLCV data found for {ticker}")
                return {"success": False, "error": "No OHLCV data available"}

            # 2. 기술적 지표 계산
            indicators_df = await self._calculate_all_indicators(ohlcv_data)

            # 3. DB 저장
            saved_count = await self._save_indicators(ticker, timeframe, indicators_df)

            logger.info(f"✅ Saved {saved_count} indicator records for {ticker}")

            # 4. 최신 지표값 반환
            latest = indicators_df.iloc[-1].to_dict() if not indicators_df.empty else {}

            return {
                "success": True,
                "ticker": ticker,
                "timeframe": timeframe,
                "saved_count": saved_count,
                "latest_indicators": latest,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to calculate indicators for {ticker}: {e}")
            return {"success": False, "error": str(e)}

    async def get_latest_indicators(
        self,
        ticker: str,
        timeframe: str = '1h'
    ) -> Optional[Dict]:
        """
        최신 기술적 지표 조회

        Args:
            ticker: 종목 코드
            timeframe: 시간 프레임

        Returns:
            최신 지표값 딕셔너리
        """
        try:
            stmt = (
                select(TechnicalIndicator)
                .where(TechnicalIndicator.ticker == ticker)
                .where(TechnicalIndicator.timeframe == timeframe)
                .order_by(desc(TechnicalIndicator.timestamp))
                .limit(1)
            )

            result = await self.db.execute(stmt)
            indicator = result.scalar_one_or_none()

            if not indicator:
                return None

            return {
                "ticker": ticker,
                "timeframe": timeframe,
                "timestamp": indicator.timestamp.isoformat() if indicator.timestamp else None,
                "close_price": indicator.close_price,
                "moving_averages": {
                    "sma_10": indicator.sma_10,
                    "sma_20": indicator.sma_20,
                    "sma_50": indicator.sma_50,
                    "sma_100": indicator.sma_100,
                    "sma_200": indicator.sma_200,
                    "ema_10": indicator.ema_10,
                    "ema_20": indicator.ema_20,
                    "ema_50": indicator.ema_50,
                },
                "rsi": indicator.rsi_14,
                "macd": {
                    "macd": indicator.macd,
                    "signal": indicator.macd_signal,
                    "histogram": indicator.macd_histogram,
                },
                "bollinger": {
                    "upper": indicator.bb_upper,
                    "middle": indicator.bb_middle,
                    "lower": indicator.bb_lower,
                    "bandwidth": indicator.bb_bandwidth,
                    "percent": indicator.bb_percent,
                },
                "atr": indicator.atr_14,
                "vwap": indicator.vwap,
                "stochastic": {
                    "k": indicator.stoch_k,
                    "d": indicator.stoch_d,
                },
                "adx": {
                    "adx": indicator.adx_14,
                    "plus_di": indicator.plus_di,
                    "minus_di": indicator.minus_di,
                },
                "volume": {
                    "current": indicator.volume,
                    "sma_20": indicator.volume_sma_20,
                    "ratio": indicator.volume_ratio,
                },
            }

        except Exception as e:
            logger.error(f"Failed to get latest indicators for {ticker}: {e}")
            return None

    async def _fetch_ohlcv_data(
        self,
        ticker: str,
        timeframe: str,
        lookback: int
    ) -> pd.DataFrame:
        """
        OHLCV 데이터 조회 및 DataFrame 변환

        Args:
            ticker: 종목 코드
            timeframe: 시간 프레임
            lookback: 조회할 캔들 수

        Returns:
            OHLCV DataFrame
        """
        try:
            stmt = (
                select(OHLCV)
                .where(OHLCV.ticker == ticker)
                .where(OHLCV.timeframe == timeframe)
                .order_by(desc(OHLCV.timestamp))
                .limit(lookback)
            )

            result = await self.db.execute(stmt)
            candles = result.scalars().all()

            if not candles:
                return pd.DataFrame()

            # DataFrame 변환 (시간순 정렬)
            df = pd.DataFrame([
                {
                    'timestamp': c.timestamp,
                    'open': c.open,
                    'high': c.high,
                    'low': c.low,
                    'close': c.close,
                    'volume': c.volume,
                }
                for c in reversed(candles)
            ])

            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)

            return df

        except Exception as e:
            logger.error(f"Failed to fetch OHLCV data: {e}")
            return pd.DataFrame()

    async def _calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        모든 기술적 지표 계산 (pandas-ta 사용)

        Args:
            df: OHLCV DataFrame

        Returns:
            지표가 추가된 DataFrame
        """
        try:
            # pandas-ta 사용을 위해 컬럼명 확인
            df_copy = df.copy()

            # 1. Moving Averages (SMA, EMA)
            for period in self.params['sma_periods']:
                df_copy[f'sma_{period}'] = ta.sma(df_copy['close'], length=period)

            for period in self.params['ema_periods']:
                df_copy[f'ema_{period}'] = ta.ema(df_copy['close'], length=period)

            # 2. RSI
            df_copy['rsi_14'] = ta.rsi(df_copy['close'], length=self.params['rsi_period'])

            # 3. MACD
            macd = ta.macd(
                df_copy['close'],
                fast=self.params['macd_fast'],
                slow=self.params['macd_slow'],
                signal=self.params['macd_signal']
            )
            if macd is not None:
                df_copy['macd'] = macd[f"MACD_{self.params['macd_fast']}_{self.params['macd_slow']}_{self.params['macd_signal']}"]
                df_copy['macd_signal'] = macd[f"MACDs_{self.params['macd_fast']}_{self.params['macd_slow']}_{self.params['macd_signal']}"]
                df_copy['macd_histogram'] = macd[f"MACDh_{self.params['macd_fast']}_{self.params['macd_slow']}_{self.params['macd_signal']}"]

            # 4. Bollinger Bands
            bb = ta.bbands(
                df_copy['close'],
                length=self.params['bb_period'],
                std=self.params['bb_std']
            )
            if bb is not None:
                df_copy['bb_upper'] = bb[f"BBU_{self.params['bb_period']}_{self.params['bb_std']}.0"]
                df_copy['bb_middle'] = bb[f"BBM_{self.params['bb_period']}_{self.params['bb_std']}.0"]
                df_copy['bb_lower'] = bb[f"BBL_{self.params['bb_period']}_{self.params['bb_std']}.0"]
                df_copy['bb_bandwidth'] = bb[f"BBB_{self.params['bb_period']}_{self.params['bb_std']}.0"]
                df_copy['bb_percent'] = bb[f"BBP_{self.params['bb_period']}_{self.params['bb_std']}.0"]

            # 5. ATR (Average True Range)
            df_copy['atr_14'] = ta.atr(
                df_copy['high'],
                df_copy['low'],
                df_copy['close'],
                length=self.params['atr_period']
            )

            # 6. VWAP
            df_copy['vwap'] = ta.vwap(
                df_copy['high'],
                df_copy['low'],
                df_copy['close'],
                df_copy['volume']
            )

            # 7. Stochastic Oscillator
            stoch = ta.stoch(
                df_copy['high'],
                df_copy['low'],
                df_copy['close'],
                k=self.params['stoch_k'],
                d=self.params['stoch_d']
            )
            if stoch is not None:
                df_copy['stoch_k'] = stoch[f"STOCHk_{self.params['stoch_k']}_{self.params['stoch_d']}_3"]
                df_copy['stoch_d'] = stoch[f"STOCHd_{self.params['stoch_k']}_{self.params['stoch_d']}_3"]

            # 8. ADX (Average Directional Index)
            adx = ta.adx(
                df_copy['high'],
                df_copy['low'],
                df_copy['close'],
                length=self.params['adx_period']
            )
            if adx is not None:
                df_copy['adx_14'] = adx[f"ADX_{self.params['adx_period']}"]
                df_copy['plus_di'] = adx[f"DMP_{self.params['adx_period']}"]
                df_copy['minus_di'] = adx[f"DMN_{self.params['adx_period']}"]

            # 9. Volume indicators
            df_copy['volume_sma_20'] = ta.sma(df_copy['volume'], length=self.params['volume_sma'])
            df_copy['volume_ratio'] = df_copy['volume'] / df_copy['volume_sma_20']

            return df_copy

        except Exception as e:
            logger.error(f"Failed to calculate indicators: {e}")
            return df

    async def _save_indicators(
        self,
        ticker: str,
        timeframe: str,
        df: pd.DataFrame
    ) -> int:
        """
        계산된 지표를 DB에 저장

        Args:
            ticker: 종목 코드
            timeframe: 시간 프레임
            df: 지표가 포함된 DataFrame

        Returns:
            저장된 레코드 수
        """
        try:
            saved_count = 0

            for timestamp, row in df.iterrows():
                # NaN이 아닌 값만 저장
                indicator_data = {
                    "ticker": ticker,
                    "timeframe": timeframe,
                    "timestamp": timestamp,
                    "close_price": row['close'],
                    "volume": int(row['volume']) if pd.notna(row['volume']) else None,
                }

                # 각 지표 추가 (NaN 체크)
                indicators = {
                    'sma_10': row.get('sma_10'),
                    'sma_20': row.get('sma_20'),
                    'sma_50': row.get('sma_50'),
                    'sma_100': row.get('sma_100'),
                    'sma_200': row.get('sma_200'),
                    'ema_10': row.get('ema_10'),
                    'ema_20': row.get('ema_20'),
                    'ema_50': row.get('ema_50'),
                    'ema_100': row.get('ema_100'),
                    'ema_200': row.get('ema_200'),
                    'rsi_14': row.get('rsi_14'),
                    'macd': row.get('macd'),
                    'macd_signal': row.get('macd_signal'),
                    'macd_histogram': row.get('macd_histogram'),
                    'bb_upper': row.get('bb_upper'),
                    'bb_middle': row.get('bb_middle'),
                    'bb_lower': row.get('bb_lower'),
                    'bb_bandwidth': row.get('bb_bandwidth'),
                    'bb_percent': row.get('bb_percent'),
                    'atr_14': row.get('atr_14'),
                    'vwap': row.get('vwap'),
                    'stoch_k': row.get('stoch_k'),
                    'stoch_d': row.get('stoch_d'),
                    'adx_14': row.get('adx_14'),
                    'plus_di': row.get('plus_di'),
                    'minus_di': row.get('minus_di'),
                    'volume_sma_20': row.get('volume_sma_20'),
                    'volume_ratio': row.get('volume_ratio'),
                }

                # NaN 제거
                for key, value in indicators.items():
                    if pd.notna(value):
                        indicator_data[key] = float(value)

                # Upsert
                stmt = insert(TechnicalIndicator).values(**indicator_data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker', 'timeframe', 'timestamp'],
                    set_={k: getattr(stmt.excluded, k) for k in indicator_data.keys() if k not in ['ticker', 'timeframe', 'timestamp']}
                )

                await self.db.execute(stmt)
                saved_count += 1

            await self.db.commit()
            return saved_count

        except Exception as e:
            logger.error(f"Failed to save indicators: {e}")
            await self.db.rollback()
            return 0
