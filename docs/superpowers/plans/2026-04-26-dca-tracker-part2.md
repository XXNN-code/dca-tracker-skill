# DCA Tracker 实施计划 (Part 2: Task 5-7)

继续自 Part 1。

---

### Task 5: sheets.py — Google Sheets 操作

**Files:**
- Create: `dca_tracker/sheets.py`
- Create: `credentials/` 目录

- [ ] **Step 1: 创建 credentials 目录**

Run: `New-Item -ItemType Directory -Path credentials -Force`

用户需将 Google Service Account JSON 密钥文件放入 `credentials/service_account.json`。

- [ ] **Step 2: 实现 sheets.py**

```python
"""Google Sheets CRUD 操作"""
import gspread
from google.oauth2.service_account import Credentials

from dca_tracker.config import CREDENTIALS_PATH, SHEET_NAME, WORKSHEET_NAME, SHEET_COLUMNS


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_client() -> gspread.Client:
    """获取 gspread 客户端（Service Account 认证）"""
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    return gspread.authorize(creds)


def init_sheet(share_email: str | None = None) -> str:
    """首次创建 Sheet + 表头，返回 Sheet URL。如已存在则打开。"""
    gc = get_client()
    try:
        sh = gc.open(SHEET_NAME)
    except gspread.SpreadsheetNotFound:
        sh = gc.create(SHEET_NAME)
        if share_email:
            sh.share(share_email, perm_type="user", role="writer")
        else:
            sh.share(None, perm_type="anyone", role="writer")
    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=len(SHEET_COLUMNS))
        ws.append_row(SHEET_COLUMNS)
    return sh.url


def _get_worksheet() -> gspread.Worksheet:
    """获取工作表"""
    gc = get_client()
    sh = gc.open(SHEET_NAME)
    return sh.worksheet(WORKSHEET_NAME)


def get_all_records() -> list[dict]:
    """读取所有记录"""
    ws = _get_worksheet()
    return ws.get_all_records()


def get_unique_tickers() -> list[str]:
    """获取不重复的 Ticker 列表"""
    records = get_all_records()
    seen = set()
    tickers = []
    for r in records:
        t = r.get("Ticker", "")
        if t and t not in seen:
            seen.add(t)
            tickers.append(t)
    return tickers


def get_latest_record(ticker: str) -> dict | None:
    """获取某 Ticker 最新一条记录"""
    records = get_all_records()
    matches = [r for r in records if r.get("Ticker") == ticker]
    return matches[-1] if matches else None


def append_record(record: dict):
    """追加一行新记录"""
    ws = _get_worksheet()
    row = [record.get(col, "") for col in SHEET_COLUMNS]
    ws.append_row(row, value_input_option="USER_ENTERED")
```

- [ ] **Step 3: Commit**

Run: `git add -A && git commit -m "feat: add Google Sheets module"`

---

### Task 6: main.py — Agent 入口函数

**Files:**
- Create: `dca_tracker/main.py`
- Modify: `dca_tracker/__init__.py`

- [ ] **Step 1: 实现 main.py**

