TradingBot System: AI-Optimized Architecture Specification

This document is designed for AI agents (e.g., LLMs, code interpreters, refactoring tools) to understand, modify, and extend the Automatic Trading Bot architecture. It provides:
	•	Intent & Objectives (machine-readable)
	•	Module Interfaces (function signatures, data types)
	•	Data Schemas (JSON, Python types)
	•	Control Flow (pseudocode blocks)
	•	Integration Contracts (AI Model, Broker API)
	•	Configuration Schema (config.json structure)
	•	Extension Points (hooks, TODOs)

⸻

1. SYSTEM INTENT (Machine-Readable)

{
  "system_name": "Automatic Trading Bot",
  "purpose": "Fully automated intraday trading using hybrid technical+AI signals.",
  "input": {
    "tick_data": {"type": "object", "properties": {
      "datetime": "ISO8601 string",
      "symbol": "string",
      "price": "float",
      "volume": "int"
    }},
    "config": {"$ref": "#/components/schemas/ConfigJSON"}
  },
  "output": {
    "orders": {"type": "array", "items": {"$ref": "#/components/schemas/Order"}},
    "logs": "text entries with timestamps",
    "metrics": {"type": "object", "properties": {
      "capital": "float", "available_cash": "float", "positions": "object"
    }}
  },
  "modes": ["live", "backtest"],
  "frequency": {"tick_resolution": "1s", "bar_resolution": "1m"}
}


⸻

2. CONFIGURATION SCHEMA (config.json)

JSON Schema (Draft 07)

{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TradingBot Config",
  "type": "object",
  "properties": {
    "mode": {"type": "string", "enum": ["live", "backtest"]},
    "symbols": {"type": "array", "items": {"type": "string"}},
    "time_zone": {"type": "string", "description": "IANA time zone name, e.g., 'America/New_York'"},
    "broker": {
      "type": "object",
      "properties": {
        "api_type": {"type": "string", "enum": ["kiwoom", "other"]},
        "credentials": {
          "type": "object",
          "properties": {
            "account_id": {"type": "string"},
            "access_token": {"type": "string"}
          },
          "required": ["account_id", "access_token"]
        }
      },
      "required": ["api_type", "credentials"]
    },
    "risk_params": {
      "type": "object",
      "properties": {
        "max_position_pct": {"type": "number", "minimum": 0, "maximum": 1},
        "daily_max_loss_pct": {"type": "number", "minimum": 0, "maximum": 1},
        "daily_target_pct": {"type": "number", "minimum": 0, "maximum": 1}
      },
      "required": ["max_position_pct", "daily_max_loss_pct", "daily_target_pct"]
    },
    "indicator_params": {
      "type": "object",
      "properties": {
        "ema_short_period": {"type": "integer", "minimum": 1},
        "ema_long_period": {"type": "integer", "minimum": 1},
        "rsi_period": {"type": "integer", "minimum": 1},
        "rsi_oversold": {"type": "number", "minimum": 0, "maximum": 100},
        "rsi_overbought": {"type": "number", "minimum": 0, "maximum": 100},
        "bb_period": {"type": "integer", "minimum": 1},
        "bb_dev": {"type": "number", "minimum": 0}
      },
      "required": ["ema_short_period", "ema_long_period", "rsi_period", "rsi_oversold", "rsi_overbought", "bb_period", "bb_dev"]
    },
    "ai_model": {
      "type": "object",
      "properties": {
        "endpoint_url": {"type": "string", "format": "uri"},
        "headers": {"type": "object", "additionalProperties": {"type": "string"}}
      },
      "required": ["endpoint_url"]
    },
    "logging": {
      "type": "object",
      "properties": {
        "log_file_path": {"type": "string"},
        "log_level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]}
      },
      "required": ["log_file_path", "log_level"]
    }
  },
  "required": ["mode", "symbols", "time_zone", "broker", "risk_params", "indicator_params", "ai_model", "logging"]
}

Example config.json

