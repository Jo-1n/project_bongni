import logging
from typing import Dict, List, Optional
from datetime import datetime

import pandas as pd

from src.config import Config

logger = logging.getLogger(__name__)


class Position:
    """
    Stores information about an individual position and checks for stop-loss / take-profit.
    """

    def __init__(
        self,
        symbol: str,
        entry_price: float,
        quantity: int,
        stop_loss_price: float,
        take_profit_price: float,
        entry_time: datetime,
    ):
        self.symbol = symbol
        self.entry_price = entry_price
        self.quantity = quantity
        self.stop_loss_price = stop_loss_price
        self.take_profit_price = take_profit_price
        self.entry_time = entry_time
        self.is_open = True

    def check_stop_loss(self, current_price: float) -> bool:
        return current_price <= self.stop_loss_price

    def check_take_profit(self, current_price: float) -> bool:
        return current_price >= self.take_profit_price


class RiskManager:
    """
    Manages account equity, available cash, open positions, and daily P&L.

    Key features:
      - Volatility‐adjusted position sizing (ATR‐based, fallback to percent‐based).
      - Dynamic stop-loss / take-profit (ATR‐based multipliers, fallback to config percentages).
      - Tracks trade_history for each closed trade.
      - Computes equity curve & drawdown from trade_history.
      - Enforces daily target return and daily max drawdown.
    """

    def __init__(self, config: Config):
        self.config = config

        # 1) Initial capital and available cash
        self.capital = self.config.initial_capital
        self.available_cash = self.config.initial_capital

        # 2) Currently open positions: {symbol: Position}
        self.positions: Dict[str, Position] = {}

        # 3) List of closed trade records (for equity curve)
        self.trade_history: List[dict] = []

        # 4) Daily starting capital (reset at start of each trading day)
        self.daily_starting_capital = self.config.initial_capital

    def _get_latest_atr(self, symbol: str) -> Optional[float]:
        """
        Retrieves the most recent ATR from DataHandler.historical_data[symbol]['atr'].
        Returns None if ATR is unavailable or the DataFrame is empty.
        """
        dh = getattr(self.config, "_data_handler_ref", None)
        if dh is None:
            return None

        df = dh.historical_data.get(symbol)
        if df is None or df.empty or "atr" not in df.columns:
            return None

        return df["atr"].iloc[-1]

    def calculate_position_size(self, symbol: str, price: float) -> Optional[tuple]:
        """
        Determines position size (quantity, stop-loss, take-profit) using ATR or percent-based sizing.

        ATR-based sizing (if ATR is available):
          - dollar_risk_per_share = ATR × atr_stop_multiplier
          - max_risk_per_trade = capital × max_position_pct
          - qty = floor(max_risk_per_trade / dollar_risk_per_share)
          - SL = price − ATR × atr_stop_multiplier
          - TP = price + ATR × atr_take_multiplier

        If ATR is not available, fallback to percent-based sizing:
          - max_value = capital × max_position_pct
          - qty = floor(max_value / price)
          - SL = price × (1 − stop_loss_pct/100)
          - TP = price × (1 + take_profit_pct/100)

        Returns (qty, sl_price, tp_price) or None if:
          - Required cash > available_cash, or
          - qty < 1.
        """
        atr = self._get_latest_atr(symbol)
        if atr is not None and atr > 0:
            atr_stop_mult = getattr(self.config, "atr_stop_multiplier", 1.0)
            atr_take_mult = getattr(self.config, "atr_take_multiplier", 2.0)

            dollar_risk_per_share = atr * atr_stop_mult
            max_risk_per_trade = self.capital * self.config.max_position_pct

            if dollar_risk_per_share <= 0:
                logger.warning(f"[RISK] Invalid ATR ({atr}) for {symbol}.")
                return None

            qty = int(max_risk_per_trade // dollar_risk_per_share)
            if qty < 1:
                logger.warning(
                    f"[RISK] {symbol}: ATR-based quantity < 1 (ATR={atr:.2f})."
                )
                return None

            required_cash = price * qty
            if required_cash > self.available_cash:
                logger.warning(
                    f"[RISK] {symbol}: Required cash ({required_cash:.2f}) > available cash ({self.available_cash:.2f})."
                )
                return None

            sl_price = price - atr * atr_stop_mult
            tp_price = price + atr * atr_take_mult
            return qty, sl_price, tp_price

        # Fallback to percent-based sizing
        max_value = self.capital * self.config.max_position_pct
        qty = int(max_value // price)
        if qty < 1:
            logger.warning(f"[RISK] {symbol}: Percent-based quantity < 1.")
            return None

        required_cash = price * qty
        if required_cash > self.available_cash:
            logger.warning(
                f"[RISK] {symbol}: Required cash ({required_cash:.2f}) > available cash ({self.available_cash:.2f})."
            )
            return None

        sl_price = price * (1.0 - self.config.stop_loss_pct / 100.0)
        tp_price = price * (1.0 + self.config.take_profit_pct / 100.0)
        return qty, sl_price, tp_price

    def can_open_position(self, symbol: str, price: float) -> bool:
        """
        Determines if a new position can be opened:
          1) calculate_position_size() returns valid sizing.
          2) Position value ≤ capital × max_position_pct.
          3) Current drawdown < daily_max_loss_pct.
        """
        size_info = self.calculate_position_size(symbol, price)
        if size_info is None:
            return False

        qty, sl_price, tp_price = size_info
        position_value = price * qty
        max_value = self.capital * self.config.max_position_pct
        if position_value > max_value:
            logger.warning(
                f"[RISK] {symbol}: Position value {position_value:.2f} > max {max_value:.2f}."
            )
            return False

        current_drawdown = self.get_current_drawdown()
        if current_drawdown >= (self.config.daily_max_loss_pct / 100.0):
            logger.warning(
                f"[RISK] {symbol}: Current drawdown {current_drawdown*100:.2f}% ≥ daily max {self.config.daily_max_loss_pct}%."
            )
            return False

        return True

    def open_position(self, symbol: str, price: float):
        """
        Opens a new position for 'symbol' at 'price':
          - Calls calculate_position_size to get (qty, sl_price, tp_price).
          - Deducts cash and stores a Position object.
        """
        size_info = self.calculate_position_size(symbol, price)
        if size_info is None:
            return

        qty, sl_price, tp_price = size_info
        entry_time = datetime.utcnow()

        pos = Position(
            symbol=symbol,
            entry_price=price,
            quantity=qty,
            stop_loss_price=sl_price,
            take_profit_price=tp_price,
            entry_time=entry_time,
        )
        self.positions[symbol] = pos

        invested = price * qty
        self.available_cash -= invested

        logger.info(
            f"[RISK] Opened {symbol}: qty={qty}, entry={price:.2f}, SL={sl_price:.2f}, "
            f"TP={tp_price:.2f}, cash_left={self.available_cash:.2f}"
        )

    def close_position(self, symbol: str, exit_price: float):
        """
        Closes an existing position for 'symbol' at 'exit_price':
          - Calculates profit = (exit_price − entry_price) × quantity.
          - Updates capital & available_cash.
          - Records the trade in trade_history.
        """
        pos = self.positions.get(symbol)
        if not pos or not pos.is_open:
            return

        exit_time = datetime.utcnow()
        profit = (exit_price - pos.entry_price) * pos.quantity

        # Update account equity
        self.capital += profit
        self.available_cash += exit_price * pos.quantity
        pos.is_open = False

        # Record trade
        equity_after = self.capital
        trade_record = {
            "symbol":       symbol,
            "entry_time":   pos.entry_time,
            "exit_time":    exit_time,
            "entry_price":  pos.entry_price,
            "exit_price":   exit_price,
            "quantity":     pos.quantity,
            "pnl":          profit,
            "equity_after": equity_after,
        }
        self.trade_history.append(trade_record)

        logger.info(
            f"[RISK] Closed {symbol}: exit={exit_price:.2f}, qty={pos.quantity}, "
            f"PnL={profit:.2f}, equity={self.capital:.2f}"
        )

    def get_equity_curve(self) -> pd.DataFrame:
        """
        Returns a DataFrame of equity over time based on trade_history.
        Columns: ['timestamp','equity'].
        - First row: daily_starting_capital at the entry_time of the first trade (if any).
        """
        if not self.trade_history:
            return pd.DataFrame(
                [{"timestamp": datetime.utcnow(), "equity": self.daily_starting_capital}]
            )

        records = []
        first_entry = self.trade_history[0]["entry_time"]
        records.append({"timestamp": first_entry, "equity": self.daily_starting_capital})

        for trade in self.trade_history:
            records.append({
                "timestamp": trade["exit_time"],
                "equity":    trade["equity_after"],
            })

        df_eq = pd.DataFrame(records)
        df_eq = df_eq.sort_values("timestamp").reset_index(drop=True)
        return df_eq

    def get_current_drawdown(self) -> float:
        """
        Computes the current peak-to-trough drawdown from the equity curve.
        Returns a decimal (e.g., 0.05 for 5% drawdown).
        """
        df_eq = self.get_equity_curve()
        if df_eq.empty:
            return 0.0

        equities = df_eq["equity"].values
        peaks = pd.Series(equities).cummax().values
        drawdowns = (peaks - equities) / peaks
        return float(drawdowns.max())

    def check_daily_targets(self) -> bool:
        """
        Checks daily target return and daily max drawdown:
          - If current return ≥ target_daily_return_pct/100 → return False (stop trading)
          - If current drawdown ≥ daily_max_loss_pct/100 → return False (stop trading)
          - Otherwise, return True (continue trading)
        """
        current_equity = self.capital
        current_return = (current_equity - self.daily_starting_capital) / self.daily_starting_capital

        if current_return >= (self.config.target_daily_return_pct / 100.0):
            logger.info(
                f"[RISK] Daily target reached: {current_return*100:.2f}% ≥ {self.config.target_daily_return_pct}%."
            )
            return False

        current_dd = self.get_current_drawdown()
        if current_dd >= (self.config.daily_max_loss_pct / 100.0):
            logger.info(
                f"[RISK] Daily drawdown reached: {current_dd*100:.2f}% ≥ {self.config.daily_max_loss_pct}%."
            )
            return False

        return True