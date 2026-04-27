"""calculator 模块测试"""
from dca_tracker.calculator import calculate


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