{
  "mode": "live",
  "symbols": ["AAPL", "MSFT", "GOOG"],
  "time_zone": "America/New_York",
  "broker": {"api_type": "kiwoom", "credentials": {"account_id": "ABC123", "access_token": "XYZ456"}},
  "risk_params": {"max_position_pct": 0.10, "daily_max_loss_pct": 0.05, "daily_target_pct": 0.02},
  "indicator_params": {"ema_short_period": 12, "ema_long_period": 26, "rsi_period": 14, "rsi_oversold": 30.0, "rsi_overbought": 70.0, "bb_period": 20, "bb_dev": 2.0},
  "ai_model": {"endpoint_url": "https://api.example.com/predict", "headers": {"Authorization": "Bearer TOKEN"}},
  "logging": {"log_file_path": "logs/bot.log", "log_level": "INFO"}
}


⸻

3. MODULE INTERFACES (Python Signatures & Types)

3.1. Config (src/config.py)

from typing import List, Dict, Any

class Config:
    def __init__(self, config_dict: Dict[str, Any]) -> None:
        self.mode: str  # 'live' or 'backtest'
        self.symbols: List[str]
        self.time_zone: str
        self.broker_api_type: str
        self.broker_credentials: Dict[str, str]
        self.max_position_pct: float
        self.daily_max_loss_pct: float
        self.daily_target_pct: float
        self.ema_short_period: int
        self.ema_long_period: int
        self.rsi_period: int
        self.rsi_oversold: float
        self.rsi_overbought: float
        self.bb_period: int
        self.bb_dev: float
        self.ai_endpoint: str
        self.ai_headers: Dict[str, str]
        self.log_file_path: str
        self.log_level: str
        # Internal validation: raise ValueError if missing keys or type mismatch
    
    @staticmethod
    def from_json(path: str) -> 'Config':
        """Parses config.json, returns Config instance."""

3.2. DataHandler (src/data_handler.py)

import pandas as pd
from typing import Dict, Any

class DataHandler:
    historical_data: Dict[str, pd.DataFrame]   # symbol -> DataFrame
    real_time_buffer: Dict[str, list[Dict[str, Any]]]  # symbol -> list of ticks

    def __init__(self, symbols: list[str], lookback_days: int) -> None:
        """Initialize empty buffers and load historical CSV if backtest mode."""

    def fetch_historical(self, symbol: str) -> pd.DataFrame:
        """Returns DataFrame with OHLCV bars for last lookback_days."""

    def update_historical_all(self) -> None:
        """Load historical for all symbols; store in self.historical_data."""

    def update_realtime(self, symbol: str, tick: Dict[str, Any]) -> None:
        """Append tick to buffer; every 60 ticks → aggregate to minute bar."""

    def _aggregate_to_minute_bar(self, symbol: str) -> None:
        """Converts buffered ticks into one OHLCV row, appends to historical_data."""

    def compute_indicators(self, symbol: str) -> pd.DataFrame:
        """Given DataFrame self.historical_data[symbol], returns with added columns: ema_short, ema_long, rsi, bb_hband, bb_lband, vwap."""

3.3. RiskManager (src/risk_manager.py)

from typing import Dict, Any, Optional

class Position:
    symbol: str
    entry_price: float
    quantity: int
    stop_loss: float
    take_profit: float
    is_open: bool

    def __init__(self, symbol: str, entry_price: float, quantity: int, stop_loss: float, take_profit: float) -> None:
        self.symbol = symbol
        self.entry_price = entry_price
        self.quantity = quantity
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.is_open = True

    def check_stop_loss(self, price: float) -> bool:
        return price <= self.stop_loss

    def check_take_profit(self, price: float) -> bool:
        return price >= self.take_profit

