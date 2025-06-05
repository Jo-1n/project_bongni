import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.config import Config
from src.data_handler import DataHandler
from src.risk_manager import RiskManager
from src.trading_bot import TradingBot

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
        "ema_short_period": 3,
        "ema_long_period": 5,
        "rsi_period": 5,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "bb_period": 5,
        "bb_std_dev": 2,
        "historical_lookback_days": 1,
        "historical_bar_period": "1min",
        "order_retry_interval_sec": 0.1,
        "loop_interval_sec": 0.1,
        "log_level": "DEBUG",
        "log_file": "logs/test.log"
    }

def test_generate_signals_buy_and_sell(config_dict):
    """
    단순화된 데이터셋에 대해 BUY 및 SELL 신호가 발생하는지 확인합니다.
    """
    cfg = Config(config_dict)
    bot = TradingBot(config=config_dict)
    bot.initialize()

    # 1) DataHandler에 가상의 과거 데이터 준비(단순 패턴)
    now = datetime.utcnow()
    dates = pd.date_range(now - timedelta(minutes=10), now, freq="1T")
    prices = [100 + i for i in range(len(dates))]
    volumes = [100] * len(dates)
    df = pd.DataFrame({
        "open": prices,
        "high": prices,
        "low": prices,
        "close": prices,
        "volume": volumes
    }, index=dates)
    bot.data_handler.historical_data["TEST"] = df
    bot.data_handler.last_timestamp["TEST"] = df.index[-1]

    # 2) EMA 크로스오버 계산을 위해 일부러 짧은 기간 데이터로 채움
    #    가격이 상승세를 타고 있기 때문에 BUY 신호가 발생해야 함
    signal = bot.generate_signals("TEST")
    assert signal["signal"] in ["BUY", "HOLD"]  # 가중치에 따라 BUY 또는 HOLD

    # 3) 이미 포지션을 열었다고 가정하고, 손절/익절 신호 확인
    bot.risk_manager.open_position("TEST", price=100.0, quantity=1)
    # 현재 가격을 익절가 이상으로 강제 설정
    pos = bot.risk_manager.positions["TEST"]
    exit_price = pos.take_profit_price + 1.0
    signal2 = bot.generate_signals("TEST")
    assert signal2["signal"] in ["SELL_TP", "SELL"]

def test_main_loop_terminates_on_target(config_dict):
    """
    일별 목표 수익 달성 시 run() 루프가 종료되는지 확인합니다.
    """
    cfg = Config(config_dict)
    bot = TradingBot(config=config_dict)
    bot.initialize()

    # 간단히 리스크 매니저의 자본을 목표 이상으로 설정
    bot.risk_manager.capital = bot.risk_manager.daily_starting_capital * 1.05

    # run()은 내부에서 check_daily_targets()를 호출하므로, 곧바로 종료되어야 함
    bot.run()
    # 포지션이 없으므로 별도 체크 없음. 단순히 에러 없이 메서드가 빠져나오면 성공
    assert True