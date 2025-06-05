# src/broker_api.py

import logging
import time
from enum import Enum
from typing import Literal

logger = logging.getLogger(__name__)


class HogaType(str, Enum):
    LIMIT = "00"   # Limit order
    MARKET = "03"  # Market order


class BrokerAPI:
    """
    Wraps Kiwoom SendOrder and related callbacks with rate limiting.
    """

    def __init__(self, kiwoom, account_no: str, screen_no: str = "0101"):
        self.kiwoom = kiwoom
        self.account_no = account_no
        self.screen_no = screen_no
        # Load rate limit from config if available, else default 0.2s
        self.rate_limit_sec = getattr(kiwoom, "rate_limit_sec", 0.2)

    def send_order(
        self,
        direction: Literal["BUY", "SELL"],
        symbol: str,
        quantity: int,
        price: float,
        order_type: HogaType = HogaType.LIMIT
    ) -> None:
        """
        Submits an order via Kiwoom.

        Args:
            direction:  "BUY" or "SELL"
            symbol:     Stock code (string)
            quantity:   Number of shares (int, > 0)
            price:      Order price (float, > 0)
            order_type: HogaType.LIMIT or HogaType.MARKET

        Enforces Kiwoom’s rate limit (configurable, default 5 orders/sec).
        """
        if quantity <= 0 or price <= 0:
            raise ValueError("Quantity and price must be positive.")

        sibal = 1 if direction.upper() == "BUY" else 2

        try:
            self.kiwoom.SendOrder(
                "OrderRequest",             # User-defined request name
                self.screen_no,             # Screen number
                self.account_no,            # Account number
                sibal,                      # 1=buy, 2=sell
                symbol,                     # Stock code
                quantity,                   # Order quantity
                price,                      # Order price
                order_type.value,           # "00" or "03"
                ""                          # Original order number (empty for new)
            )
            logger.info(
                f"[BROKER] {direction} order submitted: {symbol} qty={quantity} @ {price:.2f}"
            )
        except Exception as e:
            logger.error(f"[BROKER] SendOrder failed for {symbol}: {e}")
            raise  # Re-raise so caller can handle retries

        # Respect rate limit
        time.sleep(self.rate_limit_sec)

    def cancel_order(self, order_id: str) -> None:
        """
        Cancels an existing order by its order ID.
        (Implementation depends on Kiwoom’s cancel syntax.)

        Args:
          order_id: Kiwoom’s order identifier string.
        """
        try:
            # Example Kiwoom call (actual parameters may differ):
            self.kiwoom.SendOrder(
                "CancelRequest",
                self.screen_no,
                self.account_no,
                3,            # sibal=3 for cancel (example)
                order_id,     # original order ID
                0,            # quantity (ignored)
                0,            # price (ignored)
                "00",         # hoga type (ignored)
                order_id      # original order number
            )
            logger.info(f"[BROKER] Cancel request sent for order {order_id}")
        except Exception as e:
            logger.error(f"[BROKER] CancelOrder failed for {order_id}: {e}")
            raise

        time.sleep(self.rate_limit_sec)