class RiskManager:
    def __init__(self, starting_capital: float, max_position_pct: float, daily_max_loss_pct: float, daily_target_pct: float) -> None:
        self.capital: float = starting_capital
        self.available_cash: float = starting_capital
        self.positions: Dict[str, Position] = {}
        self.daily_starting_capital: float = starting_capital
        self.max_position_pct: float = max_position_pct
        self.daily_max_loss_pct: float = daily_max_loss_pct
        self.daily_target_pct: float = daily_target_pct

    def can_open_position(self, symbol: str, price: float) -> bool:
        """Checks cash, position sizing, and drawdown constraints."""
        invested = sum(pos.entry_price * pos.quantity for pos in self.positions.values() if pos.is_open)
        if (price * 1) > (self.capital * self.max_position_pct):
            return False
        if (price * 1) > self.available_cash:
            return False
        drawdown = (self.daily_starting_capital - self.capital) / self.daily_starting_capital
        if drawdown >= self.daily_max_loss_pct:
            return False
        return True

    def open_position(self, symbol: str, price: float, quantity: int) -> None:
        """Creates Position, deducts capital and cash."""
        sl = price * (1 - self.daily_max_loss_pct)
        tp = price * (1 + self.daily_target_pct)
        self.positions[symbol] = Position(symbol, price, quantity, sl, tp)
        self.available_cash -= price * quantity

    def close_position(self, symbol: str, exit_price: float) -> Optional[float]:
        """Closes existing position, returns P&L or None if no position."""
        pos = self.positions.get(symbol)
        if not pos or not pos.is_open:
            return None
        profit = (exit_price - pos.entry_price) * pos.quantity
        self.capital += profit
        self.available_cash += exit_price * pos.quantity
        pos.is_open = False
        return profit

    def check_daily_targets(self) -> bool:
        """Returns True to continue trading; False to stop."""
        ret = (self.capital - self.daily_starting_capital) / self.daily_starting_capital
        if ret >= self.daily_target_pct:
            return False
        drawdown = (self.daily_starting_capital - self.capital) / self.daily_starting_capital
        if drawdown >= self.daily_max_loss_pct:
            return False
        return True

3.4. TradingBot (src/trading_bot.py)

from typing import Dict, Any
from datetime import datetime, timezone

