import json
import logging
from datetime import datetime, timedelta
import pytz

from src.config import Config, setup_logging

logger = logging.getLogger(__name__)


def load_config(path: str) -> Config:
    """
    Load and validate config.json, set up logging, and return a Config instance.

    Example:
        config = load_config("config.json")
    """
    config = Config.from_json(path)
    setup_logging(config.log_level, config.log_file)
    logger.info(f"[UTILS] Loaded configuration from {path}")
    return config


def floor_to_minute(dt: datetime) -> datetime:
    """
    Return a new datetime floored to the nearest minute (zeroing out seconds & microseconds).

    If dt has no tzinfo, it is returned unchanged aside from flooring. If dt is tz-aware,
    the returned datetime preserves the same tzinfo.
    """
    return dt.replace(second=0, microsecond=0)


def utc_to_tz(utc_dt: datetime, tz: pytz.BaseTzInfo) -> datetime:
    """
    Convert a UTC datetime (naive or tz-aware) to the target timezone.

    If utc_dt is naive, assume it is UTC.
    """
    if utc_dt.tzinfo is None:
        utc_dt = pytz.utc.localize(utc_dt)
    return utc_dt.astimezone(tz)


def parse_kiwoom_timestamp(date_str: str, time_str: str, tz: pytz.BaseTzInfo) -> datetime:
    """
    Parse Kiwoom’s date and time strings into a tz-aware datetime in the given timezone.

    Kiwoom often returns:
      - date_str: "YYYYMMDD"
      - time_str: "HHMMSS" (e.g., "093012")

    Returns a datetime localized to tz (e.g., America/New_York for US stock data).
    """
    # Combine into "YYYYMMDDHHMMSS"
    dt_naive = datetime.strptime(date_str + time_str, "%Y%m%d%H%M%S")
    return tz.localize(dt_naive)


def is_nyse_open(now_utc: datetime, tz: pytz.BaseTzInfo) -> bool:
    """
    Given a UTC datetime (naive or tz-aware), return True if NYSE is open.

    Hours: 09:30 – 16:00 America/New_York, Monday through Friday.
    """
    now_ny = utc_to_tz(now_utc, tz)
    # Weekend check: 5 = Saturday, 6 = Sunday
    if now_ny.weekday() >= 5:
        return False

    open_time = now_ny.replace(hour=9, minute=30, second=0, microsecond=0)
    close_time = now_ny.replace(hour=16, minute=0, second=0, microsecond=0)
    return open_time <= now_ny < close_time


def is_nyse_close(now_utc: datetime, tz: pytz.BaseTzInfo) -> bool:
    """
    Given a UTC datetime, return True if NYSE is closed for the day (i.e., past 16:00 NY or weekend).

    Note: If it is Saturday or Sunday in NY, this returns True immediately.
    """
    now_ny = utc_to_tz(now_utc, tz)
    if now_ny.weekday() >= 5:
        return True

    # After 16:00 on a weekday
    if now_ny.hour > 16 or (now_ny.hour == 16 and now_ny.minute >= 0):
        return True

    return False


def prune_dataframe_by_days(df, days: int, tz: pytz.BaseTzInfo) -> None:
    """
    In-place prune: keep only rows from the last `days` days in the DataFrame `df`.

    Assumes df is indexed by a tz-aware datetime in the same timezone `tz`.
    Any rows with timestamp < (now_tz - days) are dropped.
    """
    if df.empty:
        return

    now_tz = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(tz)
    cutoff = now_tz - timedelta(days=days)
    df.drop(df[df.index < cutoff].index, inplace=True)


def load_json_safely(path: str) -> dict:
    """
    Load a JSON file and return its contents as a dict.
    Raises a clear error if the file does not exist or is invalid JSON.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"[UTILS] JSON file not found: {path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"[UTILS] Invalid JSON in {path}: {e}")
        raise


# Additional convenience functions can be added here as needed,
# such as functions for CSV loading, log formatting, or generic time utilities.