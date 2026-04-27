"""行情数据获取 — akshare (中国场外基金) + yfinance (加拿大股票)"""
import akshare as ak
import yfinance as yf


def get_china_fund_data(ticker: str) -> dict:
    """通过 akshare 获取场外基金净值和200日均线

    使用 fund_open_fund_info_em 获取历史净值数据，
    取最新净值作为 quote，计算200日均线作为 ma。
    """
    df = ak.fund_open_fund_info_em(symbol=ticker, indicator="单位净值走势")
    if df.empty:
        raise ValueError(f"无法获取基金 {ticker} 的数据")

    # fund_open_fund_info_em 返回列: 净值日期, 单位净值, 日增长率
    # 列名可能因版本而异，按位置取值更稳定
    nav_col = df.columns[1]  # 第二列是单位净值
    df[nav_col] = df[nav_col].astype(float)

    quote = df[nav_col].iloc[-1]
    ma_days = min(200, len(df))
    ma = df[nav_col].tail(ma_days).mean()

    return {"quote": round(float(quote), 4), "ma": round(float(ma), 4)}


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
    """统一入口：根据 market 分发到对应函数

    返回: {"quote": float, "ma": float}
    """
    if market == "China":
        return get_china_fund_data(ticker)
    elif market == "Canada":
        return get_canada_stock_data(ticker)
    else:
        raise ValueError(f"不支持的市场: {market}，可用: China, Canada")
