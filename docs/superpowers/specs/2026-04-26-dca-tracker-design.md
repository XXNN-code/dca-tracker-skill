# DCA Tracker 设计文档

> 自动定投追踪系统 — AI Agent 驱动的智能定投计算与记录工具

## 1. 项目概述

### 1.1 目标

构建一个 Python 模块，由 AI Agent 调用执行，实现：
- 自动读取 Google Sheet 中的定投记录
- 通过 akshare / yfinance API 获取实时行情和200日均线
- 使用 DCA 均线偏离法（`M × (MA/Quote)^k`）计算建议买入金额
- 将交易记录写回 Google Sheet

### 1.2 核心约束

- **执行方式**：AI Agent 通过 `uv run` 调用 Python 函数，不是独立 CLI 程序
- **数据存储**：Google Sheets（通过 Service Account 认证）
- **市场支持**：中国（场外基金，akshare）+ 加拿大（股票/ETF，yfinance）
- **交互模式**：计算结果由 Agent 展示给用户确认，用户同意后再写入 Sheet

### 1.3 两种操作模式

| 模式 | 触发方式 | 说明 |
|------|---------|------|
| **定投计算** | 用户说"执行定投" | 自动遍历所有 Ticker 计算建议金额 |
| **添加产品** | 用户说"添加新产品 XXX" | Agent 收集参数后调用 add_product() |

## 2. Google Sheet 数据结构

Sheet 名称：`DCA_Tracker`，工作表名称：`Records`

| 列名 | 类型 | 来源 | 说明 |
|------|------|------|------|
| Date | 日期 | 自动 | 当天日期 `YYYY-MM-DD` |
| Type | 文本 | 自动 | `Buy` / `Sell` |
| Name | 文本 | 用户输入 | 产品名称，如"易方达中小盘" |
| Ticker | 文本 | 用户输入 | 代码，如 `110011` 或 `VFV.TO` |
| Market | 文本 | 用户输入 | `China` / `Canada` |
| ISIN | 文本 | 可选 | 国际证券识别码 |
| Quote | 数字 | API | 当天单价（基金净值/股价）|
| Currency | 文本 | 自动 | China→`CNY`，Canada→`CAD` |
| Fees | 数字 | 用户输入 | 手续费 |
| Shares | 数字 | 计算 | `Total Amount / Quote` |
| Total Amount | 数字 | 计算/确认 | 实际交易总额，默认=Suggested Amount，用户可覆盖 |
| Account | 文本 | 自动 | China→`支付宝`，Canada→`iTRADE` |
| Strategy | 文本 | 用户输入 | 交易策略，默认 `DCA`，未来可选 `VA` 等 |
| M | 数字 | 用户输入 | 基准定投额 |
| MA | 数字 | API | 200日均线价格 |
| k | 数字 | 默认=2 | 敏感度系数，可按产品调整 |
| Suggested Amount | 数字 | 计算 | `min(M × (MA/Quote)^k, Max Amount)` |
| Max Amount | 数字 | 用户输入 | 最大买入限额 |

### 自动推导规则

- `Date` = 当天日期
- `Type` = `Buy`（添加产品时固定）
- `Currency` = 由 `Market` 推导（China→CNY, Canada→CAD）
- `Account` = 由 `Market` 推导（China→支付宝, Canada→iTRADE）
- `Strategy` = 默认 `DCA`，决定使用哪种计算策略
- `k` = 默认 `2`，用户可按产品调整
- `Quote`, `MA` = 通过 API 自动获取
- `Shares` = `Total Amount / Quote`
- `Suggested Amount` = `min(M × (MA/Quote)^k, Max Amount)`

## 3. 模块架构

```
VibeCoding/
├── dca_tracker/
│   ├── __init__.py          # 导出核心函数
│   ├── main.py              # 入口：run_dca(), add_product(), confirm_and_save()
│   ├── sheets.py            # Google Sheets CRUD
│   ├── market_data.py       # 行情数据获取（akshare / yfinance）
│   ├── calculator.py        # DCA 公式计算
│   └── config.py            # 常量与默认配置
├── credentials/             # Google API 密钥（.gitignore）
│   └── service_account.json
├── pyproject.toml
├── setup_guide.md           # Google API 设置指南
└── README.md
```

### 3.1 `config.py` — 常量与映射

