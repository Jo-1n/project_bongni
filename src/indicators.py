import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange


def compute_ema(df: pd.DataFrame, span: int) -> pd.Series:
    """
    Compute the Exponential Moving Average (EMA) of the 'close' column.

    Args:
        df: DataFrame with a 'close' column.
        span: Lookback period for EMA (integer).

    Returns:
        A pandas Series of EMA values (aligned to df.index).
    """
    if df.empty or "close" not in df:
        return pd.Series(dtype=float, index=df.index)
    return EMAIndicator(close=df["close"], window=span).ema_indicator()


def compute_rsi(df: pd.DataFrame, period: int) -> pd.Series:
    """
    Compute the Relative Strength Index (RSI) of the 'close' column.

    Args:
        df: DataFrame with a 'close' column.
        period: Lookback period for RSI (integer).

    Returns:
        A pandas Series of RSI values (aligned to df.index).
    """
    if df.empty or "close" not in df:
        return pd.Series(dtype=float, index=df.index)
    return RSIIndicator(close=df["close"], window=period).rsi()


def compute_bb(df: pd.DataFrame, period: int, dev: float) -> (pd.Series, pd.Series, pd.Series):
    """
    Compute Bollinger Bands (upper, lower, and middle) on the 'close' column.

    Args:
        df: DataFrame with a 'close' column.
        period: Lookback period for the moving average (integer).
        dev: Number of standard deviations for the bands (float).

    Returns:
        Tuple of three pandas Series: (bb_hband, bb_lband, bb_mavg), all aligned to df.index.
    """
    if df.empty or "close" not in df:
        empty = pd.Series(dtype=float, index=df.index)
        return empty, empty, empty

    bb = BollingerBands(close=df["close"], window=period, window_dev=dev)
    hband = bb.bollinger_hband()
    lband = bb.bollinger_lband()
    mavg = bb.bollinger_mavg()
    return hband, lband, mavg


def compute_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Compute the Volume-Weighted Average Price (VWAP) cumulatively over the DataFrame.

    Args:
        df: DataFrame with 'close' and 'volume' columns.

    Returns:
        A pandas Series of VWAP values (aligned to df.index).
    """
    if df.empty or any(col not in df for col in ("close", "volume")):
        return pd.Series(dtype=float, index=df.index)
    cumulative_pv = (df["close"] * df["volume"]).cumsum()
    cumulative_vol = df["volume"].cumsum()
    return cumulative_pv / cumulative_vol


def compute_atr(df: pd.DataFrame, period: int) -> pd.Series:
    """
    Compute the Average True Range (ATR) over the specified period.

    Args:
        df: DataFrame with 'high', 'low', and 'close' columns.
        period: Lookback period for ATR (integer).

    Returns:
        A pandas Series of ATR values (aligned to df.index).
    """
    if df.empty or any(col not in df for col in ("high", "low", "close")):
        return pd.Series(dtype=float, index=df.index)
    atr = AverageTrueRange(high=df["high"], low=df["low"], close=df["close"], window=period)
    return atr.average_true_range()