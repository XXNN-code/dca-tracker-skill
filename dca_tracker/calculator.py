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
