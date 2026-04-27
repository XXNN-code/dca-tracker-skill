---
name: dca-tracker
description: Use when the user wants to calculate, track, or manage Dollar-Cost Averaging (DCA) investments for Chinese funds or Canadian stocks.
---

# DCA Tracker Skill

## Overview
This skill provides an automated Dollar-Cost Averaging (DCA) investment tracking system. It integrates with Google Sheets to store records and uses `akshare` and `yfinance` to fetch real-time market data.

## When to Use

- When the user asks to "run DCA", "check investments", or "calculate what to buy today"
- When the user wants to add a new fund or stock to their DCA strategy
- When the user wants to confirm and record an actual investment transaction
- When the user wants to **sell all / 清仓** a product (stops future DCA tracking)

## Core Formula

The DCA suggested amount is calculated as:
`Suggested Amount = M × (MA / Quote) ^ k`
(M = base amount, MA = 200-day moving average, Quote = current price, k = sensitivity factor, default 2)

## Status Field

Each record has a `Status` column (`On` / `Off`):
- **On** (default): The product is actively tracked and included in DCA calculations.
- **Off**: The product has been sold / 清仓. `run_dca()` will automatically skip it.
- When the user says "卖出", "清仓", "sell all", or "stop tracking" a ticker, use `sell_all()` to mark it as Off.

## Quick Reference

**IMPORTANT:** Always set your working directory to the skill's root (`C:\Users\Xiang\.gemini\antigravity\skills\dca-tracker`) when running these commands, and use the virtual environment (`uv run`).

### 1. Run DCA Calculation
Calculates the suggested investment amount for all **active** (Status=On) products. Skips products that were updated less than 29 days ago or have Status=Off.

```powershell
.\.venv\Scripts\Activate.ps1
uv run python -c "from dca_tracker.main import run_dca; run_dca()"
```

### 2. Add a New Product
Adds a new investment target to the Google Sheet. `fee_rate` is the percentage (e.g., 0.0007 for 0.07%). Status defaults to `On`.

```powershell
.\.venv\Scripts\Activate.ps1
uv run python -c "from dca_tracker.main import add_product; add_product('名称', '代码', 'China/Canada', category='类别', m=500, fee_rate=0.001)"
```

### 3. Confirm and Save Transaction
Saves the actual invested amount to the Google Sheet.

```powershell
.\.venv\Scripts\Activate.ps1
uv run python -c "from dca_tracker.main import confirm_and_save; confirm_and_save('代码', suggested_amount=35.5, actual_amount=40.0)"
```

### 4. Record a Sell / 部分卖出
Records a partial sell transaction (Type=Sell, Status=On). The product **continues** to participate in DCA calculations.

```powershell
.\.venv\Scripts\Activate.ps1
uv run python -c "from dca_tracker.main import record_sell; record_sell('代码', actual_amount=500.0, shares=25.0)"
```

`shares` is optional — if omitted, it will be estimated from the current quote.

### 5. Sell All / 清仓
Marks a product as fully sold (Type=Sell, Status=Off). Future DCA calculations will **skip** this product.

```powershell
.\.venv\Scripts\Activate.ps1
uv run python -c "from dca_tracker.main import sell_all; sell_all('代码', actual_amount=1000.0, shares=50.0)"
```

`actual_amount` and `shares` are optional — they are recorded for reference only.

## Setup & Credentials

The Google Service Account JSON must be located at `credentials/service_account.json` inside the skill directory.