```python
DEFAULT_K = 2
DEFAULT_STRATEGY = "DCA"

MARKET_CONFIG = {
    "China":  {"currency": "CNY", "account": "支付宝"},
    "Canada": {"currency": "CAD", "account": "iTRADE"},
}

SHEET_NAME = "DCA_Tracker"
WORKSHEET_NAME = "Records"

SHEET_COLUMNS = [
    "Date", "Type", "Name", "Ticker", "Market", "ISIN",
    "Quote", "Currency", "Fees", "Shares", "Total Amount",
    "Account", "Strategy", "M", "MA", "k",
    "Suggested Amount", "Max Amount"
]

CREDENTIALS_PATH = "credentials/service_account.json"
```

### 3.2 `sheets.py` — Google Sheets 操作

```python
def get_client():
    """获取 gspread 客户端（Service Account 认证）"""

def init_sheet():
    """首次创建 Sheet 和工作表，写入表头。如已存在则跳过。"""

def get_all_records() -> list[dict]:
    """读取所有记录，返回字典列表"""

def get_unique_tickers() -> list[str]:
    """获取不重复的 Ticker 列表"""

def get_latest_record(ticker: str) -> dict | None:
    """获取某 Ticker 最新一条记录（最后一行）"""

def append_record(record: dict):
    """追加一行新记录到 Sheet"""
```

### 3.3 `market_data.py` — 行情获取

```python
def get_china_fund_data(ticker: str) -> dict:
    """通过 akshare 获取场外基金净值和200日均线
    返回: {"quote": float, "ma": float}
    """

def get_canada_stock_data(ticker: str) -> dict:
    """通过 yfinance 获取股价和200日均线
    返回: {"quote": float, "ma": float}
    """

def get_market_data(ticker: str, market: str) -> dict:
    """统一入口，根据 market 分发到对应函数
    返回: {"quote": float, "ma": float}
    """
```

### 3.4 `calculator.py` — 策略计算（可扩展）

采用策略注册模式，当前实现 DCA，未来可直接添加 VA 等新策略：

```python
# 策略注册表
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
        raise ValueError(f"未知策略: {strategy}，可用: {list(STRATEGY_REGISTRY.keys())}")
    return STRATEGY_REGISTRY[strategy](**kwargs)

@register_strategy("DCA")
def calculate_dca(
    m: float,
    ma: float,
    quote: float,
    k: float = 2,
    max_amount: float | None = None,
    **kwargs  # 忽略其他策略的参数
) -> dict:
    """
    DCA 均线偏离法计算
    
    公式: suggested = M × (MA / Quote) ^ k
    如果 suggested > max_amount，则 suggested = max_amount
    
    返回: {
        "suggested_amount": float,
        "shares": float,          # suggested_amount / quote
        "capped": bool,           # 是否触顶
        "ratio": float,           # MA / Quote 比值
    }
    """

# 未来添加 VA 策略示例：
# @register_strategy("VA")
# def calculate_va(month, target_value, current_value, quote, ...) -> dict:
#     ...
```

### 3.5 `main.py` — Agent 入口函数

```python
def run_dca() -> list[dict]:
    """
    自动定投计算（默认模式）
    
    流程:
    1. 读取 Sheet，获取所有不重复的 Ticker
    2. 对每个 Ticker：
       - 读取最新记录获取 M, k, Max Amount, Market 等配置
       - 通过 API 获取当日 Quote 和 MA
       - 计算 Suggested Amount
    3. 打印汇总表
    4. 返回所有计算结果列表
    
    返回: [{"ticker", "name", "quote", "ma", "suggested_amount", "shares", ...}, ...]
    """

def add_product(
    name: str,
    ticker: str,
    market: str,
    fees: float,
    total_amount: float,
    m: float,
    k: float = 2,
    max_amount: float | None = None,
    isin: str | None = None
) -> dict:
    """
    添加新产品
    
    流程:
    1. 自动获取 Quote 和 MA
    2. 设置自动推导字段（date, currency, account 等）
    3. 计算 shares = total_amount / quote
    4. 追加记录到 Sheet
    5. 返回写入的完整记录
    """

def confirm_and_save(
    ticker: str,
    suggested_amount: float,
    actual_amount: float | None = None
) -> dict:
    """
    确认交易并保存到 Sheet
    
    - actual_amount 为 None 时使用 suggested_amount
    - 从最新记录获取配置信息
    - 重新获取 Quote 计算 shares
    - 追加新记录到 Sheet
    - 返回写入的完整记录
    """
```

## 4. 工作流详细设计

### 4.1 `run_dca()` 工作流

