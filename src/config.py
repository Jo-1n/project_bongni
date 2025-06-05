import os
import json
import logging
from jsonschema import validate, ValidationError
import pytz

# =============================================================================
# 1) JSON SCHEMA DEFINITION
#    - Mirror every key you expect in config.json here.
#    - If you add a new "number" field (e.g. max_drawdown_pct), update both
#      the 'properties' section and the 'required' list below.
# =============================================================================
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "kiwoom": {
            "type": "object",
            "properties": {
                "user_id":    {"type": "string"},
                "user_pw":    {"type": "string"},
                "cert_pw":    {"type": "string"},
                "account_no": {"type": "string"}
            },
            "required": ["user_id", "user_pw", "cert_pw", "account_no"]
        },
        "ai_model": {
            "type": "object",
            "properties": {
                "endpoint_url": {"type": "string", "format": "uri"},
                "api_key":      {"type": "string"}
            },
            "required": ["endpoint_url"]
        },
        "symbols":             {"type": "array",   "items": {"type": "string"}},
        "time_zone":           {"type": "string"},
        "initial_capital":        {"type": "number"},
        "max_position_pct":       {"type": "number"},
        "target_daily_return_pct":{"type": "number"},
        "stop_loss_pct":          {"type": "number"},
        "take_profit_pct":        {"type": "number"},
        "daily_max_loss_pct":     {"type": "number"},
        "ema_short_period":       {"type": "integer"},
        "ema_long_period":        {"type": "integer"},
        "rsi_period":             {"type": "integer"},
        "rsi_oversold":           {"type": "integer"},
        "rsi_overbought":         {"type": "integer"},
        "bb_period":              {"type": "integer"},
        "bb_std_dev":             {"type": "number"},
        "historical_lookback_days":{"type": "integer"},
        "historical_bar_period":   {"type": "string"},
        "order_retry_interval_sec":{"type": "number"},
        "loop_interval_sec":       {"type": "number"},
        "log_level": {
            "type": "string",
            "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        },
        "log_file": {"type": "string"}
    },
    "required": [
        "kiwoom",
        "ai_model",
        "symbols",
        "time_zone",
        "initial_capital",
        "max_position_pct",
        "target_daily_return_pct",
        "stop_loss_pct",
        "take_profit_pct",
        "daily_max_loss_pct",
        "ema_short_period",
        "ema_long_period",
        "rsi_period",
        "rsi_oversold",
        "rsi_overbought",
        "bb_period",
        "bb_std_dev",
        "historical_lookback_days",
        "historical_bar_period",
        "order_retry_interval_sec",
        "loop_interval_sec",
        "log_level",
        "log_file"
    ]
}


# =============================================================================
# 2) Logging Helper
#    - Call this once, after instantiating Config, to configure file + console.
# =============================================================================
def setup_logging(log_level: str, log_file: str):
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=fmt,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )


