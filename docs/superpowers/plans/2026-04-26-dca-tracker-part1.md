# DCA Tracker 实施计划 (Part 1: Task 1-4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建 AI Agent 驱动的自动定投追踪系统

**Architecture:** Python 模块化设计，5个模块（config/sheets/market_data/calculator/main），Google Sheets 存储，akshare+yfinance 获取行情

**Tech Stack:** Python 3.11+, gspread, google-auth, akshare, yfinance

**Spec:** `docs/superpowers/specs/2026-04-26-dca-tracker-design.md`

---

### Task 1: 项目初始化

**Files:**
- Create: `pyproject.toml`
- Create: `dca_tracker/__init__.py`
- Create: `.gitignore`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[project]
name = "dca-tracker"
version = "0.1.0"
description = "AI Agent driven DCA investment tracker"
requires-python = ">=3.11"
dependencies = [
    "gspread>=6.0.0",
    "google-auth>=2.0.0",
    "akshare>=1.10.0",
    "yfinance>=0.2.0",
]
```

- [ ] **Step 2: 创建 __init__.py**

```python
"""DCA Tracker - 自动定投追踪系统"""
```

- [ ] **Step 3: 创建 .gitignore**

```
credentials/
__pycache__/
*.pyc
.venv/
```

- [ ] **Step 4: 创建虚拟环境并安装依赖**

Run: `uv venv && .\.venv\Scripts\Activate.ps1 && uv pip install -e .`

- [ ] **Step 5: Commit**

Run: `git init && git add -A && git commit -m "chore: init project with dependencies"`

---

### Task 2: config.py — 常量配置

**Files:**
- Create: `dca_tracker/config.py`

- [ ] **Step 1: 创建 config.py**

```python
"""DCA Tracker 配置常量"""

DEFAULT_K = 2
DEFAULT_STRATEGY = "DCA"

MARKET_CONFIG = {
    "China": {"currency": "CNY", "account": "支付宝"},
    "Canada": {"currency": "CAD", "account": "iTRADE"},
}

SHEET_NAME = "DCA_Tracker"
WORKSHEET_NAME = "Records"

SHEET_COLUMNS = [
    "Date", "Type", "Name", "Ticker", "Market", "ISIN",
    "Quote", "Currency", "Fees", "Shares", "Total Amount",
    "Account", "Strategy", "M", "MA", "k",
    "Suggested Amount", "Max Amount",
]

CREDENTIALS_PATH = "credentials/service_account.json"
```

- [ ] **Step 2: 验证导入**

Run: `uv run python -c "from dca_tracker.config import SHEET_COLUMNS; print(len(SHEET_COLUMNS))"`
Expected: `18`

- [ ] **Step 3: Commit**

Run: `git add -A && git commit -m "feat: add config module"`

---

### Task 3: calculator.py — 策略计算引擎

**Files:**
- Create: `dca_tracker/calculator.py`
- Create: `tests/test_calculator.py`

- [ ] **Step 1: 创建测试文件**

```python
"""calculator 模块测试"""
from dca_tracker.calculator import calculate, calculate_dca


def test_dca_basic():
    """MA == Quote 时，suggested == M"""
    result = calculate("DCA", m=500, ma=10.0, quote=10.0, k=2)
    assert result["suggested_amount"] == 500.0
    assert result["capped"] is False


def test_dca_undervalued():
    """MA > Quote 时，suggested > M"""
    result = calculate("DCA", m=500, ma=12.0, quote=10.0, k=2)
    expected = 500 * (12.0 / 10.0) ** 2  # 720
    assert abs(result["suggested_amount"] - expected) < 0.01


def test_dca_overvalued():
    """MA < Quote 时，suggested < M"""
    result = calculate("DCA", m=500, ma=8.0, quote=10.0, k=2)
    expected = 500 * (8.0 / 10.0) ** 2  # 320
    assert abs(result["suggested_amount"] - expected) < 0.01


def test_dca_capped():
    """超过 max_amount 时触顶"""
    result = calculate("DCA", m=500, ma=20.0, quote=10.0, k=2, max_amount=1000)
    assert result["suggested_amount"] == 1000.0
    assert result["capped"] is True


def test_dca_shares():
    """份额计算正确"""
    result = calculate("DCA", m=500, ma=10.0, quote=10.0, k=2)
    assert abs(result["shares"] - 50.0) < 0.01


