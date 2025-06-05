import logging
import time
import requests
from typing import Dict, Any, Optional

from src.config import Config

logger = logging.getLogger(__name__)

class AIClient:
    """
    Wraps calls to an external AI‐prediction REST endpoint.

    Usage:
      1) Instantiate with config (reads ai_endpoint and api_key).
      2) Call .predict(symbol, features) → returns a float predicted_return.
      3) Retries HTTP errors up to max_attempts with exponential backoff.
    """

    def __init__(self, config: Config):
        self.config = config
        self.endpoint = config.ai_endpoint
        self.api_key = config.ai_api_key
        self.max_attempts = int(config.__dict__.get("ai_max_retries", 3))
        self.timeout = float(config.__dict__.get("ai_request_timeout", 5.0))

    def predict(self, symbol: str, features: Dict[str, Any]) -> float:
        """
        Sends a JSON payload to the AI endpoint and returns a predicted_return (float).
        If any error occurs or no valid response, returns 0.0.

        Args:
          symbol:   Stock ticker (string)
          features: Dict where keys are feature names and values are lists of values
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "symbol": symbol,
            "features": features
        }

        attempt = 0
        backoff = 1.0
        while attempt < self.max_attempts:
            try:
                response = requests.post(
                    self.endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                if response.status_code == 200:
                    data = response.json()
                    return float(data.get("predicted_return", 0.0))
                elif response.status_code in (429, 500, 502, 503, 504):
                    # Retryable error
                    logger.warning(
                        f"[AI_CLIENT] HTTP {response.status_code} for {symbol}. Retrying in {backoff:.1f}s..."
                    )
                    time.sleep(backoff)
                    backoff *= 2
                    attempt += 1
                    continue
                else:
                    # Non-retryable error
                    logger.error(f"[AI_CLIENT] Error {response.status_code} for {symbol}: {response.text}")
                    break
            except requests.RequestException as e:
                logger.warning(f"[AI_CLIENT] Request failed for {symbol}: {e}. Retrying in {backoff:.1f}s...")
                time.sleep(backoff)
                backoff *= 2
                attempt += 1

        # Fallback if all attempts fail
        logger.warning(f"[AI_CLIENT] All retries failed for {symbol}. Returning 0.0")
        return 0.0