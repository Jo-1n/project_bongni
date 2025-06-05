import threading
import time
import logging
from datetime import datetime

import numpy as np
import pytz

from typing import Callable, Dict, List

from src.data_handler import DataHandler
from src.risk_manager import RiskManager
from src.config import Config
from src.broker_api import BrokerAPI
from src.utils import is_nyse_open, is_nyse_close

# Placeholder import for AIClient (to be implemented in ai_client.py)
try:
    from src.ai_client import AIClient
except ImportError:
    AIClient = None

# Kiwoom import
try:
    from pykiwoom.kiwoom import Kiwoom
except ImportError:
    Kiwoom = None

logger = logging.getLogger(__name__)


class TradingBot:
    """
    전체 자동매매 로직을 수행하는 클래스입니다.

    • Live mode: event-driven via Kiwoom.OnReceiveRealData
    • Backtest mode: dummy tick feed + polling loop

    New features per revision_config:
      - Accepts an AIClient instance to get real predictions.
      - Supports plugin hooks: 'before_signal' and 'after_signal'.
      - Uses shared utils for market-open/close checks.
    """

    def __init__(
        self,
        config: Config,
        data_handler: DataHandler,
        risk_manager: RiskManager,
        ai_client: "AIClient" = None
    ):
        self.config = config
        self.data_handler = data_handler
        self.risk_manager = risk_manager
        self.ai_client = ai_client
        self.mode = getattr(self.config, "mode", "live")

        # Plugin hooks: lists of callables
        #   before_signal(symbol: str, df: pd.DataFrame) → None
        #   after_signal(symbol: str, signal: dict) → None
        self.plugins: Dict[str, List[Callable]] = {
            "before_signal": [],
            "after_signal": []
        }

        # Live‐mode setup
        self.kiwoom = None
        self.broker = None

        if self.mode == "live":
            if Kiwoom is None:
                raise EnvironmentError(
                    "Live mode requested but PyKiwoom is not installed."
                )

            # DataHandler must have instantiated Kiwoom
            self.kiwoom = self.data_handler.kiwoom
            if self.kiwoom is None:
                raise EnvironmentError(
                    "DataHandler was not initialized in live mode with Kiwoom."
                )

            # Attach event for real-time ticks
            self.kiwoom.OnReceiveRealData.connect(self._on_receive_real_data)
            logger.info("[BOT] Attached Kiwoom OnReceiveRealData handler.")

            # Initialize BrokerAPI wrapper
            self.broker = BrokerAPI(
                kiwoom=self.kiwoom,
                account_no=self.config.kiwoom_account
            )
        else:
            logger.info("[BOT] Running in backtest mode (no Kiwoom).")

        self.trading_day = None

    def register_plugin(self, hook_name: str, callback: Callable):
        """
        Register a callback for a plugin hook.

        hook_name: "before_signal" or "after_signal"
        callback: function to call with (symbol, df) or (symbol, signal_dict)
        """
        if hook_name not in self.plugins:
            raise ValueError(f"Unknown hook: {hook_name}")
        self.plugins[hook_name].append(callback)

    def initialize(self):
        """
        - Load historical data for all symbols.
        - Set self.trading_day (NYSE date) from UTC.
        """
        self.data_handler.update_historical_all()

        now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
        now_ny = now_utc.astimezone(self.config.time_zone)
        self.trading_day = now_ny.date()

        logger.info(f"[INIT] TradingBot initialized. Trading day (NY): {self.trading_day}")

    def fetch_realtime_ticks(self):
        """
        In backtest mode, start a dummy tick feed thread.
        In live mode, do nothing (Kiwoom callbacks drive ticks).
        """
        if self.mode == "live":
            return

        def _dummy_tick_feed():
            while True:
                now = datetime.utcnow().replace(tzinfo=pytz.utc)

                for symbol in self.config.symbols:
                    price = np.random.random() * 100
                    volume = np.random.randint(1, 10)
                    tick = {"datetime": now, "price": price, "volume": volume}

                    self.data_handler.update_realtime(symbol, tick)

                    # If a new minute bar just closed, generate & execute signal
                    last_ts = self.data_handler.last_timestamp[symbol]
                    if last_ts and last_ts == tick["datetime"].astimezone(self.config.time_zone).replace(second=0, microsecond=0):
                        sig = self.generate_signals(symbol)
                        if sig["signal"] != "HOLD":
                            self.execute_order(sig, symbol)

                time.sleep(1)

        thread = threading.Thread(target=_dummy_tick_feed, daemon=True)
        thread.start()
        logger.info("[BACKTEST] Dummy tick feed started.")

    def generate_signals(self, symbol: str) -> dict:
        """
        Generate BUY / SELL / HOLD based on:
          1) Technical indicators from DataHandler.compute_indicators()
          2) AI prediction via self.ai_client (when available)
          3) Weighted‐score logic as before

        Also invokes plugin hooks:
          - before_signal(symbol, df)
          - after_signal(symbol, signal_dict)

        Returns:
          { "signal": one of ["BUY","SELL","SELL_SL","SELL_TP","HOLD"],
            "price": float,
            "quantity": int }
        """
        df = self.data_handler.compute_indicators(symbol)

        # Plugin hook: before computing signal
        for fn in self.plugins["before_signal"]:
            try:
                fn(symbol, df)
            except Exception as e:
                logger.warning(f"[PLUGIN][before_signal] {symbol} error: {e}")

        # Not enough data → HOLD
        if df.empty or len(df) < max(
            self.config.ema_long_period,
            self.config.rsi_period,
            self.config.bb_period
        ):
            result = {"signal": "HOLD"}
            for fn in self.plugins["after_signal"]:
                try:
                    fn(symbol, result)
                except Exception as e:
                    logger.warning(f"[PLUGIN][after_signal] {symbol} error: {e}")
            return result

        latest = df.iloc[-1]
        prev   = df.iloc[-2]
        price  = latest["close"]

        # 1) EMA crossover
        ema_cross_up   = (prev["ema_short"] < prev["ema_long"]) and (latest["ema_short"] > latest["ema_long"])
        ema_cross_down = (prev["ema_short"] > prev["ema_long"]) and (latest["ema_short"] < latest["ema_long"])

        # 2) RSI
        rsi = latest["rsi"]
        rsi_oversold   = rsi < self.config.rsi_oversold
        rsi_overbought = rsi > self.config.rsi_overbought

        # 3) Bollinger Band
        bb_break_up   = (prev["close"] <= prev["bb_hband"]) and (price > latest["bb_hband"])
        bb_break_down = (prev["close"] >= prev["bb_lband"]) and (price < latest["bb_lband"])

        # 4) VWAP
        vwap_break_up   = (prev["close"] <= prev["vwap"]) and (price > latest["vwap"])
        vwap_break_down = (prev["close"] >= prev["vwap"]) and (price < latest["vwap"])

        # 5) AI prediction
        if self.ai_client is not None:
            # Example: pass the last N rows as features
            features = df.tail(self.config.ema_long_period * 2).to_dict(orient="list")
            try:
                predicted_return = self.ai_client.predict(symbol, features)
            except Exception as e:
                logger.warning(f"[AI] Prediction failed for {symbol}: {e}")
                predicted_return = 0.0
        else:
            # Fallback to random stub if AIClient isn’t provided
            predicted_return = np.random.uniform(-0.01, 0.01)

        ai_buy_signal  = (predicted_return > 0.005)
        ai_sell_signal = (predicted_return < -0.005)

        # 6) Weighted score
        buy_score = 0.0
        if ema_cross_up:   buy_score += 1.0
        if rsi_oversold:   buy_score += 0.5
        if bb_break_up:    buy_score += 0.7
        if vwap_break_up:  buy_score += 0.5
        if ai_buy_signal:  buy_score += 1.0

        sell_score = 0.0
        if ema_cross_down: sell_score += 1.0
        if rsi_overbought: sell_score += 0.5
        if bb_break_down:  sell_score += 0.7
        if vwap_break_down: sell_score += 0.5
        if ai_sell_signal: sell_score += 1.0

        BUY_THRESHOLD  = 1.5
        SELL_THRESHOLD = 1.5

        has_position = (
            symbol in self.risk_manager.positions and
            self.risk_manager.positions[symbol].is_open
        )

        # BUY signal
        result = {"signal": "HOLD"}
        if (buy_score >= BUY_THRESHOLD) and (not has_position) and self.risk_manager.can_open_position(symbol, price):
            size_info = self.risk_manager.calculate_position_size(symbol, price)
            if size_info is not None:
                quantity, _, _ = size_info
                result = {"signal": "BUY", "price": price, "quantity": quantity}

        # SELL signal
        elif has_position and (sell_score >= SELL_THRESHOLD):
            result = {"signal": "SELL", "price": price, "quantity": 0}

        # Stop-loss / Take-profit override
        if has_position:
            pos = self.risk_manager.positions[symbol]
            if pos.check_stop_loss(price):
                result = {"signal": "SELL_SL", "price": price, "quantity": 0}
            elif pos.check_take_profit(price):
                result = {"signal": "SELL_TP", "price": price, "quantity": 0}

        # Plugin hook: after computing signal
        for fn in self.plugins["after_signal"]:
            try:
                fn(symbol, result)
            except Exception as e:
                logger.warning(f"[PLUGIN][after_signal] {symbol} error: {e}")

        return result

    def execute_order(self, signal: dict, symbol: str):
        """
        Execute a trade based on the generated signal.

        • Live mode: uses BrokerAPI for real orders + RiskManager updates.
        • Backtest mode: only RiskManager updates (no external API).
        """
        sig_type = signal.get("signal", "HOLD")
        price    = signal.get("price", 0.0)
        quantity = signal.get("quantity", 0)

        if sig_type == "BUY":
            if self.mode == "live":
                try:
                    self.broker.send_order("BUY", symbol, quantity, price, order_type="LIMIT")
                    self.risk_manager.open_position(symbol, price)
                except Exception as e:
                    logger.error(f"[ORDER][BUY] {symbol} failed: {e}")
            else:
                try:
                    self.risk_manager.open_position(symbol, price)
                    logger.info(f"[BACKTEST][BUY] {symbol} qty={quantity} @ {price:.2f}")
                except Exception as e:
                    logger.error(f"[BACKTEST][BUY] {symbol} RiskManager failed: {e}")

        elif sig_type in ("SELL", "SELL_SL", "SELL_TP"):
            if self.mode == "live":
                try:
                    pos = self.risk_manager.positions.get(symbol)
                    qty_to_sell = pos.quantity if pos else 0
                    self.broker.send_order("SELL", symbol, qty_to_sell, price, order_type="LIMIT")
                    self.risk_manager.close_position(symbol, price)
                except Exception as e:
                    logger.error(f"[ORDER][SELL] {symbol} failed: {e}")
            else:
                try:
                    self.risk_manager.close_position(symbol, price)
                    logger.info(f"[BACKTEST][SELL] {symbol} @ {price:.2f}")
                except Exception as e:
                    logger.error(f"[BACKTEST][SELL] {symbol} RiskManager failed: {e}")

        # HOLD → do nothing

    def run(self):
        """
        Main loop:

        • Live mode:
            - Call initialize()
            - Sleep until market close (16:00 NY), then final cleanup.
            - All trading is driven by _on_receive_real_data.

        • Backtest mode:
            - Call initialize()
            - Start dummy tick feed
            - Poll every loop_interval_sec: generate signals on latest bar & execute
            - Check daily targets; exit if hit or if market close.
            - Final cleanup.
        """
        self.initialize()

        if self.mode == "live":
            logger.info("[BOT] Live mode: awaiting real-time ticks...")
            while True:
                now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
                if is_nyse_close(now_utc, self.config.time_zone):
                    logger.info("[MARKET] Market closed. Starting final cleanup.")
                    break
                time.sleep(30)
            self._final_cleanup()

        else:
            logger.info("[BOT] Backtest mode: starting dummy tick feed.")
            self.fetch_realtime_ticks()
            while True:
                now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
                if is_nyse_close(now_utc, self.config.time_zone):
                    logger.info("[BACKTEST] Market closed. Starting final cleanup.")
                    break

                for symbol in self.config.symbols:
                    df = self.data_handler.historical_data[symbol]
                    if df.empty:
                        continue
                    sig = self.generate_signals(symbol)
                    if sig["signal"] != "HOLD":
                        self.execute_order(sig, symbol)

                if not self.risk_manager.check_daily_targets():
                    logger.info("[BACKTEST] Daily target/loss reached. Exiting loop.")
                    break

                time.sleep(self.config.loop_interval_sec)

            self._final_cleanup()

    def _on_receive_real_data(self, sRealType, sRealData):
        """
        Kiwoom calls this whenever a subscribed real‐time event arrives.
        sRealType: the real‐time type code (e.g., “주식체결” for tick)
        sRealData: dict or raw data containing fields like 체결시간, 현재가, 거래량, 종목코드.
        """
        if sRealType != "주식체결":
            return

        # Extract symbol, time, price, volume
        symbol = sRealData["종목코드"]
        date_str = datetime.now(pytz.utc).astimezone(self.config.time_zone).strftime("%Y%m%d")
        time_str = sRealData["체결시간"]  # e.g., "093012"
        # parse into NY‐tz datetime
        dt_naive = datetime.strptime(date_str + time_str, "%Y%m%d%H%M%S")
        dt_ny = self.config.time_zone.localize(dt_naive)
        price = float(sRealData["현재가"])
        volume = int(sRealData["거래량"])

        tick = {"datetime": dt_ny, "price": price, "volume": volume}
        self.data_handler.update_realtime(symbol, tick)

        # If that tick closed a new 1-min bar, generate & execute
        last_ts = self.data_handler.last_timestamp[symbol]
        if last_ts and last_ts == tick["datetime"].replace(second=0, microsecond=0):
            sig = self.generate_signals(symbol)
            if sig["signal"] != "HOLD":
                self.execute_order(sig, symbol)

    def _final_cleanup(self):
        """
        At market close, liquidate all open positions.
        """
        logger.info("[CLEANUP] Liquidating all open positions...")
        for symbol, pos in list(self.risk_manager.positions.items()):
            if pos.is_open:
                df = self.data_handler.historical_data[symbol]
                last_price = df["close"].iloc[-1] if not df.empty else 0.0
                try:
                    if self.mode == "live":
                        qty_to_sell = pos.quantity
                        self.broker.send_order("SELL", symbol, qty_to_sell, last_price, order_type="LIMIT")
                    self.risk_manager.close_position(symbol, last_price)
                    logger.info(f"[CLEANUP] {symbol} closed @ {last_price:.2f}")
                except Exception as e:
                    logger.error(f"[CLEANUP] Failed to close {symbol}: {e}")
        logger.info("[CLEANUP] All positions liquidated.")