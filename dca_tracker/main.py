"""Agent 入口函数 — run_dca(), add_product(), confirm_and_save()"""
from datetime import date, datetime

DCA_INTERVAL_DAYS = 29  # 两次定投之间的最少间隔天数

from dca_tracker.config import DEFAULT_K, DEFAULT_STRATEGY, MARKET_CONFIG
from dca_tracker.sheets import (
    get_unique_tickers, get_latest_record, append_record, init_sheet,
    get_all_records,
)
from dca_tracker.market_data import get_market_data
from dca_tracker.calculator import calculate


def run_dca() -> list[dict]:
    """自动定投计算：遍历所有 Ticker，计算建议买入金额。

    返回所有计算结果列表，Agent 据此向用户展示并确认。
    """
    tickers = get_unique_tickers()
    if not tickers:
        print("📭 无记录，请先使用 add_product() 添加产品。")
        return []

    results = []
    skipped = []
    for ticker in tickers:
        try:
            latest = get_latest_record(ticker)
            if not latest:
                continue

            name = latest.get("Name", "")

            # 检查 Status，Off 表示已清仓，跳过
            status = latest.get("Status", "On")
            if status == "Off":
                print(f"\n🚫 {name} ({ticker}) — 已清仓 (Status=Off)，跳过。")
                continue

            # 检查距离上次定投是否满 29 天
            last_date_str = latest.get("Date", "")
            if last_date_str:
                last_date = datetime.strptime(str(last_date_str), "%Y-%m-%d").date()
                days_since = (date.today() - last_date).days
                if days_since < DCA_INTERVAL_DAYS:
                    remaining = DCA_INTERVAL_DAYS - days_since
                    skipped.append((name, ticker, days_since, remaining))
                    print(
                        f"\n⏳ {name} ({ticker}) — "
                        f"距上次定投仅 {days_since} 天，"
                        f"还需等待 {remaining} 天。做时间的朋友 🕰️"
                    )
                    continue

            market = latest.get("Market", "")
            m = float(latest.get("M", 0))
            k = float(latest.get("k", DEFAULT_K))
            max_amt_raw = latest.get("Max Amount", "")
            max_amount = float(max_amt_raw) if max_amt_raw else None
            strategy = latest.get("Strategy", DEFAULT_STRATEGY)

            data = get_market_data(ticker, market)
            quote = data["quote"]
            ma = data["ma"]

            calc = calculate(
                strategy, m=m, ma=ma, quote=quote, k=k, max_amount=max_amount
            )
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
            print(
                f"   建议买入: {currency} {calc['suggested_amount']}"
                f" ({calc['shares']}份){cap_warn}"
            )

        except Exception as e:
            print(f"\n⚠️ {ticker} 处理失败: {e}")
            continue

    if results:
        print(f"\n{'='*50}")
        print(f"📋 共 {len(results)} 个产品待定投")
        total_by_currency: dict[str, float] = {}
        for r in results:
            c = r["currency"]
            total_by_currency[c] = total_by_currency.get(c, 0) + r["suggested_amount"]
        for c, t in total_by_currency.items():
            print(f"   {c} 合计: {t:.2f}")

    if skipped and not results:
        print(f"\n📋 所有 {len(skipped)} 个产品均未到定投日期，请耐心等待。")

    return results


def add_product(
    name: str,
    ticker: str,
    market: str,
    category: str,
    m: float,
    fee_rate: float = 0,
    total_amount: float | None = None,
    k: float = DEFAULT_K,
    max_amount: float | None = None,
    isin: str | None = None,
) -> dict:
    """添加新产品：获取行情、计算份额、写入 Sheet。

    Args:
        fee_rate: 费率（如 0.001 表示 0.1%），fees = total_amount × fee_rate
        首次买入时 total_amount 默认等于 M（基准定投额），
        max_amount 默认等于 5 * M。
    """
    if total_amount is None:
        total_amount = m
    if max_amount is None:
        max_amount = 5 * m
    data = get_market_data(ticker, market)
    quote = data["quote"]
    ma = data["ma"]
    fees = round(total_amount * fee_rate, 4)
    shares = round((total_amount - fees) / quote, 4)
    strategy = DEFAULT_STRATEGY
    calc = calculate(
        strategy, m=m, ma=ma, quote=quote, k=k, max_amount=max_amount
    )
    mc = MARKET_CONFIG.get(market, {})

    record = {
        "Date": date.today().isoformat(),
        "Type": "Buy",
        "Name": name,
        "Ticker": ticker,
        "Market": market,
        "Category": category,
        "ISIN": isin or "",
        "Quote": quote,
        "Currency": mc.get("currency", ""),
        "Fees": fee_rate,
        "Shares": shares,
        "Total Amount": total_amount,
        "Account": mc.get("account", ""),
        "Strategy": strategy,
        "M": m,
        "MA": ma,
        "k": k,
        "Suggested Amount": calc["suggested_amount"],
        "Max Amount": max_amount or "",
        "Status": "On",
    }

    append_record(record)
    print(f"✅ 已添加: {name} ({ticker})")
    print(f"   Quote: {quote} | 费率: {fee_rate} | 手续费: {fees}")
    print(f"   Shares: {shares} | Total: {total_amount}")
    return record