def test_unknown_strategy():
    """未知策略应报错"""
    try:
        calculate("UNKNOWN", m=500, ma=10.0, quote=10.0)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run python -m pytest tests/test_calculator.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: 实现 calculator.py**

```python
"""策略计算引擎 — 可扩展的投资策略计算"""
from typing import Callable

STRATEGY_REGISTRY: dict[str, Callable] = {}


def register_strategy(name: str):
    """装饰器：注册新的计算策略"""
    def decorator(func):
        STRATEGY_REGISTRY[name] = func
        return func
    return decorator


def calculate(strategy: str, **kwargs) -> dict:
    """统一入口：根据 strategy 名称分发到对应计算函数"""
    if strategy not in STRATEGY_REGISTRY:
        raise ValueError(
            f"未知策略: {strategy}，可用: {list(STRATEGY_REGISTRY.keys())}"
        )
    return STRATEGY_REGISTRY[strategy](**kwargs)


@register_strategy("DCA")
def calculate_dca(
    m: float,
    ma: float,
    quote: float,
    k: float = 2,
    max_amount: float | None = None,
    **kwargs,
) -> dict:
    """DCA 均线偏离法: suggested = M × (MA / Quote) ^ k"""
    ratio = ma / quote
    suggested = m * (ratio ** k)
    capped = False
    if max_amount is not None and suggested > max_amount:
        suggested = max_amount
        capped = True
    shares = suggested / quote
    return {
        "suggested_amount": round(suggested, 2),
        "shares": round(shares, 4),
        "capped": capped,
        "ratio": round(ratio, 4),
    }
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run python -m pytest tests/test_calculator.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

Run: `git add -A && git commit -m "feat: add calculator with DCA strategy"`

---

### Task 4: market_data.py — 行情数据获取

**Files:**
- Create: `dca_tracker/market_data.py`

- [ ] **Step 1: 实现 market_data.py**

```python
"""行情数据获取 — akshare (中国场外基金) + yfinance (加拿大股票)"""
import akshare as ak
import yfinance as yf


def get_china_fund_data(ticker: str) -> dict:
    """通过 akshare 获取场外基金净值和200日均线

    使用 fund_open_fund_info_em 获取历史净值数据，
    取最新净值作为 quote，计算200日均线作为 ma。
    """
    df = ak.fund_open_fund_info_em(symbol=ticker, indicator="单位净值走势")
    df.columns = ["date", "nav", "cumulative_nav", "daily_growth"]
    df["nav"] = df["nav"].astype(float)
    quote = df["nav"].iloc[-1]
    ma_days = min(200, len(df))
    ma = df["nav"].tail(ma_days).mean()
    return {"quote": round(quote, 4), "ma": round(ma, 4)}


def get_canada_stock_data(ticker: str) -> dict:
    """通过 yfinance 获取股价和200日均线"""
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1y")
    if hist.empty:
        raise ValueError(f"无法获取 {ticker} 的历史数据")
    quote = hist["Close"].iloc[-1]
    ma_days = min(200, len(hist))
    ma = hist["Close"].tail(ma_days).mean()
    return {"quote": round(float(quote), 4), "ma": round(float(ma), 4)}


def get_market_data(ticker: str, market: str) -> dict:
    """统一入口：根据 market 分发到对应函数"""
    if market == "China":
        return get_china_fund_data(ticker)
    elif market == "Canada":
        return get_canada_stock_data(ticker)
    else:
        raise ValueError(f"不支持的市场: {market}，可用: China, Canada")
```

- [ ] **Step 2: 手动测试 yfinance**

Run: `uv run python -c "from dca_tracker.market_data import get_canada_stock_data; print(get_canada_stock_data('VFV.TO'))"`
Expected: 输出 `{'quote': XX.XX, 'ma': XX.XX}`

- [ ] **Step 3: 手动测试 akshare**

Run: `uv run python -c "from dca_tracker.market_data import get_china_fund_data; print(get_china_fund_data('110011'))"`
Expected: 输出 `{'quote': XX.XX, 'ma': XX.XX}`

- [ ] **Step 4: Commit**

Run: `git add -A && git commit -m "feat: add market data module (akshare + yfinance)"`
