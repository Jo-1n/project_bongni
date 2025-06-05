import pytest
import pandas as pd
from datetime import datetime
from src.config import Config
from src.data_handler import DataHandler

@pytest.fixture
def config_dict():
    return {
        "kiwoom": {"user_id": "", "user_pw": "", "cert_pw": "", "account_no": ""},
        "ai_model": {"endpoint_url": "", "api_key": ""},
        "symbols": ["TEST"],
        "time_zone": "America/New_York",
        "initial_capital": 1000.0,
        "max_position_pct": 0.5,
        "target_daily_return_pct": 2.0,
        "stop_loss_pct": 1.0,
        "take_profit_pct": 1.5,
        "daily_max_loss_pct": 3.0,
        "ema_short_period": 5,
        "ema_long_period": 10,
        "rsi_period": 14,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "bb_period": 20,
        "bb_std_dev": 2,
        "historical_lookback_days": 1,
        "historical_bar_period": "1min",
        "order_retry_interval_sec": 1.0,
        "loop_interval_sec": 5.0,
        "log_level": "DEBUG",
        "log_file": "logs/test.log"
    }

def test_fetch_historical(config_dict):
    cfg = Config(config_dict)
    dh = DataHandler(cfg)
    df = dh.fetch_historical("TEST")
    assert isinstance(df, pd.DataFrame)
    assert "close" in df.columns
    assert len(df) > 0

def test_aggregate_to_minute_bar(config_dict):
    cfg = Config(config_dict)
    dh = DataHandler(cfg)
    # 60개의 틱 데이터 모의 생성
    now = datetime.utcnow()
    for i in range(60):
        tick = {"datetime": now, "price": 100 + i, "volume": 10}
        dh.update_realtime("TEST", tick)
        now = now.replace(microsecond=now.microsecond + 1000)
    # 1분봉이 생성되었는지 확인
    assert not dh.historical_data["TEST"].empty
    # 마지막 타임스탬프가 존재해야 함
    assert dh.last_timestamp["TEST"] is not None

def test_compute_indicators_insufficient_data(config_dict):
    cfg = Config(config_dict)
    dh = DataHandler(cfg)
    # 빈 DataFrame 상태
    df_ind = dh.compute_indicators("TEST")
    assert df_ind.empty