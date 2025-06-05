import threading
import time
import logging
import requests
from datetime import datetime

import numpy as np

from src.data_handler import DataHandler
from src.risk_manager import RiskManager
from src.config import Config
from pytz import timezone

logger = logging.getLogger(__name__)

class TradingBot:
    """
    전체 자동매매 로직을 수행하는 클래스입니다.
    """

    def __init__(self, config: dict):
        # 1) 설정 객체 생성
        self.config = Config(config)

        # 2) DataHandler, RiskManager 인스턴스 생성
        self.data_handler = DataHandler(self.config)
        self.risk_manager = RiskManager(self.config)

        # 3) Kiwoom API 또는 브로커 API 래퍼 초기화 (예: PyKiwoom 인스턴스)
        # self.kiwoom = PyKiwoom(...)
        # TODO: 실제 Kiwoom API 초기화 코드 구현

        # 4) 현재 거래일(day) 기준
        self.trading_day = None

    def initialize(self):
        """
        - 과거 데이터 로드
        - API 로그인
        - 현재 거래일 설정
        """
        self.data_handler.update_historical_all()

        # Kiwoom 로그인
        # TODO: self.kiwoom.login(self.config.kiwoom_id, self.config.kiwoom_pw, self.config.kiwoom_cert)
        # logger.info("[API] Kiwoom 로그인 성공")

        # 현재 거래일 설정 (미국 정규장 TimeZone 사용)
        now_utc = datetime.utcnow()
        tz = timezone(self.config.time_zone)
        now_local = now_utc.replace(tzinfo=timezone("UTC")).astimezone(tz)
        self.trading_day = now_local.date()

        logger.info(f"[INIT] TradingBot 초기화 완료. 거래일: {self.trading_day}")

    def fetch_realtime_ticks(self):
        """
        실제 Kiwoom API의 OnReceiveRealData 콜백에서 틱 데이터를 받아
        DataHandler.update_realtime()을 호출해야 합니다.
        여기서는 데모용으로 랜덤 틱 데이터를 생성하는 스레드를 가동합니다.
        """
        def _dummy_tick_feed():
            while True:
                now = datetime.utcnow()
                for symbol in self.config.symbols:
                    price = np.random.random() * 100  # 예시 랜덤 가격
                    volume = np.random.randint(1, 10)
                    tick = {"datetime": now, "price": price, "volume": volume}
                    self.data_handler.update_realtime(symbol, tick)
                time.sleep(1)

        t = threading.Thread(target=_dummy_tick_feed, daemon=True)
        t.start()

    def generate_signals(self, symbol: str) -> dict:
        """
        최신 1분봉 기준으로 매수/매도/HOLD 신호를 생성하여 반환합니다.
        반환형 예시: {"signal": "BUY"/"SELL"/"HOLD", "price": float, "quantity": int}
        """
        df = self.data_handler.compute_indicators(symbol)
        if df.empty or len(df) < max(
                self.config.ema_long_period,
                self.config.rsi_period,
                self.config.bb_period
        ):
            return {"signal": "HOLD"}

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # 1) EMA 크로스오버
        ema_short = latest["ema_short"]
        ema_long = latest["ema_long"]
        prev_ema_short = prev["ema_short"]
        prev_ema_long = prev["ema_long"]
        ema_cross_up = (prev_ema_short < prev_ema_long) and (ema_short > ema_long)
        ema_cross_down = (prev_ema_short > prev_ema_long) and (ema_short < ema_long)

        # 2) RSI 과매수/과매도
        rsi = latest["rsi"]
        rsi_oversold = rsi < self.config.rsi_oversold
        rsi_overbought = rsi > self.config.rsi_overbought

        # 3) Bollinger Band 돌파
        price = latest["close"]
        bb_hband = latest["bb_hband"]
        bb_lband = latest["bb_lband"]
        bb_break_up = (prev["close"] <= prev["bb_hband"]) and (price > bb_hband)
        bb_break_down = (prev["close"] >= prev["bb_lband"]) and (price < bb_lband)

        # 4) VWAP 돌파
        vwap = latest["vwap"]
        prev_vwap = prev["vwap"]
        vwap_break_up = (prev["close"] <= prev_vwap) and (price > vwap)
        vwap_break_down = (prev["close"] >= prev_vwap) and (price < vwap)

        # 5) AI 예측 신호 (실제 환경에서는 REST API 호출)
        # 예시: response = requests.post(self.config.ai_endpoint, json={...}, headers={...})
        #       predicted_return = response.json().get("predicted_return", 0.0)
        predicted_return = np.random.uniform(-0.01, 0.01)
        ai_buy_signal = (predicted_return > 0.005)
        ai_sell_signal = (predicted_return < -0.005)

        # 6) 신호 가중치 합산
        buy_score = 0.0
        if ema_cross_up: buy_score += 1.0
        if rsi_oversold: buy_score += 0.5
        if bb_break_up: buy_score += 0.7
        if vwap_break_up: buy_score += 0.5
        if ai_buy_signal: buy_score += 1.0

        sell_score = 0.0
        if ema_cross_down: sell_score += 1.0
        if rsi_overbought: sell_score += 0.5
        if bb_break_down: sell_score += 0.7
        if vwap_break_down: sell_score += 0.5
        if ai_sell_signal: sell_score += 1.0

        # 7) 임계값(Threshold)
        BUY_THRESHOLD = 1.5
        SELL_THRESHOLD = 1.5

        has_position = (
            symbol in self.risk_manager.positions and
            self.risk_manager.positions[symbol].is_open
        )

        # 매수 신호
        if (buy_score >= BUY_THRESHOLD) and (not has_position) and self.risk_manager.can_open_position(symbol, price):
            max_per_position = self.risk_manager.capital * (self.config.max_position_pct)
            quantity = int(max_per_position // price)
            if quantity <= 0:
                return {"signal": "HOLD"}
            return {"signal": "BUY", "price": price, "quantity": quantity}

        # 매도(청산) 신호
        if has_position and (sell_score >= SELL_THRESHOLD):
            return {"signal": "SELL", "price": price, "quantity": 0}

        # 손절/익절 자동 체크
        if has_position:
            pos = self.risk_manager.positions[symbol]
            if pos.check_stop_loss(price):
                return {"signal": "SELL_SL", "price": price, "quantity": 0}
            if pos.check_take_profit(price):
                return {"signal": "SELL_TP", "price": price, "quantity": 0}

        return {"signal": "HOLD"}

    def execute_order(self, signal: dict, symbol: str):
        """
        generate_signals에서 반환된 시그널을 바탕으로 실제 주문을 보내거나
        RiskManager를 통해 포지션을 관리합니다.
        """
        sig_type = signal.get("signal", "HOLD")
        price = signal.get("price", 0.0)
        quantity = signal.get("quantity", 0)

        if sig_type == "BUY":
            try:
                # TODO: 실제 API 호출 예시
                # order_no = self.kiwoom.send_order("신규매수", self.config.kiwoom_account, symbol, quantity, price, ...)
                self.risk_manager.open_position(symbol, price, quantity)
            except Exception as e:
                logger.error(f"[ORDER][BUY] {symbol} 주문 실패: {e}")

        elif sig_type in ["SELL", "SELL_SL", "SELL_TP"]:
            try:
                # TODO: 실제 API 호출 예시
                # order_no = self.kiwoom.send_order("매도", self.config.kiwoom_account, symbol, pos.quantity, price, ...)
                self.risk_manager.close_position(symbol, price)
            except Exception as e:
                logger.error(f"[ORDER][SELL] {symbol} 청산 실패: {e}")

        # HOLD인 경우에는 별도 처리 없음

    def run(self):
        """
        메인 루프: 시장 개장 중이라면 주기적으로 신호를 생성하고 주문을 실행합니다.
        """
        # 1) 실시간 틱 피드 시작
        self.fetch_realtime_ticks()

        while True:
            now_utc = datetime.utcnow()
            # 시장 개장 여부 확인
            if not self.is_market_open(now_utc):
                logger.info("[MARKET] 미개장 또는 장 종료 상태. 1분 후 재확인")
                time.sleep(60)
                continue

            # 각 종목별로 신호 생성 및 주문 실행
            for symbol in self.config.symbols:
                df = self.data_handler.historical_data[symbol]
                if df.empty:
                    continue
                signal = self.generate_signals(symbol)
                if signal["signal"] != "HOLD":
                    self.execute_order(signal, symbol)

            # 일별 목표 달성 또는 손실 한도 도달 여부 확인
            if not self.risk_manager.check_daily_targets():
                logger.info("[BOT] 목표달성/손실한도 도달: 신규 진입 중지 및 루프 종료")
                break

            time.sleep(self.config.loop_interval_sec)

        # 시장 폐장 전 남은 포지션 청산
        self._final_cleanup()

    def is_market_open(self, now_utc: datetime) -> bool:
        """
        현재 UTC 시간을 기반으로 미국 정규장 개폐 여부를 판단합니다.
        (정확한 시간 계산을 위해 pytz를 사용하여 타임존 변환 필요)
        """
        # 간략화: UTC 기준 14:30~21:00 사이를 개장으로 가정
        hour = now_utc.hour
        minute = now_utc.minute
        if (hour == 14 and minute >= 30) or (14 < hour < 21) or (hour == 21 and minute == 0):
            return True
        return False

    def _final_cleanup(self):
        """
        시장 폐장 직전에 남은 포지션을 모두 청산합니다.
        """
        logger.info("[CLEANUP] 시장 폐장 전 모든 포지션 청산 중...")
        for symbol, pos in list(self.risk_manager.positions.items()):
            if pos.is_open:
                last_price = self.data_handler.historical_data[symbol]["close"].iloc[-1]
                self.risk_manager.close_position(symbol, last_price)
        logger.info("[CLEANUP] 모든 포지션이 청산되었습니다.")