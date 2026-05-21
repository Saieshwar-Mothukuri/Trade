"""
Order placement logic — sits between the CLI layer and the raw API client.

Responsibilities:
- Accept already-validated params
- Delegate to BinanceFuturesClient
- Format and return a clean OrderResult
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .client import BinanceFuturesClient
from .logging_config import get_logger

logger = get_logger("orders")


@dataclass
class OrderResult:
    """Structured representation of a Binance order response."""

    success: bool
    order_id: Optional[int] = None
    client_order_id: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    order_type: Optional[str] = None
    status: Optional[str] = None
    orig_qty: Optional[str] = None
    executed_qty: Optional[str] = None
    avg_price: Optional[str] = None
    price: Optional[str] = None
    time_in_force: Optional[str] = None
    error_message: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "OrderResult":
        """Parse a raw Binance order response into an OrderResult."""
        avg = data.get("avgPrice") or data.get("price", "0")
        return cls(
            success=True,
            order_id=data.get("orderId"),
            client_order_id=data.get("clientOrderId"),
            symbol=data.get("symbol"),
            side=data.get("side"),
            order_type=data.get("type"),
            status=data.get("status"),
            orig_qty=data.get("origQty"),
            executed_qty=data.get("executedQty"),
            avg_price=avg,
            price=data.get("price"),
            time_in_force=data.get("timeInForce"),
            raw=data,
        )

    @classmethod
    def from_error(cls, message: str) -> "OrderResult":
        return cls(success=False, error_message=message)

    def pretty(self) -> str:
        """Return a human-readable summary of the order result."""
        if not self.success:
            return f"❌  Order FAILED: {self.error_message}"

        lines = [
            "",
            "╔══════════════════════════════════════╗",
            "║          ORDER CONFIRMATION          ║",
            "╚══════════════════════════════════════╝",
            f"  Order ID      : {self.order_id}",
            f"  Client OID    : {self.client_order_id}",
            f"  Symbol        : {self.symbol}",
            f"  Side          : {self.side}",
            f"  Type          : {self.order_type}",
            f"  Status        : {self.status}",
            f"  Orig Qty      : {self.orig_qty}",
            f"  Executed Qty  : {self.executed_qty}",
        ]
        if self.avg_price and float(self.avg_price) > 0:
            lines.append(f"  Avg Price     : {self.avg_price}")
        if self.price and float(self.price) > 0:
            lines.append(f"  Limit Price   : {self.price}")
        if self.time_in_force:
            lines.append(f"  Time-in-Force : {self.time_in_force}")
        lines.append("")
        lines.append("  ✅  Order placed successfully on Binance Futures Testnet")
        lines.append("")
        return "\n".join(lines)


class OrderManager:
    """
    Orchestrates order placement using a BinanceFuturesClient instance.

    Decouples the CLI from direct API client usage so either layer
    can be replaced or unit-tested independently.
    """

    def __init__(self, client: BinanceFuturesClient) -> None:
        self._client = client

    def place(self, validated_params: Dict[str, Any]) -> OrderResult:
        """
        Place an order and return an OrderResult.

        Parameters
        ----------
        validated_params: Output of validators.validate_all()

        Returns
        -------
        OrderResult (success or failure, never raises)
        """
        symbol = validated_params.get("symbol", "?")
        side = validated_params.get("side", "?")
        otype = validated_params.get("type", "?")

        logger.info(
            "Submitting %s %s order for %s", otype, side, symbol
        )

        try:
            data = self._client.place_order(validated_params)
            result = OrderResult.from_api_response(data)
            logger.info(
                "Order success | orderId=%s | status=%s | executedQty=%s",
                result.order_id,
                result.status,
                result.executed_qty,
            )
            return result

        except (RuntimeError, ConnectionError, TimeoutError) as exc:
            msg = str(exc)
            logger.error("Order failed | %s", msg)
            return OrderResult.from_error(msg)

        except Exception as exc:          # noqa: BLE001 – unexpected errors
            msg = f"Unexpected error: {exc}"
            logger.exception("Unexpected error placing order")
            return OrderResult.from_error(msg)
