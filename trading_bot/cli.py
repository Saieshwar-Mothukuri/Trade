#!/usr/bin/env python3
"""
cli.py – Command-line entry point for the Binance Futures Testnet trading bot.

Usage examples
--------------
# Market BUY
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Limit SELL
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 100000

# Stop-Market (bonus order type)
python cli.py --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 90000

Credentials are loaded from environment variables:
  BINANCE_API_KEY
  BINANCE_API_SECRET
Or passed via --api-key / --api-secret flags.
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap

from bot import (
    BinanceFuturesClient,
    OrderManager,
    setup_logging,
    validate_all,
)
from bot.logging_config import get_logger

# ── helpers ────────────────────────────────────────────────────────────────


def _banner() -> str:
    return textwrap.dedent(
        """
        ┌─────────────────────────────────────────────┐
        │  Binance Futures Testnet – Trading Bot CLI  │
        └─────────────────────────────────────────────┘
        """
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Place orders on the Binance Futures USDT-M Testnet.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Examples:
              Market buy:
                python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

              Limit sell:
                python cli.py --symbol BTCUSDT --side SELL --type LIMIT \\
                              --quantity 0.001 --price 100000

              Stop-Market sell (bonus):
                python cli.py --symbol BTCUSDT --side SELL --type STOP_MARKET \\
                              --quantity 0.001 --stop-price 90000
            """
        ),
    )

    # ── credentials ────────────────────────────────────────────────────────
    cred = parser.add_argument_group("credentials (env vars preferred)")
    cred.add_argument(
        "--api-key",
        default=os.getenv("BINANCE_API_KEY"),
        help="Binance Testnet API key  [env: BINANCE_API_KEY]",
    )
    cred.add_argument(
        "--api-secret",
        default=os.getenv("BINANCE_API_SECRET"),
        help="Binance Testnet API secret  [env: BINANCE_API_SECRET]",
    )

    # ── order parameters ───────────────────────────────────────────────────
    order = parser.add_argument_group("order parameters")
    order.add_argument(
        "--symbol", required=True, help="Trading pair, e.g. BTCUSDT"
    )
    order.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL"],
        type=str.upper,
        help="Order side: BUY or SELL",
    )
    order.add_argument(
        "--type",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET"],
        type=str.upper,
        help="Order type: MARKET | LIMIT | STOP_MARKET",
    )
    order.add_argument(
        "--quantity",
        required=True,
        help="Order quantity (base asset), e.g. 0.001",
    )
    order.add_argument(
        "--price",
        default=None,
        help="Limit price (required for LIMIT orders)",
    )
    order.add_argument(
        "--stop-price",
        default=None,
        dest="stop_price",
        help="Stop trigger price (required for STOP_MARKET orders)",
    )

    # ── misc ───────────────────────────────────────────────────────────────
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity for the log file (default: INFO)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and show request summary but do NOT send to API",
    )

    return parser


def _print_request_summary(params: dict) -> None:
    print("\n── Order Request Summary ─────────────────────────────")
    for key, value in params.items():
        print(f"  {key:<16}: {value}")
    print("──────────────────────────────────────────────────────")


# ── main ───────────────────────────────────────────────────────────────────


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    # Set up logging first
    setup_logging(args.log_level)
    logger = get_logger("cli")

    print(_banner())

    # ── credential check ───────────────────────────────────────────────────
    if not args.api_key or not args.api_secret:
        parser.error(
            "API credentials are required.\n"
            "Set BINANCE_API_KEY and BINANCE_API_SECRET env vars, "
            "or pass --api-key / --api-secret."
        )
        return 1

    # ── validation ─────────────────────────────────────────────────────────
    try:
        params = validate_all(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValueError as exc:
        print(f"\n❌  Validation error: {exc}\n", file=sys.stderr)
        logger.error("Validation failed: %s", exc)
        return 1

    _print_request_summary(params)

    if args.dry_run:
        print("\n⚠️   DRY RUN mode – request NOT sent to Binance.\n")
        logger.info("Dry-run: validated params=%s", params)
        return 0

    # ── API call ───────────────────────────────────────────────────────────
    try:
        client = BinanceFuturesClient(
            api_key=args.api_key,
            api_secret=args.api_secret,
        )
    except ValueError as exc:
        print(f"\n❌  Client init error: {exc}\n", file=sys.stderr)
        return 1

    manager = OrderManager(client)
    result = manager.place(params)

    print(result.pretty())

    if not result.success:
        logger.error("Order placement failed: %s", result.error_message)
        return 1

    logger.info(
        "CLI completed successfully | orderId=%s", result.order_id
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
