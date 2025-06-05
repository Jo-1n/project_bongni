import os
import pandas as pd
import numpy as np
import ta
from datetime import datetime, timedelta
import logging

from src.config import Config

logger = logging.getLogger(__name__)

class DataHandler:
    """
    과거 데이터 로드, 실시간 틱 데이터 수집 및 1분봉 집계,
    기술적 보조 지표 계산을 담당하는 클래스입니다.
    """

    def __init__(self, config: Config):
        self.config = config

        # 종목별 과거 시세 데이터(DataFrame) 사전
        self.historical_data = {symbol: pd.DataFrame() for symbol in self.config.symbols}
        # 실시간 틱 버퍼(종목별 리스트)
        self.real_time_buffer = {symbol: [] for symbol in self.config.symbols}
        # 마지막 1분봉 타임스탬프(종목별)
        self.last_timestamp = {symbol: None for symbol in self.config.symbols}

    def fetch_historical(self, symbol: str) -> pd.DataFrame:
        """
        특정 종목의 과거 N일치 데이터를 가져오는 메서드입니다.
        실제 환경에서는 Kiwoom OpenAPI, IEX Cloud, AlphaVantage 등을 사용할 수 있습니다.

        반환: pandas DataFrame (index: datetime, columns: open, high, low, close, volume)
        """
        # 1) API 호출 또는 로컬 CSV 조회를 구현해야 합니다.
        #    예시로, 현재는 랜덤 데이터로 채우는 형태입니다.
        now = datetime.utcnow()
        start_date = now - timedelta(days=self.config.historical_lookback_days)
        dates = pd.date_range(start=start_date, end=now, freq="1T")
        df = pd.DataFrame({
            "datetime": dates,
            "open": np.random.random(len(dates)) * 100,
            "high": np.random.random(len(dates)) * 100,
            "low": np.random.random(len(dates)) * 100,
            "close": np.random.random(len(dates)) * 100,
            "volume": np.random.randint(100, 1000, size=len(dates))
        })
        df.set_index("datetime", inplace=True)
        return df

    def update_historical_all(self):
        """
        초기 실행 시 모든 종목의 과거 데이터를 한 번에 불러와 저장합니다.
        """
        for symbol in self.config.symbols:
            df = self.fetch_historical(symbol)
            self.historical_data[symbol] = df
            self.last_timestamp[symbol] = df.index[-1]
            logger.info(f"[DATA] {symbol} 과거 데이터 로드 완료: {len(df)}행")

    def update_realtime(self, symbol: str, new_tick: dict):
        """
        실시간 틱 데이터를 수신할 때마다 호출됩니다.
        new_tick 형식: {'datetime': datetime, 'price': float, 'volume': int}
        틱 버퍼에 쌓였다가, 60틱이 모이면 1분봉으로 집계합니다.
        """
        self.real_time_buffer[symbol].append(new_tick)
        if len(self.real_time_buffer[symbol]) >= 60:
            self._aggregate_to_minute_bar(symbol)

    def _aggregate_to_minute_bar(self, symbol: str):
        """
        60틱을 모아서 1분봉으로 집계한 뒤 self.historical_data[symbol]에 추가합니다.
        """
        buffer = self.real_time_buffer[symbol]
        if not buffer:
            return

        df_ticks = pd.DataFrame(buffer)
        df_ticks.set_index("datetime", inplace=True)
        open_p = df_ticks["price"].iloc[0]
        high_p = df_ticks["price"].max()
        low_p = df_ticks["price"].min()
        close_p = df_ticks["price"].iloc[-1]
        volume = df_ticks["volume"].sum()
        ts = df_ticks.index[-1].floor("T")

        new_bar = pd.DataFrame({
            "open": [open_p],
            "high": [high_p],
            "low": [low_p],
            "close": [close_p],
            "volume": [volume]
        }, index=[ts])

        self.historical_data[symbol] = pd.concat([self.historical_data[symbol], new_bar])
        self.last_timestamp[symbol] = ts
        self.real_time_buffer[symbol].clear()
        logger.debug(f"[DATA] {symbol} 1분봉 추가: {ts}, 종가={close_p:.2f}")

    def compute_indicators(self, symbol: str) -> pd.DataFrame:
        """
        historical_data를 기반으로 기술적 지표(EMA, RSI, Bollinger Band, VWAP 등)를 계산하여 반환합니다.
        """
        df = self.historical_data[symbol].copy()
        if df.empty:
            return df

        # EMA
        df["ema_short"] = ta.trend.EMAIndicator(
            close=df["close"], window=self.config.ema_short_period
        ).ema_indicator()
        df["ema_long"] = ta.trend.EMAIndicator(
            close=df["close"], window=self.config.ema_long_period
        ).ema_indicator()

        # RSI
        df["rsi"] = ta.momentum.RSIIndicator(
            close=df["close"], window=self.config.rsi_period
        ).rsi()

        # Bollinger Band
        bb = ta.volatility.BollingerBands(
            close=df["close"],
            window=self.config.bb_period,
            window_dev=self.config.bb_std_dev
        )
        df["bb_hband"] = bb.bollinger_hband()
        df["bb_lband"] = bb.bollinger_lband()
        df["bb_mavg"] = bb.bollinger_mavg()

        # VWAP (1분봉 누적 기준)
        df["vwap"] = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()

        return df