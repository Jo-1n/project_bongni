import os
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def load_json(path: str) -> dict:
    """
    지정된 경로의 JSON 파일을 로드하여 파이썬 딕셔너리로 반환합니다.
    """
    if not os.path.isfile(path):
        logger.error(f"[UTIL] JSON 파일을 찾을 수 없습니다: {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"[UTIL] JSON 디코딩 오류: {e}")
            return {}

def save_log(message: str, log_file: str = "logs/utility.log"):
    """
    간단한 텍스트 로그를 저장하는 헬퍼 함수입니다.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {message}\\n")

def ensure_dir(directory: str):
    """
    디렉터리가 존재하지 않으면 생성합니다.
    """
    if not os.path.isdir(directory):
        try:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"[UTIL] 디렉터리 생성: {directory}")
        except Exception as e:
            logger.error(f"[UTIL] 디렉터리 생성 실패: {e}")