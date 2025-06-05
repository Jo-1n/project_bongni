import os
import sys
import time
import logging
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import pytz

from src.config import Config
from src.indicators import (
    compute_ema,
    compute_rsi,
    compute_bb,
    compute_vwap,
    compute_atr,
)

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# If running under Windows, import PyKiwoom; else stub
# -----------------------------------------------------------------------------
if sys.platform.startswith("win"):
    try:
        from pykiwoom.kiwoom import Kiwoom
    except ImportError as e:
        raise ImportError(
            "PyKiwoom is required on Windows. Install via 'pip install pykiwoom'."
        ) from e
else:
    Kiwoom = None


class DataHandler:
    """
    Manages historical 1-minute bars and real-time tick aggregation.

    Attributes:
        config:            Config
        mode:              "live" or "backtest"
        time_zone:         pytz timezone (e.g., America/New_York)
        local_tz:          pytz timezone (e.g., Asia/Seoul)
        historical_data:   Dict[str, pd.DataFrame]
                           – Each DataFrame has columns:
                             ['open','high','low','close','volume',
                              'ema_short','ema_long','rsi',
                              'bb_hband','bb_lband','bb_mavg',
                              'vwap','atr']
                           – Indexed by tz-aware datetime (market tz)
        real_time_buffer:  Dict[str, Dict[datetime, List[Dict[str,Any]]]]
                           – For each symbol: minute_ts → list of tick dicts
        last_timestamp:    Dict[str, Optional[datetime]] – last finalized minute per symbol
        kiwoom:            Kiwoom instance if live+Windows; else None
    """

    def __init__(self, config: Config, mode: str = "live"):
        self.config = config
        self.mode = mode  # "live" or "backtest"
        self.time_zone = config.time_zone    # e.g., America/New_York
        self.local_tz = config.local_tz      # e.g., Asia/Seoul

        # Initialize empty DataFrames for each symbol
        self.historical_data = {
            symbol: pd.DataFrame(columns=[
                "open", "high", "low", "close", "volume",
                "ema_short", "ema_long", "rsi",
                "bb_hband", "bb_lband", "bb_mavg",
                "vwap", "atr"
            ])
            for symbol in self.config.symbols
        }

        # Per-symbol real-time tick buffer: {symbol → {minute_ts → [tick_dicts]}}
        self.real_time_buffer = {symbol: {} for symbol in self.config.symbols}

        # Track last committed minute timestamp (tz-aware) per symbol
        self.last_timestamp = {symbol: None for symbol in self.config.symbols}

        # If in live mode on Windows, connect to Kiwoom
        if self.mode == "live" and Kiwoom is not None:
            if not sys.platform.startswith("win"):
                raise EnvironmentError("KiwoomOpenAPI+ only works on Windows.")
            self.kiwoom = Kiwoom()
            logger.info("[KIWOOM] Connecting to Kiwoom OpenAPI+...")
            self.kiwoom.CommConnect(block=True)
            logger.info("[KIWOOM] Connected.")
        else:
            self.kiwoom = None
            if self.mode == "live":
                logger.warning(
                    "[DATA_HANDLER] Live mode requested but Kiwoom is unavailable."
                )

    # -------------------------------------------------------------------------
    # Public API: Historical Data Loading
    # -------------------------------------------------------------------------
    def fetch_historical(self, symbol: str) -> pd.DataFrame:
        """
        Retrieve historical 1-minute bars for 'symbol'.

        - If mode == "backtest": load from CSV via _load_from_csv().
        - If mode == "live": fetch from Kiwoom via _fetch_historical_kiwoom().
        """
        if self.mode == "backtest":
            return self._load_from_csv(symbol)

        # Live mode
        if self.kiwoom is None:
            raise EnvironmentError("Kiwoom API is not available in this environment.")
        return self._fetch_historical_kiwoom(symbol)

    def update_historical_all(self):
        """
        On startup, load historical data for ALL symbols and store in self.historical_data.

        After loading:
          - self.last_timestamp[symbol] = most recent minute_ts for that symbol
          - Logs row count or warns if empty.
        """
        for symbol in self.config.symbols:
            try:
                df = self.fetch_historical(symbol)
            except Exception as e:
                logger.error(f"[DATA] Failed to load historical for {symbol}: {e}")
                df = pd.DataFrame(columns=[
                    "open", "high", "low", "close", "volume",
                    "ema_short", "ema_long", "rsi",
                    "bb_hband", "bb_lband", "bb_mavg",
                    "vwap", "atr"
                ])

            if not df.empty:
                df = df.sort_index()
                self.historical_data[symbol] = df
                self.last_timestamp[symbol] = df.index.max()
                logger.info(f"[DATA] {symbol} historical loaded: {len(df)} rows.")
            else:
                self.historical_data[symbol] = df
                self.last_timestamp[symbol] = None
                logger.warning(f"[DATA] {symbol} has no historical bars.")

    # -------------------------------------------------------------------------
    # Private: Load from CSV (backtest)
    # -------------------------------------------------------------------------
    def _load_from_csv(self, symbol: str) -> pd.DataFrame:
        """
        Load historical 1-min bars from CSV: data/historical/{symbol}_1min.csv.

        Expects columns: ['datetime','open','high','low','close','volume'].
        Returns a DataFrame indexed by tz-aware datetime in time_zone, pruned to last historical_lookback_days.
        """
        path = f"data/historical/{symbol}_1min.csv"
        if not os.path.exists(path):
            raise FileNotFoundError(f"No CSV for {symbol} at {path}")

        df = pd.read_csv(path, parse_dates=["datetime"])
        df.set_index("datetime", inplace=True)

        # Localize or convert to market tz
        if df.index.tzinfo is None:
            df.index = df.index.tz_localize(self.time_zone)
        else:
            df.index = df.index.tz_convert(self.time_zone)

        # Prune to last N days
        cutoff = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(self.time_zone) - timedelta(
            days=self.config.historical_lookback_days
        )
        df = df[df.index >= cutoff]

        # Compute indicators
        df = self._compute_all_indicators(df)
        return df

    # -------------------------------------------------------------------------
    # Private: Fetch from Kiwoom (live mode)
    # -------------------------------------------------------------------------
    def _fetch_historical_kiwoom(self, symbol: str) -> pd.DataFrame:
        """
        Use PyKiwoom to request 1-min bars via TR 'opt10080'.

        Returns a DataFrame indexed by tz-aware datetime with columns:
        ['open','high','low','close','volume','ema_short','ema_long','rsi','bb_hband','bb_lband','bb_mavg','vwap','atr'].
        """
        all_pages = []
        next_flag = "0"
        rqname = f"{symbol}_분봉요청"
        trcode = "opt10080"
        screen_no = "1000"

        while True:
            # Set TR inputs
            self.kiwoom.SetInputValue("종목코드", symbol)
            self.kiwoom.SetInputValue("틱범위", "1")       # 1-minute
            self.kiwoom.SetInputValue("수정주가구분", "1")   # adjusted

            df_page = self.kiwoom.block_request(
                trcode,
                rqname=rqname,
                next=next_flag,
                screen_no=screen_no,
                output="주식분봉차트조회"
            )
            all_pages.append(df_page)

            try:
                has_more = self.kiwoom.remained_data
            except AttributeError:
                has_more = False

            if not has_more:
                break

            next_flag = "2"
            time.sleep(0.2)  # respect ≤ 5 TR calls/sec

        if not all_pages:
            return pd.DataFrame(columns=[
                "open", "high", "low", "close", "volume",
                "ema_short", "ema_long", "rsi",
                "bb_hband", "bb_lband", "bb_mavg",
                "vwap", "atr"
            ])

        df_raw = pd.concat(all_pages, ignore_index=True)

        # Rename & parse columns
        df_renamed = pd.DataFrame({
            "datetime": df_raw["체결시간"],
            "open":     df_raw["시가"],
            "high":     df_raw["고가"],
            "low":      df_raw["저가"],
            "close":    df_raw["현재가"].abs(),
            "volume":   df_raw["거래량"]
        })

        def parse_minute_ts(x):
            if isinstance(x, str):
                try:
                    dt_naive = datetime.strptime(x, "%Y%m%d %H%M%S")
                except ValueError:
                    dt_naive = datetime.strptime(str(x), "%Y%m%d%H%M%S")
            else:
                dt_naive = pd.to_datetime(x, format="%Y%m%d%H%M%S").to_pydatetime()
            return self.time_zone.localize(dt_naive)

        df_renamed["datetime"] = df_renamed["datetime"].apply(parse_minute_ts)
        df_renamed.set_index("datetime", inplace=True)
        df_sorted = df_renamed.sort_index()

        cutoff = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(self.time_zone) - timedelta(
            days=self.config.historical_lookback_days
        )
        df_sorted = df_sorted[df_sorted.index >= cutoff]

        # Compute indicators
        df_sorted = self._compute_all_indicators(df_sorted)
        return df_sorted

    # -------------------------------------------------------------------------
    # Real-time tick ingestion → time-based 1-min aggregation
    # -------------------------------------------------------------------------
    def update_realtime(self, symbol: str, new_tick: dict):
        """
        Called for each real-time tick:
          new_tick: {'datetime': datetime (UTC-naive or tz-aware), 'price': float, 'volume': int}

        Steps:
          1) Convert new_tick['datetime'] → tz-aware UTC → to market tz.
          2) Floor to the minute: minute_ts = dt_ny.replace(sec=0,μs=0).
          3) Buffer under real_time_buffer[symbol][minute_ts].
          4) If minute_ts > last_timestamp[symbol], finalize all prior minutes via _finalize_minute_bar().
        """
        raw_dt = new_tick["datetime"]
        if raw_dt.tzinfo is None:
            raw_dt = pytz.utc.localize(raw_dt)

        dt_ny = raw_dt.astimezone(self.time_zone)
        minute_ts = dt_ny.replace(second=0, microsecond=0)

        buff = self.real_time_buffer[symbol]
        if minute_ts not in buff:
            buff[minute_ts] = []
        buff[minute_ts].append({
            "datetime": dt_ny,
            "price": new_tick["price"],
            "volume": new_tick["volume"]
        })

        last_ts = self.last_timestamp[symbol]
        if last_ts is not None and minute_ts > last_ts:
            to_finalize = [ts for ts in buff if ts <= last_ts]
            for ts in to_finalize:
                self._finalize_minute_bar(symbol, ts)

            self.last_timestamp[symbol] = minute_ts

    def _finalize_minute_bar(self, symbol: str, minute_ts: datetime):
        """
        Aggregate buffered ticks for 'minute_ts' into a 1-min bar:
          - open = first tick price
          - high = max price
          - low  = min price
          - close= last tick price
          - volume = sum volumes
        Then append to historical_data and run data checks & pruning.
        """
        buffer_for_minute = self.real_time_buffer[symbol].pop(minute_ts, [])
        if not buffer_for_minute:
            logger.warning(
                f"[DATA] {symbol}: no ticks for minute {minute_ts.isoformat()} → skipping"
            )
            return

        df_ticks = pd.DataFrame(buffer_for_minute).set_index("datetime")
        open_p  = df_ticks["price"].iloc[0]
        high_p  = df_ticks["price"].max()
        low_p   = df_ticks["price"].min()
        close_p = df_ticks["price"].iloc[-1]
        volume  = df_ticks["volume"].sum()

        new_bar = pd.DataFrame({
            "open":  [open_p],
            "high":  [high_p],
            "low":   [low_p],
            "close": [close_p],
            "volume":[volume]
        }, index=[minute_ts])

        # Append
        self.historical_data[symbol] = pd.concat(
            [self.historical_data[symbol], new_bar]
        )

        # Data integrity checks
        hist = self.historical_data[symbol]
        if len(hist) >= 2:
            prev_ts = hist.index[-2]
            prev_close = hist["close"].iloc[-2]

            # Gap check
            if (minute_ts - prev_ts) > timedelta(minutes=1):
                logger.warning(
                    f"[DATA] {symbol}: gap {prev_ts.isoformat()} → {minute_ts.isoformat()}"
                )

            # Outlier check
            jump_pct = abs((close_p - prev_close) / prev_close)
            if jump_pct > 0.10:
                logger.warning(
                    f"[DATA] {symbol}: outlier @ {minute_ts.isoformat()}, jump {jump_pct*100:.1f}%"
                )

        # Update last_timestamp if not set
        if self.last_timestamp[symbol] is None:
            self.last_timestamp[symbol] = minute_ts

        # Prune old bars
        self._prune_old_bars(symbol)

        # Recompute indicators on the updated DataFrame slice
        df_ind = self._compute_all_indicators(self.historical_data[symbol])
        self.historical_data[symbol] = df_ind

        logger.debug(
            f"[DATA] {symbol}: 1-min bar added {minute_ts.isoformat()} | close={close_p:.2f}, vol={volume}"
        )

    def _prune_old_bars(self, symbol: str):
        """
        Keep only the last M minutes of history, where M = 3 × max(ema_long, rsi, bb).
        """
        df = self.historical_data[symbol]
        if df.empty:
            return

        latest_ts = df.index.max()
        lookback_minutes = max(
            self.config.ema_long_period,
            self.config.rsi_period,
            self.config.bb_period
        ) * 3
        cutoff = latest_ts - timedelta(minutes=lookback_minutes)
        self.historical_data[symbol] = df[df.index >= cutoff]

    def _compute_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Given a DataFrame with ['open','high','low','close','volume'], compute and append:
          - EMA (short & long)
          - RSI
          - Bollinger Bands (hband, lband, mavg)
          - VWAP (cumulative)
          - ATR
        Returns a new DataFrame with added columns.
        """
        if df.empty:
            return df

        df = df.copy()

        # EMA
        df["ema_short"] = compute_ema(df, self.config.ema_short_period)
        df["ema_long"]  = compute_ema(df, self.config.ema_long_period)

        # RSI
        df["rsi"] = compute_rsi(df, self.config.rsi_period)

        # Bollinger Bands
        hband, lband, mavg = compute_bb(
            df, self.config.bb_period, self.config.bb_std_dev
        )
        df["bb_hband"], df["bb_lband"], df["bb_mavg"] = hband, lband, mavg

        # VWAP (cumulative)
        df["vwap"] = compute_vwap(df)

        # ATR
        df["atr"] = compute_atr(df, self.config.atr_period)

        return df

    def compute_indicators(self, symbol: str) -> pd.DataFrame:
        """
        Return the current 1-minute bar DataFrame for 'symbol', including all indicators.
        """
        return self.historical_data[symbol].copy()