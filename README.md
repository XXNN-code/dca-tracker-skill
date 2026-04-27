# DCA Tracker — 自动定投追踪系统

AI Agent 驱动的智能定投计算与记录工具。

## 功能

- 📊 **自动定投计算** — 批量计算所有产品的建议买入金额
- ➕ **添加新产品** — 自动获取行情并写入 Google Sheet
- 📈 **双市场支持** — 中国场外基金（akshare）+ 加拿大股票（yfinance）
- 🔄 **可扩展策略** — 当前支持 DCA 均线偏离法，预留 VA 等策略接口

## 安装

```powershell
uv venv
.\.venv\Scripts\Activate.ps1
uv pip install -e .
```

## Google API 设置

详见 [setup_guide.md](setup_guide.md)

## 使用方式（通过 AI Agent）

### 执行定投
```python
from dca_tracker.main import run_dca
results = run_dca()
```

### 添加新产品
```python
from dca_tracker.main import add_product
add_product('易方达中小盘', '110011', 'China', 0, 500, 500)
```

### 确认交易
```python
from dca_tracker.main import confirm_and_save
confirm_and_save('110011', suggested_amount=523.4)
# 或指定实际金额
confirm_and_save('110011', suggested_amount=523.4, actual_amount=500)
```

## DCA 公式

```
Suggested Amount = M × (MA / Quote) ^ k
```

- **M**: 基准定投额
- **MA**: 200日均线
- **Quote**: 当日价格
- **k**: 敏感度系数（默认 2）
