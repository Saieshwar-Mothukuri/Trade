# Binance Futures Testnet – Trading Bot

A clean, production-grade Python CLI for placing orders on the Binance USDT-M Futures Testnet. Built with structured logging, layered architecture, and thorough input validation.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py         # Package exports
│   ├── client.py           # Binance REST API client (signing, retries, error handling)
│   ├── orders.py           # Order placement logic + OrderResult dataclass
│   ├── validators.py       # Input validation (raises ValueError on bad input)
│   └── logging_config.py   # File + console logging setup
├── cli.py                  # CLI entry point (argparse)
├── logs/
│   └── trading_bot.log     # Auto-created on first run
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Binance Futures Testnet Account

1. Visit [testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in with your GitHub account
3. Go to **API Key** → generate a new key pair
4. Copy the **API Key** and **Secret Key**

### 2. Clone & install dependencies

```bash
git clone <repo-url>
cd trading_bot

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Set credentials

**Recommended (environment variables):**

```bash
export BINANCE_API_KEY="your_testnet_api_key"
export BINANCE_API_SECRET="your_testnet_api_secret"
```

Or pass them directly via flags (see examples below).

---

## How to Run

### Market Order (BUY)

```bash
python cli.py \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --quantity 0.001
```

### Limit Order (SELL)

```bash
python cli.py \
  --symbol BTCUSDT \
  --side SELL \
  --type LIMIT \
  --quantity 0.001 \
  --price 100000
```

### Stop-Market Order (SELL) — Bonus order type

```bash
python cli.py \
  --symbol BTCUSDT \
  --side SELL \
  --type STOP_MARKET \
  --quantity 0.001 \
  --stop-price 90000
```

### Dry-run mode (validate without sending to API)

```bash
python cli.py \
  --symbol ETHUSDT \
  --side BUY \
  --type MARKET \
  --quantity 0.01 \
  --dry-run
```

### Pass credentials inline (alternative to env vars)

```bash
python cli.py \
  --api-key YOUR_KEY \
  --api-secret YOUR_SECRET \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --quantity 0.001
```

---

## CLI Reference

| Flag | Required | Description |
|---|---|---|
| `--symbol` | ✅ | Trading pair, e.g. `BTCUSDT`, `ETHUSDT` |
| `--side` | ✅ | `BUY` or `SELL` |
| `--type` | ✅ | `MARKET`, `LIMIT`, or `STOP_MARKET` |
| `--quantity` | ✅ | Quantity in base asset (e.g. `0.001` BTC) |
| `--price` | LIMIT only | Limit price |
| `--stop-price` | STOP_MARKET only | Stop trigger price |
| `--api-key` | if no env var | Testnet API key |
| `--api-secret` | if no env var | Testnet API secret |
| `--log-level` | ❌ | `DEBUG`/`INFO`/`WARNING`/`ERROR` (default: `INFO`) |
| `--dry-run` | ❌ | Validate and preview without placing order |

---

## Example Output

```
┌─────────────────────────────────────────────┐
│  Binance Futures Testnet – Trading Bot CLI  │
└─────────────────────────────────────────────┘

── Order Request Summary ─────────────────────────────
  symbol          : BTCUSDT
  side            : BUY
  type            : MARKET
  quantity        : 0.001
──────────────────────────────────────────────────────

╔══════════════════════════════════════╗
║          ORDER CONFIRMATION          ║
╚══════════════════════════════════════╝
  Order ID      : 4254642309
  Client OID    : web_FaVS3ByqxOSs4pSBEzim
  Symbol        : BTCUSDT
  Side          : BUY
  Type          : MARKET
  Status        : FILLED
  Orig Qty      : 0.001
  Executed Qty  : 0.001
  Avg Price     : 97341.60

  ✅  Order placed successfully on Binance Futures Testnet
```

---

## Logging

Logs are written to `logs/trading_bot.log` (auto-created).

- **File handler**: captures `DEBUG` and above — full API request/response audit trail
- **Console (stderr)**: shows `WARNING` and above only — keeps CLI output clean

Log format:
```
2025-01-15T10:23:41 | INFO     | trading_bot.orders | Order success | orderId=4254642309 | status=FILLED | executedQty=0.001
```

Sample log file (`logs/trading_bot.log`) is included showing:
- MARKET BUY order (FILLED)
- LIMIT SELL order (NEW / resting)
- STOP_MARKET SELL order (bonus)
- An API error (invalid symbol) demonstrating error handling

---

## Design Decisions & Assumptions

| Decision | Rationale |
|---|---|
| No third-party SDK (`python-binance`) | Uses only `requests` to keep dependencies minimal and show raw API understanding |
| `requests` + `HTTPAdapter` retry | Handles transient 429/5xx without crashing |
| `Decimal` for price/qty | Avoids float precision issues when serialising to the API |
| Validators return clean strings | Binance expects string values for numeric fields |
| `OrderResult` dataclass | Clean separation — CLI never touches raw dict keys |
| File log = DEBUG, console = WARNING | Full audit trail without polluting CLI output |
| `--dry-run` flag | Safe way to test validation and CLI without API calls |
| STOP_MARKET as bonus order type | Simplest stop order; no additional price field conflicts |

### Assumptions

- Testnet only; credentials are never validated against mainnet
- `timeInForce` defaults to `GTC` for LIMIT orders (most common default)
- Futures account must have testnet USDT balance (request via testnet faucet if needed)
- Symbol names must be alphabetic (no digits) per Binance's futures naming convention

---

## Running Tests (optional)

```bash
# Validate inputs without hitting the API
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --dry-run

# Trigger a validation error (no price for LIMIT)
python cli.py --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001
# → ❌  Validation error: Price is required for LIMIT orders (--price <value>).

# Trigger a validation error (price on MARKET)
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --price 50000
# → ❌  Validation error: Price must not be supplied for MARKET orders.
```

---

## Requirements

- Python 3.9+
- `requests >= 2.31.0`
- `urllib3 >= 2.0.0`