# =============================================================================
# 3) Config Class
#    - Use Config.from_json("/path/to/config.json") to load & validate.
#    - Environment‐variable overrides are checked first for Kiwoom & AI keys.
#    - Automatically casts types for numeric fields (int, float).
#    - Provides BOTH market_time_zone and local_time_zone attributes.
# =============================================================================
class Config:
    """
    Loads and validates config.json (or environment overrides).
    Exposes every setting as a typed attribute.
    """

    @staticmethod
    def from_json(path: str) -> "Config":
        """
        Factory: load JSON from 'path', validate against schema,
        and return a Config(...) instance. Raises ValueError on failure.
        """
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            try:
                raw = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in {path}: {e}")

        # 1) Validate structure & types
        try:
            validate(instance=raw, schema=CONFIG_SCHEMA)
        except ValidationError as err:
            # err.message tells you exactly which field is wrong/missing
            raise ValueError(f"config.json validation error: {err.message}")

        # 2) Build a Config object
        return Config(raw)

    def __init__(self, cfg: dict):
        # ──────────────────────────────────────────────
        # 1) Kiwoom API (override via environment if set)
        # ──────────────────────────────────────────────
        self.kiwoom_id      = os.getenv("KIWOOM_ID", cfg["kiwoom"]["user_id"])
        self.kiwoom_pw      = os.getenv("KIWOOM_PW", cfg["kiwoom"]["user_pw"])
        self.kiwoom_cert    = os.getenv("KIWOOM_CERT_PW", cfg["kiwoom"]["cert_pw"])
        self.kiwoom_account = os.getenv("KIWOOM_ACCOUNT_NO", cfg["kiwoom"]["account_no"])

        # ──────────────────────────────────────────────
        # 2) AI Model (optional override via env)
        # ──────────────────────────────────────────────
        self.ai_endpoint = cfg["ai_model"]["endpoint_url"]
        self.ai_api_key  = os.getenv("AI_API_KEY", cfg["ai_model"].get("api_key"))

        # ──────────────────────────────────────────────
        # 3) Symbols & Time Zones
        # ──────────────────────────────────────────────
        self.symbols = cfg["symbols"]  # list[str]

        # Market time zone (e.g. "US/Eastern")
        tz_str = cfg["time_zone"]
        try:
            self.market_tz = pytz.timezone(tz_str)
        except pytz.UnknownTimeZoneError:
            raise ValueError(f"Invalid time_zone in config.json: '{tz_str}'")

        # Local machine time zone (hardcoded Asia/Seoul)
        self.local_tz = pytz.timezone("Asia/Seoul")

        # ──────────────────────────────────────────────
        # 4) Risk Management & Capital
        # ──────────────────────────────────────────────
        # Cast numbers explicitly for clarity
        self.initial_capital         = float(cfg["initial_capital"])
        self.max_position_pct        = float(cfg["max_position_pct"])
        self.target_daily_return_pct = float(cfg["target_daily_return_pct"])
        self.stop_loss_pct           = float(cfg["stop_loss_pct"])
        self.take_profit_pct         = float(cfg["take_profit_pct"])
        self.daily_max_loss_pct      = float(cfg["daily_max_loss_pct"])

        # ──────────────────────────────────────────────
        # 5) Technical Indicators
        # ──────────────────────────────────────────────
        self.ema_short_period  = int(cfg["ema_short_period"])
        self.ema_long_period   = int(cfg["ema_long_period"])
        self.rsi_period        = int(cfg["rsi_period"])
        self.rsi_oversold      = int(cfg["rsi_oversold"])
        self.rsi_overbought    = int(cfg["rsi_overbought"])
        self.bb_period         = int(cfg["bb_period"])
        self.bb_std_dev        = float(cfg["bb_std_dev"])

        # ──────────────────────────────────────────────
        # 6) Historical Data / Backtest Settings
        # ──────────────────────────────────────────────
        self.historical_lookback_days = int(cfg["historical_lookback_days"])
        self.historical_bar_period    = cfg["historical_bar_period"]  # e.g. "1d", "5m", etc.

        # ──────────────────────────────────────────────
        # 7) Order Retry & Loop Intervals
        # ──────────────────────────────────────────────
        self.order_retry_interval_sec = float(cfg["order_retry_interval_sec"])
        self.loop_interval_sec        = float(cfg["loop_interval_sec"])

        # ──────────────────────────────────────────────
        # 8) Logging Configuration
        # ──────────────────────────────────────────────
        self.log_level = cfg["log_level"]
        self.log_file  = cfg["log_file"]

        # Sanity check: ensure initial capital is positive
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be > 0")

    def enable_logging(self):
        """
        Configure Python's root logger using log_level and log_file.
        Call this once early in your main application.
        """
        setup_logging(self.log_level, self.log_file)


# =============================================================================
# 4) Example: Run as a Script
#    $ python src/config.py /path/to/config.json
# =============================================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} /path/to/config.json")
        sys.exit(1)

    cfg_path = sys.argv[1]
    try:
        cfg = Config.from_json(cfg_path)
        # Immediately enable logging if desired:
        cfg.enable_logging()
        logging.info("Configuration loaded successfully.")
        logging.info(f"Symbols: {cfg.symbols}")
        logging.info(f"Market TZ: {cfg.market_tz}")
        logging.info(f"Local TZ: {cfg.local_tz}")
        logging.info(f"Initial Capital: {cfg.initial_capital}")
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}")
        sys.exit(2)