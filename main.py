import json
import logging
import os
from datetime import datetime

from src.trading_bot import TradingBot

# =============================================================================
# 1. 환경 변수 로드 (선택 사항: .env 파일에서 로드)
# =============================================================================
from dotenv import load_dotenv
load_dotenv()  # .env 파일에 설정된 값들을 환경 변수로 등록

# =============================================================================
# 2. 설정 파일(config.json) 로드
# =============================================================================
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

# =============================================================================
# 3. 로깅 설정
# =============================================================================
log_level = getattr(logging, config.get("log_level", "INFO"))
log_file = config.get("log_file", "logs/bot.log")

logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# 4. 메인 실행
# =============================================================================
def main():
    start_time = datetime.now()
    logger.info(f"[MAIN] Trading Bot 시작: {start_time}")

    # TradingBot 객체 생성 및 초기화
    bot = TradingBot(config=config)
    bot.initialize()

    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("[MAIN] 사용자에 의해 강제 종료됨. 포지션 청산 및 종료 처리 중...")
        bot._final_cleanup()
    except Exception as e:
        logger.exception(f"[MAIN] 예기치 못한 오류 발생: {e}")
        bot._final_cleanup()

    end_time = datetime.now()
    logger.info(f"[MAIN] Trading Bot 종료: {end_time}, 총 실행시간: {end_time - start_time}")


if __name__ == "__main__":
    main()