```
开始
  ↓
初始化 Google Sheets 客户端
  ↓
读取所有记录 → 提取不重复 Ticker 列表
  ↓
如果无记录 → 打印提示"请先 add_product" → 返回空列表
  ↓
┌─ 遍历每个 Ticker ──────────────────────────┐
│  读取该 Ticker 最新一条记录                   │
│  提取: Name, Market, M, k, Max Amount, Fees  │
│  ↓                                           │
│  根据 Market 调用 akshare 或 yfinance        │
│  获取当日 Quote 和 200日 MA                   │
│  ↓                                           │
│  计算:                                        │
│    suggested = min(M × (MA/Quote)^k, Max Amount) │
│    shares = suggested / quote                 │
│  ↓                                           │
│  打印单条结果:                                │
│  "[Name] (Ticker)"                            │
│  "  Quote: XX | MA: XX | MA/Quote: XX"        │
│  "  建议买入: XX | 份额: XX"                   │
│  ↓                                           │
│  将结果加入汇总列表                            │
└──────────────────────────────────────────────┘
  ↓
打印汇总表（所有 Ticker 的建议金额总览）
  ↓
返回结果列表
```

### 4.2 `add_product()` 工作流

```
接收参数: name, ticker, market, fees, total_amount, m, k=2, max_amount
  ↓
自动推导:
  date = 今天
  type = "Buy"
  currency = MARKET_CONFIG[market]["currency"]
  account = MARKET_CONFIG[market]["account"]
  strategy = "DCA"
  ↓
调用 get_market_data(ticker, market) → 获取 quote, ma
  ↓
计算:
  shares = total_amount / quote
  suggested_amount = min(m × (ma/quote)^k, max_amount)
  ↓
构建完整记录字典（18个字段）
  ↓
调用 append_record(record) → 写入 Sheet
  ↓
打印确认信息
返回记录
```

### 4.3 Agent 交互流程

```
用户: "执行定投"
  ↓
Agent 运行 run_dca() → 获得结果列表
  ↓
Agent 展示结果:
  "以下是今天的定投建议：
   1. 易方达中小盘 (110011): 建议买入 ¥523.40 (5.23份)
   2. VFV (VFV.TO): 建议买入 C$487.20 (3.21份)
   是否按建议金额执行？"
  ↓
用户确认 → Agent 逐个调用 confirm_and_save()
或
用户修改 → Agent 调用 confirm_and_save(ticker, suggested, actual=用户金额)
```

## 5. 错误处理

| 场景 | 处理方式 |
|------|---------|
| Google Sheet 连接失败 | 抛出异常，打印明确错误信息，提示检查 credentials 文件 |
| API 获取行情失败 | 跳过该 Ticker，打印警告，继续处理其他 Ticker |
| 中国基金净值当天未更新 | 使用最近一个交易日的净值，打印提示 |
| Sheet 为空（首次 run_dca） | 打印 "无记录，请先使用 add_product 添加产品" |
| MA 数据不足200天 | 使用已有数据计算均线，打印警告 |
| Ticker 不存在 / 格式错误 | 抛出 ValueError，提示正确格式 |
| 网络超时 | 重试1次，仍失败则跳过 |

## 6. 依赖

```
gspread>=6.0.0        # Google Sheets API
google-auth>=2.0.0     # Google 认证
akshare>=1.10.0        # 中国市场数据（场外基金）
yfinance>=0.2.0        # 加拿大市场数据
```

## 7. Google Cloud API 设置步骤

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目（或选择已有项目）
3. 启用 **Google Sheets API** 和 **Google Drive API**
4. 创建 **服务账户**（Service Account）
5. 为服务账户创建 **JSON 密钥**
6. 下载密钥文件，保存到 `credentials/service_account.json`
7. 程序首次运行时会自动创建 Sheet 并输出 Sheet URL
8. 打开 Sheet → 点击"共享" → 将服务账户邮箱添加为编辑者

## 8. 未来扩展预留

- **新交易策略**（VA 等）— 在 `calculator.py` 中用 `@register_strategy("VA")` 注册新函数，Sheet 中 `Strategy` 列填 `VA` 即可自动使用
- 支持更多中国市场类型（A股、场内ETF）— 在 `market_data.py` 中添加新函数
- 支持更多市场（美股等）— 在 `config.py` 中添加 MARKET_CONFIG 条目
- 卖出逻辑 — 当 MA/Quote 比值低于阈值时建议卖出
- 历史分析 — 基于 Sheet 记录生成收益分析报告