def confirm_and_save(
    ticker: str,
    suggested_amount: float,
    actual_amount: float | None = None,
) -> dict:
    """确认交易并保存到 Sheet。

    Args:
        ticker: 产品代码
        suggested_amount: 建议金额
        actual_amount: 实际金额，None 时使用 suggested_amount
    """
    latest = get_latest_record(ticker)
    if not latest:
        raise ValueError(f"未找到 {ticker} 的记录")

    amount = actual_amount if actual_amount is not None else suggested_amount
    market = latest.get("Market", "")
    data = get_market_data(ticker, market)
    quote = data["quote"]
    ma = data["ma"]
    fee_rate = float(latest.get("Fees", 0))
    fees = round(amount * fee_rate, 4)
    shares = round((amount - fees) / quote, 4)
    mc = MARKET_CONFIG.get(market, {})

    record = {
        "Date": date.today().isoformat(),
        "Type": "Buy",
        "Name": latest.get("Name", ""),
        "Ticker": ticker,
        "Market": market,
        "Category": latest.get("Category", ""),
        "ISIN": latest.get("ISIN", ""),
        "Quote": quote,
        "Currency": mc.get("currency", ""),
        "Fees": fee_rate,
        "Shares": shares,
        "Total Amount": amount,
        "Account": mc.get("account", ""),
        "Strategy": latest.get("Strategy", DEFAULT_STRATEGY),
        "M": latest.get("M", 0),
        "MA": ma,
        "k": latest.get("k", DEFAULT_K),
        "Suggested Amount": suggested_amount,
        "Max Amount": latest.get("Max Amount", ""),
        "Status": "On",
    }

    append_record(record)
    print(f"✅ 已保存: {latest.get('Name', '')} ({ticker})")
    print(f"   实际买入: {mc.get('currency', '')} {amount} | 手续费: {fees} ({shares}份)")
    return record


def record_sell(
    ticker: str,
    actual_amount: float,
    shares: float | None = None,
) -> dict:
    """记录部分卖出交易（Type=Sell, Status=On，不影响后续定投）。

    Args:
        ticker: 产品代码
        actual_amount: 卖出总金额
        shares: 卖出份额（可选，若不提供则根据当前报价估算）
    """
    latest = get_latest_record(ticker)
    if not latest:
        raise ValueError(f"未找到 {ticker} 的记录")

    market = latest.get("Market", "")
    mc = MARKET_CONFIG.get(market, {})

    data = get_market_data(ticker, market)
    quote = data["quote"]
    ma = data["ma"]
    fee_rate = float(latest.get("Fees", 0))
    fees = round(actual_amount * fee_rate, 4)

    if shares is None:
        shares = round((actual_amount - fees) / quote, 4)

    record = {
        "Date": date.today().isoformat(),
        "Type": "Sell",
        "Name": latest.get("Name", ""),
        "Ticker": ticker,
        "Market": market,
        "Category": latest.get("Category", ""),
        "ISIN": latest.get("ISIN", ""),
        "Quote": quote,
        "Currency": mc.get("currency", ""),
        "Fees": fee_rate,
        "Shares": shares,
        "Total Amount": actual_amount,
        "Account": mc.get("account", ""),
        "Strategy": latest.get("Strategy", DEFAULT_STRATEGY),
        "M": latest.get("M", 0),
        "MA": ma,
        "k": latest.get("k", DEFAULT_K),
        "Suggested Amount": "",
        "Max Amount": latest.get("Max Amount", ""),
        "Status": "On",
    }

    append_record(record)
    name = latest.get("Name", "")
    print(f"📤 已记录卖出: {name} ({ticker})")
    print(f"   卖出金额: {mc.get('currency', '')} {actual_amount} | 手续费: {fees} ({shares}份)")
    print(f"   Status 保持 On，继续参与定投计算。")
    return record


def sell_all(
    ticker: str,
    actual_amount: float | None = None,
    shares: float | None = None,
) -> dict:
    """清仓某个产品，写入一条 Type=Sell、Status=Off 的记录。

    Args:
        ticker: 产品代码
        actual_amount: 卖出总金额（可选，记录用）
        shares: 卖出份额（可选，记录用）

    后续 run_dca() 会自动跳过 Status=Off 的产品。
    """
    latest = get_latest_record(ticker)
    if not latest:
        raise ValueError(f"未找到 {ticker} 的记录")

    market = latest.get("Market", "")
    mc = MARKET_CONFIG.get(market, {})

    # 尝试获取当前行情
    try:
        data = get_market_data(ticker, market)
        quote = data["quote"]
        ma = data["ma"]
    except Exception:
        quote = latest.get("Quote", 0)
        ma = latest.get("MA", 0)

    record = {
        "Date": date.today().isoformat(),
        "Type": "Sell",
        "Name": latest.get("Name", ""),
        "Ticker": ticker,
        "Market": market,
        "Category": latest.get("Category", ""),
        "ISIN": latest.get("ISIN", ""),
        "Quote": quote,
        "Currency": mc.get("currency", ""),
        "Fees": latest.get("Fees", 0),
        "Shares": shares or "",
        "Total Amount": actual_amount or "",
        "Account": mc.get("account", ""),
        "Strategy": latest.get("Strategy", DEFAULT_STRATEGY),
        "M": latest.get("M", 0),
        "MA": ma,
        "k": latest.get("k", DEFAULT_K),
        "Suggested Amount": "",
        "Max Amount": latest.get("Max Amount", ""),
        "Status": "Off",
    }

    append_record(record)
    name = latest.get("Name", "")
    print(f"🔴 已清仓: {name} ({ticker}) — Status 已设为 Off")
    print(f"   后续 DCA 计算将自动跳过此产品。")
    return record
