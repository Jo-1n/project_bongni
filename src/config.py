class Config:
    """
    config.json 파일 및 환경 변수로부터 설정값을 로드하여
    속성(attribute) 형태로 제공하는 클래스입니다.
    """

    def __init__(self, config_dict: dict):
        # 1) Kiwoom API 설정
        self.kiwoom_id = config_dict["kiwoom"].get("user_id", os.getenv("KIWOOM_ID"))
        self.kiwoom_pw = config_dict["kiwoom"].get("user_pw", os.getenv("KIWOOM_PW"))
        self.kiwoom_cert = config_dict["kiwoom"].get("cert_pw", os.getenv("KIWOOM_CERT_PW"))
        self.kiwoom_account = config_dict["kiwoom"].get("account_no")

        # 2) AI 모델 설정
        self.ai_endpoint = config_dict["ai_model"].get("endpoint_url")
        self.ai_api_key = os.getenv("AI_API_KEY", config_dict["ai_model"].get("api_key"))

        # 3) 거래 대상 및 시간대
        self.symbols = config_dict.get("symbols", [])
        self.time_zone = config_dict.get("time_zone", "America/New_York")

        # 4) 리스크 관리
        self.initial_capital = float(config_dict.get("initial_capital", 0))
        self.max_position_pct = float(config_dict.get("max_position_pct", 0))
        self.target_daily_return_pct = float(config_dict.get("target_daily_return_pct", 0))
        self.stop_loss_pct = float(config_dict.get("stop_loss_pct", 0))
        self.take_profit_pct = float(config_dict.get("take_profit_pct", 0))
        self.daily_max_loss_pct = float(config_dict.get("daily_max_loss_pct", 0))

        # 5) 기술적 지표 파라미터
        self.ema_short_period = int(config_dict.get("ema_short_period", 5))
        self.ema_long_period = int(config_dict.get("ema_long_period", 10))
        self.rsi_period = int(config_dict.get("rsi_period", 14))
        self.rsi_oversold = int(config_dict.get("rsi_oversold", 30))
        self.rsi_overbought = int(config_dict.get("rsi_overbought", 70))
        self.bb_period = int(config_dict.get("bb_period", 20))
        self.bb_std_dev = float(config_dict.get("bb_std_dev", 2))

        # 6) 데이터 수집/백테스트
        self.historical_lookback_days = int(config_dict.get("historical_lookback_days", 30))
        self.historical_bar_period = config_dict.get("historical_bar_period", "1min")

        # 7) 주문 재시도 및 루프 인터벌
        self.order_retry_interval_sec = float(config_dict.get("order_retry_interval_sec", 1.0))
        self.loop_interval_sec = float(config_dict.get("loop_interval_sec", 5.0))

        # 8) 로깅
        self.log_level = config_dict.get("log_level", "INFO")
        self.log_file = config_dict.get("log_file", "logs/bot.log")