class TradingBot:
    def __init__(self, config: Config, data_handler: DataHandler, risk_manager: RiskManager) -> None:
        self.config = config
        self.data_handler = data_handler
        self.risk_manager = risk_manager
        self.trading_day = None

    def initialize(self) -> None:
        """Load historical data, login broker, compute trading day."""
        self.data_handler.update_historical_all()
        self._login_broker()
        self._set_trading_day()

    def _login_broker(self) -> None:
        """Placeholder for Kiwoом or other API login."""
        pass

    def _set_trading_day(self) -> None:
        """Compute current trading day based on config.time_zone."""
        now_utc = datetime.now(timezone.utc)
        # Convert to config.time_zone via pytz (omitted for brevity)
        self.trading_day = now_utc.date()

    def fetch_realtime_ticks(self) -> None:
        """Starts tick listener (real or dummy)."""
        # In live: subscribe to Kiwoom OnReceiveRealData callback
        # In backtest: skip
        pass

    def generate_signals(self, symbol: str) -> Dict[str, Any]:
        """Compute indicators, fetch AI, and combine rule-based signals."""
        df = self.data_handler.compute_indicators(symbol)
        if df.shape[0] < max(self.config.ema_long_period, self.config.rsi_period, self.config.bb_period):
            return {"signal": "HOLD", "price": None, "quantity": 0}
        prev = df.iloc[-2]
        latest = df.iloc[-1]
        price = latest.close

        # Rule-based signals
        ema_up = prev.ema_short < prev.ema_long and latest.ema_short > latest.ema_long
        ema_down = prev.ema_short > prev.ema_long and latest.ema_short < latest.ema_long
        rsi_low = latest.rsi < self.config.rsi_oversold
        rsi_high = latest.rsi > self.config.rsi_overbought
        bb_up = prev.close <= prev.bb_hband and latest.close > latest.bb_hband
        bb_down = prev.close >= prev.bb_lband and latest.close < latest.bb_lband
        vwap_up = prev.close <= prev.vwap and latest.close > latest.vwap
        vwap_down = prev.close >= prev.vwap and latest.close < latest.vwap

        # AI signal
        ai_pred = self._ai_predict(symbol, df.tail(self.config.ema_long_period * 2))
        ai_buy = ai_pred > 0.005
        ai_sell = ai_pred < -0.005

        buy_score = sum([ema_up, rsi_low, bb_up, vwap_up, ai_buy])
        sell_score = sum([ema_down, rsi_high, bb_down, vwap_down, ai_sell])

        has_pos = symbol in self.risk_manager.positions and self.risk_manager.positions[symbol].is_open
        if buy_score >= 1.5 and not has_pos and self.risk_manager.can_open_position(symbol, price):
            qty = int((self.risk_manager.capital * self.config.max_position_pct) // price)
            if qty >= 1:
                return {"signal": "BUY", "price": price, "quantity": qty}
        if has_pos and sell_score >= 1.5:
            return {"signal": "SELL", "price": price, "quantity": 0}
        # Stop-loss / take-profit override
        if has_pos:
            pos = self.risk_manager.positions[symbol]
            if pos.check_stop_loss(price):
                return {"signal": "SELL_SL", "price": price, "quantity": 0}
            if pos.check_take_profit(price):
                return {"signal": "SELL_TP", "price": price, "quantity": 0}
        return {"signal": "HOLD", "price": price, "quantity": 0}

    def _ai_predict(self, symbol: str, df: Any) -> float:
        """Sends HTTP POST to AI endpoint, returns predicted_return."""
        # example:
        # payload = df.to_dict(orient='list')
        # resp = requests.post(self.config.ai_endpoint, headers=self.config.ai_headers, json=payload)
        # return resp.json().get('predicted_return', 0.0)
        return 0.0  # placeholder

    def execute_order(self, signal_dict: Dict[str, Any]) -> None:
        """Interprets signal and calls RiskManager and BrokerAPI."""
        sig = signal_dict.get("signal")
        sym = signal_dict.get("symbol")
        price = signal_dict.get("price")
        qty = signal_dict.get("quantity")
        if sig == "BUY":
            self.risk_manager.open_position(sym, price, qty)
            # BrokerAPI.send_order('BUY', sym, price, qty)
        elif sig in ["SELL", "SELL_SL", "SELL_TP"]:
            profit = self.risk_manager.close_position(sym, price)
            # BrokerAPI.send_order('SELL', sym, price, qty=0)
        # else HOLD: do nothing

    def run(self) -> None:
        """Main loop: fetch ticks, generate & execute signals, check risk."""
        self.fetch_realtime_ticks()
        while True:
            if not self._market_open():
                time.sleep(60)
                continue
            for symbol in self.config.symbols:
                sig = self.generate_signals(symbol)
                if sig['signal'] != 'HOLD':
                    self.execute_order({**sig, 'symbol': symbol})
            if not self.risk_manager.check_daily_targets():
                break
            time.sleep(1)
        self._final_cleanup()

    def _market_open(self) -> bool:
        """Return True if current UTC time is within market hours."""
        now = datetime.now(timezone.utc)
        # Simplified window; replace with real calendar check
        return True

    def _final_cleanup(self) -> None:
        """Force-close all open positions at last close."""
        for symbol, pos in self.risk_manager.positions.items():
            if pos.is_open:
                price = self.data_handler.historical_data[symbol].iloc[-1].close
                self.risk_manager.close_position(symbol, price)


⸻

4. ORDER SCHEMA & CONTRACTS (OpenAPI / Internal)

4.1. Order Data Model

{
  "type": "object",
  "properties": {
    "symbol": {"type": "string"},
    "direction": {"type": "string", "enum": ["BUY", "SELL"]},
    "price": {"type": "number"},
    "quantity": {"type": "integer"},
    "order_type": {"type": "string", "enum": ["MARKET", "LIMIT"]},
    "timestamp": {"type": "string", "format": "date-time"}
  },
  "required": ["symbol", "direction", "price", "quantity", "order_type", "timestamp"]
}

4.2. BrokerAPI Interface (Kiwoom)

class BrokerAPI:
    def send_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends order to broker. Input == Order data model. 
        Returns execution_report: {"order_id": str, "filled_qty": int, "avg_price": float, "status": str}
        """


⸻

5. BACKTEST MODE SPECIFICS

class BacktestRunner:
    def __init__(self, data_folder: str, config: Config):
        self.data_folder = data_folder
        self.config = config
        self.data_handler = DataHandler(config.symbols, lookback_days=365)
        self.risk_manager = RiskManager(config.starting_capital, config.max_position_pct, config.daily_max_loss_pct, config.daily_target_pct)
        self.trading_bot = TradingBot(config, self.data_handler, self.risk_manager)

    def run_backtest(self) -> Dict[str, Any]:
        """Iterate historical CSV bars instead of real ticks."""
        for symbol in self.config.symbols:
            df = pd.read_csv(f"{self.data_folder}/{symbol}_1min.csv", parse_dates=["datetime"])
            for idx, row in df.iterrows():
                self.data_handler.historical_data[symbol].append(row)
                self.trading_bot.generate_signals(symbol)
                self.trading_bot.execute_order(...)  # adjust logic
        return {"final_capital": self.risk_manager.capital, "positions": self.risk_manager.positions}


⸻

6. EXTENSION & REFRACTION POINTS
	1.	New Indicator Modules: Add a class in src/indicators.py with:

class IndicatorBase:
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        pass

	•	Integrate by calling indicator.compute(df) inside DataHandler.compute_indicators.

	2.	Alternative AI Model: Replace _ai_predict with streaming gRPC client:

class AIClientGRPC:
    def predict(self, features: Any) -> float:
        """Streams features to ML model and returns prediction."""

	•	Swap in config by adding ai_type: "rest" or "grpc".

	3.	Custom Risk Rules: Subclass RiskManager:

class CustomRiskManager(RiskManager):
    def can_open_position(self, symbol: str, price: float) -> bool:
        # override with volatility-based sizing
        return super().can_open_position(symbol, price)


	4.	Dynamic Symbol List: Implement a SymbolManager to fetch tickers from external source:

class SymbolManager:
    def fetch_symbols(self) -> list[str]:
        # e.g., from CSV, API, database
        return [...]  

	•	TradingBot should call SymbolManager.fetch_symbols() on startup or periodically.

	5.	Plugin Hooks in TradingBot.run():

class TradingBot:
    def before_loop(self): pass
    def after_loop(self): pass
    def before_signal(self, symbol: str): pass
    def after_signal(self, symbol: str, signal: Dict[str, Any]): pass

	•	Allows dynamic logic injection without editing core code.

⸻

7. DEPLOYMENT & INFRASTRUCTURE

7.1. Environment Setup (Live)

# Python version
python == 3.9.0
pip install -r requirements.txt
# Kiwoom HTS must be installed with digital certificate, COM components available
export KIWOOM_CERT_PATH="/path/to/cert"
export API_KEY="abc123"

7.2. Containerization

Dockerfile:

FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
CMD ["python", "main.py"]

7.3. CI/CD (GitHub Actions)

name: CI
on: [push, pull_request]
jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install Dependencies
        run: pip install -r requirements.txt
      - name: Run Tests
        run: pytest --maxfail=1 --disable-warnings -q


⸻

8. DIAGRAM (Concise ASCII for AI Parsing)

[main.py] -> [Config] -> [TradingBot] -> [DataHandler]
                                  -> [RiskManager]
                                  -> [AIClient]
                                  -> [BrokerAPI]

	•	Arrows indicate data/control flow.
	•	Node labels correspond to class or module names.

⸻

9. SUMMARY FOR AI AGENT
	1.	Config: Validates and exposes all runtime parameters.
	2.	DataHandler: Manages tick ingestion, bar aggregation, indicator computation.
	3.	RiskManager: Tracks capital, positions, enforces risk logic.
	4.	TradingBot: Controls main loop, combines technical and AI signals, implements plugin hooks.
	5.	AI Integration: Configurable via REST or gRPC client.
	6.	Broker API: Abstracted interface, stubbed for Kiwoom.
	7.	BacktestRunner: Emulates live loop using historical CSVs.
	8.	Extension Points: Modular indicator, AI, risk, symbol manager, plugin hooks.

⸻

AI Agent Guidance: Use this specification to generate or modify code. Each module has explicit signatures and types. Backtests, live mode, and deployment workflows are fully described. Extension points are annotated for seamless integration. Ensure new code aligns with the data schemas and interface contracts provided above.
