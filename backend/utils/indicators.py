"""
Các hàm tính toán chỉ số kỹ thuật thuần túy.
Không DB, không side-effect. Chỉ nhận Series/DataFrame, trả Series/DataFrame.
"""
import numpy as np
import pandas as pd


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Tính chỉ số RSI (Relative Strength Index)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_indicators_per_group(df: pd.DataFrame) -> pd.DataFrame:
    """Tính EMA20, EMA50, MACD, RSI14, spread_pct, price_change, daily_return cho một nhóm type_code."""
    df = df.sort_values("ts").copy()
    price = df["mid_price"]

    # Derived price fields
    df["spread_pct"] = (df["spread"] / df["mid_price"].replace(0, np.nan) * 100).round(4).fillna(0)
    df["price_change"] = price.diff().fillna(0)
    df["daily_return_pct"] = (price.pct_change() * 100).round(4).fillna(0)

    # Technical indicators
    df["ema20"] = price.ewm(span=20, adjust=False).mean()
    df["ema50"] = price.ewm(span=50, adjust=False).mean()

    ema12 = price.ewm(span=12, adjust=False).mean()
    ema26 = price.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    df["rsi14"] = compute_rsi(price, period=14)

    return df


def none_if_nan(value):
    """Chuyển NaN/None thành None cho DB insert."""
    if value is None or pd.isna(value):
        return None
    return float(value)
