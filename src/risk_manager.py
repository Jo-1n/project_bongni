import logging

from src.config import Config

logger = logging.getLogger(__name__)

class Position:
    """
    개별 종목 포지션 정보를 저장하고, 손절/익절 여부를 판단합니다.
    """
    def __init__(self, symbol: str, entry_price: float, quantity: int,
                 stop_loss_price: float, take_profit_price: float):
        self.symbol = symbol
        self.entry_price = entry_price
        self.quantity = quantity
        self.stop_loss_price = stop_loss_price
        self.take_profit_price = take_profit_price
        self.is_open = True

    def check_stop_loss(self, current_price: float) -> bool:
        return current_price <= self.stop_loss_price

    def check_take_profit(self, current_price: float) -> bool:
        return current_price >= self.take_profit_price


class RiskManager:
    """
    계좌 전체 자본, 가용 현금, 보유 포지션, 일별손익 등을 관리합니다.
    """
    def __init__(self, config: Config):
        self.config = config

        # 초기 자본
        self.capital = self.config.initial_capital
        self.available_cash = self.config.initial_capital
        # 종목별 포지션 사전: {symbol: Position}
        self.positions = {}
        # 일별 시작 자본(리셋 시점 기준)
        self.daily_starting_capital = self.config.initial_capital

    def can_open_position(self, symbol: str, price: float) -> bool:
        """
        새로운 포지션 진입 가능 여부 판단:
        1) 포지션당 최대 자본 비중 이하인지
        2) 일별 누적 손실 한도 미달인지
        3) 가용 현금이 충분한지
        """
        invested = sum(
            pos.entry_price * pos.quantity
            for pos in self.positions.values() if pos.is_open
        )
        max_per_position = self.capital * self.config.max_position_pct
        required_cash = price * 1  # 우선 1주 매수 기준

        if required_cash > max_per_position:
            logger.warning(
                f"[RISK] {symbol} 진입 불가: 1주 매수금액({required_cash:.2f})이 "
                f"최대 포지션 한도({max_per_position:.2f}) 초과"
            )
            return False

        current_drawdown = (self.daily_starting_capital - self.capital) / self.daily_starting_capital
        if current_drawdown >= (self.config.daily_max_loss_pct / 100.0):
            logger.warning(
                f"[RISK] 일 누적 손실 한도({self.config.daily_max_loss_pct}%) 도달: "
                "추가 진입 금지"
            )
            return False

        if required_cash > self.available_cash:
            logger.warning(
                f"[RISK] {symbol} 진입 불가: 가용 현금({self.available_cash:.2f}) 부족"
            )
            return False

        return True

    def open_position(self, symbol: str, price: float, quantity: int):
        """
        새로운 포지션을 열고 Position 객체를 생성하여 self.positions에 저장.
        청산 가격(손절가, 익절가)은 파라미터 기반으로 계산합니다.
        """
        sl_price = price * (1 - self.config.stop_loss_pct / 100.0)
        tp_price = price * (1 + self.config.take_profit_pct / 100.0)

        pos = Position(symbol, entry_price=price, quantity=quantity,
                       stop_loss_price=sl_price, take_profit_price=tp_price)
        self.positions[symbol] = pos

        invested = price * quantity
        self.available_cash -= invested
        logger.info(
            f"[RISK] {symbol} 포지션 진입: 진입가={price:.2f}, 수량={quantity}, "
            f"SL={sl_price:.2f}, TP={tp_price:.2f}"
        )

    def close_position(self, symbol: str, exit_price: float):
        """
        포지션을 청산하고 계좌 자본 및 가용 현금을 업데이트합니다.
        """
        pos = self.positions.get(symbol)
        if not pos or not pos.is_open:
            return

        profit = (exit_price - pos.entry_price) * pos.quantity
        self.capital += profit
        self.available_cash += exit_price * pos.quantity
        pos.is_open = False

        logger.info(
            f"[RISK] {symbol} 포지션 청산: 청산가={exit_price:.2f}, "
            f"수익={profit:.2f}, 잔여 자본={self.capital:.2f}"
        )

    def check_daily_targets(self) -> bool:
        """
        일별 목표 수익률 달성 및 일별 최대 손실 한도 미달 여부를 확인합니다.
        - 목표 수익 달성 시: False 반환(더 이상 진입 금지)
        - 손실 한도 도달 시: False 반환(더 이상 진입 금지)
        - 그 외: True 반환
        """
        current_return = (self.capital - self.daily_starting_capital) / self.daily_starting_capital
        if current_return >= (self.config.target_daily_return_pct / 100.0):
            logger.info(
                f"[RISK] 일별 목표 수익률({self.config.target_daily_return_pct}%) 달성: "
                "추가 진입 금지"
            )
            return False

        current_drawdown = (self.daily_starting_capital - self.capital) / self.daily_starting_capital
        if current_drawdown >= (self.config.daily_max_loss_pct / 100.0):
            logger.info(
                f"[RISK] 일 누적 손실 한도({self.config.daily_max_loss_pct}%) 도달: "
                "추가 진입 금지"
            )
            return False

        return True