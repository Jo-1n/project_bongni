import pytest
from src.config import Config
from src.risk_manager import RiskManager, Position

@pytest.fixture
def config_dict():
    return {
        "kiwoom": {"user_id": "", "user_pw": "", "cert_pw": "", "account_no": ""},
        "ai_model": {"endpoint_url": "", "api_key": ""},
        "symbols": ["AAPL"],
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
        "historical_lookback_days": 30,
        "historical_bar_period": "1min",
        "order_retry_interval_sec": 1.0,
        "loop_interval_sec": 5.0,
        "log_level": "DEBUG",
        "log_file": "logs/test.log"
    }

def test_can_open_position_and_open_close(config_dict):
    cfg = Config(config_dict)
    rm = RiskManager(cfg)

    # 1) 포지션 진입 가능: 초기 자본 1000, max_position_pct=0.5 → 최대 500$까지
    assert rm.can_open_position("AAPL", price=100.0) is True

    # 2) 포지션 진입
    rm.open_position("AAPL", price=100.0, quantity=4)  # 4주 매수 → 400$ 투자
    assert "AAPL" in rm.positions
    assert rm.positions["AAPL"].is_open is True
    assert rm.available_cash == 600.0

    # 3) 손절/익절 가격 계산 검사
    pos = rm.positions["AAPL"]
    assert pos.stop_loss_price == pytest.approx(100.0 * 0.99)
    assert pos.take_profit_price == pytest.approx(100.0 * 1.015)

    # 4) 익절 청산
    rm.close_position("AAPL", exit_price=102.0)  # 수익 2$ × 4주 = 8$
    assert pos.is_open is False
    assert rm.capital == pytest.approx(1000.0 + 8.0)
    assert rm.available_cash == pytest.approx(600.0 + 102.0 * 4)

def test_daily_targets(config_dict):
    cfg = Config(config_dict)
    rm = RiskManager(cfg)
    # 일별 목표 수익률 2%, 일별 손실 한도 3%

    # 1) 초기에는 목표 미달성 -> True 반환
    assert rm.check_daily_targets() is True

    # 2) 자본을 1,020으로 변경(2% 수익 달성)
    rm.capital = 1020.0
    assert rm.check_daily_targets() is False

    # 3) 손실 한도 도달 시(자본 970으로 변경 → 3% 손실)
    rm.capital = 970.0
    rm.daily_starting_capital = 1000.0
    assert rm.check_daily_targets() is False