```python
"""Agent 入口函数 — run_dca(), add_product(), confirm_and_save()"""
from datetime import date

from dca_tracker.config import DEFAULT_K, DEFAULT_STRATEGY, MARKET_CONFIG, SHEET_COLUMNS
from dca_tracker.sheets import (
    get_unique_tickers, get_latest_record, append_record, init_sheet,
)
from dca_tracker.market_data import get_market_data
from dca_tracker.calculator import calculate


def run_dca() -> list[dict]:
    """自动定投计算：遍历所有 Ticker，计算建议买入金额。"""
    tickers = get_unique_tickers()
    if not tickers:
        print("📭 无记录，请先使用 add_product() 添加产品。")
        return []

    results = []
    for ticker in tickers:
        try:
            latest = get_latest_record(ticker)
            if not latest:
                continue

            name = latest.get("Name", "")
            market = latest.get("Market", "")
            m = float(latest.get("M", 0))
            k = float(latest.get("k", DEFAULT_K))
            max_amt_raw = latest.get("Max Amount", "")
            max_amount = float(max_amt_raw) if max_amt_raw else None
            strategy = latest.get("Strategy", DEFAULT_STRATEGY)

            data = get_market_data(ticker, market)
            quote = data["quote"]
            ma = data["ma"]

            calc = calculate(strategy, m=m, ma=ma, quote=quote, k=k, max_amount=max_amount)
            currency = MARKET_CONFIG.get(market, {}).get("currency", "")

            result = {
                "ticker": ticker,
                "name": name,
                "market": market,
                "quote": quote,
                "ma": ma,
                "ratio": calc["ratio"],
                "suggested_amount": calc["suggested_amount"],
                "shares": calc["shares"],
                "capped": calc["capped"],
                "currency": currency,
                "m": m,
                "k": k,
                "max_amount": max_amount,
                "strategy": strategy,
            }
            results.append(result)

            cap_warn = " ⚠️ 已触顶" if calc["capped"] else ""
            print(f"\n📊 {name} ({ticker})")
            print(f"   Quote: {quote} | MA: {ma} | MA/Quote: {calc['ratio']}")
            print(f"   建议买入: {currency} {calc['suggested_amount']} ({calc['shares']}份){cap_warn}")

        except Exception as e:
            print(f"\n⚠️ {ticker} 处理失败: {e}")
            continue

    if results:
        print(f"\n{'='*50}")
        print(f"📋 共 {len(results)} 个产品待定投")
        total_by_currency = {}
        for r in results:
            c = r["currency"]
            total_by_currency[c] = total_by_currency.get(c, 0) + r["suggested_amount"]
        for c, t in total_by_currency.items():
            print(f"   {c} 合计: {t:.2f}")

    return results


def add_product(
    name: str,
    ticker: str,
    market: str,
    fees: float,
    total_amount: float,
    m: float,
    k: float = DEFAULT_K,
    max_amount: float | None = None,
    isin: str | None = None,
) -> dict:
    """添加新产品并写入 Sheet。"""
    data = get_market_data(ticker, market)
    quote = data["quote"]
    ma = data["ma"]
    shares = round(total_amount / quote, 4)
    strategy = DEFAULT_STRATEGY
    calc = calculate(strategy, m=m, ma=ma, quote=quote, k=k, max_amount=max_amount)
    mc = MARKET_CONFIG.get(market, {})

    record = {
        "Date": date.today().isoformat(),
        "Type": "Buy",
        "Name": name,
        "Ticker": ticker,
        "Market": market,
        "ISIN": isin or "",
        "Quote": quote,
        "Currency": mc.get("currency", ""),
        "Fees": fees,
        "Shares": shares,
        "Total Amount": total_amount,
        "Account": mc.get("account", ""),
        "Strategy": strategy,
        "M": m,
        "MA": ma,
        "k": k,
        "Suggested Amount": calc["suggested_amount"],
        "Max Amount": max_amount or "",
    }

    append_record(record)
    print(f"✅ 已添加: {name} ({ticker})")
    print(f"   Quote: {quote} | Shares: {shares} | Total: {total_amount}")
    return record


def confirm_and_save(
    ticker: str,
    suggested_amount: float,
    actual_amount: float | None = None,
) -> dict:
    """确认交易并保存到 Sheet。"""
    latest = get_latest_record(ticker)
    if not latest:
        raise ValueError(f"未找到 {ticker} 的记录")

    amount = actual_amount if actual_amount is not None else suggested_amount
    market = latest.get("Market", "")
    data = get_market_data(ticker, market)
    quote = data["quote"]
    ma = data["ma"]
    shares = round(amount / quote, 4)
    mc = MARKET_CONFIG.get(market, {})

    record = {
        "Date": date.today().isoformat(),
        "Type": "Buy",
        "Name": latest.get("Name", ""),
        "Ticker": ticker,
        "Market": market,
        "ISIN": latest.get("ISIN", ""),
        "Quote": quote,
        "Currency": mc.get("currency", ""),
        "Fees": latest.get("Fees", 0),
        "Shares": shares,
        "Total Amount": amount,
        "Account": mc.get("account", ""),
        "Strategy": latest.get("Strategy", DEFAULT_STRATEGY),
        "M": latest.get("M", 0),
        "MA": ma,
        "k": latest.get("k", DEFAULT_K),
        "Suggested Amount": suggested_amount,
        "Max Amount": latest.get("Max Amount", ""),
    }

    append_record(record)
    print(f"✅ 已保存: {latest.get('Name', '')} ({ticker})")
    print(f"   实际买入: {mc.get('currency', '')} {amount} ({shares}份)")
    return record
```

- [ ] **Step 2: 更新 __init__.py 导出**

```python
"""DCA Tracker - 自动定投追踪系统"""
from dca_tracker.main import run_dca, add_product, confirm_and_save

__all__ = ["run_dca", "add_product", "confirm_and_save"]
```

- [ ] **Step 3: Commit**

Run: `git add -A && git commit -m "feat: add main entry functions"`

---

### Task 7: Google API 设置指南 + 端到端测试

**Files:**
- Create: `setup_guide.md`
- Create: `README.md`

- [ ] **Step 1: 创建 setup_guide.md**

Google Cloud API 设置的详细步骤文档（见设计文档第7节）。

- [ ] **Step 2: 创建 README.md**

包含项目简介、安装步骤、使用示例。

- [ ] **Step 3: 端到端测试**

在用户配置好 `credentials/service_account.json` 后：

Run: `uv run python -c "from dca_tracker.sheets import init_sheet; print(init_sheet())"`
Expected: 输出 Google Sheet URL

Run: `uv run python -c "from dca_tracker.main import add_product; add_product('测试基金', '110011', 'China', 0, 500, 500)"`
Expected: 输出 ✅ 已添加

Run: `uv run python -c "from dca_tracker.main import run_dca; run_dca()"`
Expected: 输出定投建议

- [ ] **Step 4: Commit**

Run: `git add -A && git commit -m "docs: add setup guide and README"`
