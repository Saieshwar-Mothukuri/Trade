"""
Input validation for trading bot CLI parameters.
All validation raises ValueError with a human-readable message on failure.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}

# Binance symbol rules: uppercase letters only, 2–20 chars
_MIN_SYMBOL_LEN = 3
_MAX_SYMBOL_LEN = 20


def validate_symbol(symbol: str) -> str:
    """Return the normalised symbol or raise ValueError."""
    sym = symbol.strip().upper()
    if not sym.isalpha():
        raise ValueError(
            f"Symbol '{symbol}' must contain letters only (e.g. BTCUSDT)."
        )
    if not (_MIN_SYMBOL_LEN <= len(sym) <= _MAX_SYMBOL_LEN):
        raise ValueError(
            f"Symbol '{symbol}' length must be between "
            f"{_MIN_SYMBOL_LEN} and {_MAX_SYMBOL_LEN} characters."
        )
    return sym


def validate_side(side: str) -> str:
    """Return 'BUY' or 'SELL', or raise ValueError."""
    s = side.strip().upper()
    if s not in VALID_SIDES:
        raise ValueError(
            f"Side '{side}' is invalid. Choose from: {', '.join(sorted(VALID_SIDES))}."
        )
    return s


def validate_order_type(order_type: str) -> str:
    """Return a valid order type string or raise ValueError."""
    ot = order_type.strip().upper()
    if ot not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Order type '{order_type}' is invalid. "
            f"Choose from: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return ot


def validate_quantity(quantity: str | float) -> str:
    """Return quantity as a string (Binance expects string) or raise ValueError."""
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be greater than zero, got {quantity}.")
    # Return as string to preserve precision when sent to API
    return str(qty)


def validate_price(price: Optional[str | float], order_type: str) -> Optional[str]:
    """
    Validate the price field.
    - Required for LIMIT and STOP_MARKET orders.
    - Must be None / omitted for MARKET orders.
    Returns price as string or None.
    """
    ot = order_type.strip().upper()

    if ot == "MARKET":
        if price is not None:
            raise ValueError(
                "Price must not be supplied for MARKET orders. "
                "Remove --price or set it to None."
            )
        return None

    # LIMIT / STOP_MARKET require a price
    if price is None:
        raise ValueError(f"Price is required for {ot} orders (--price <value>).")

    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"Price '{price}' is not a valid number.")
    if p <= 0:
        raise ValueError(f"Price must be greater than zero, got {price}.")
    return str(p)


def validate_stop_price(
    stop_price: Optional[str | float], order_type: str
) -> Optional[str]:
    """
    Validate the stop-price field used by STOP_MARKET orders.
    Returns stop_price as string or None.
    """
    ot = order_type.strip().upper()

    if ot != "STOP_MARKET":
        return None

    if stop_price is None:
        raise ValueError("--stop-price is required for STOP_MARKET orders.")

    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValueError(f"Stop-price '{stop_price}' is not a valid number.")
    if sp <= 0:
        raise ValueError(f"Stop-price must be greater than zero, got {stop_price}.")
    return str(sp)


def validate_all(
    *,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: Optional[str | float] = None,
    stop_price: Optional[str | float] = None,
) -> dict:
    """
    Run all validators and return a clean params dict ready for the API layer.
    Raises ValueError with a descriptive message on the first validation failure.
    """
    sym = validate_symbol(symbol)
    s = validate_side(side)
    ot = validate_order_type(order_type)
    qty = validate_quantity(quantity)
    p = validate_price(price, ot)
    sp = validate_stop_price(stop_price, ot)

    params: dict = {
        "symbol": sym,
        "side": s,
        "type": ot,
        "quantity": qty,
    }
    if p is not None:
        params["price"] = p
        params["timeInForce"] = "GTC"   # default for LIMIT orders

    if sp is not None:
        params["stopPrice"] = sp

    return params
