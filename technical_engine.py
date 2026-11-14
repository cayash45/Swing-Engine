import numpy as np
import pandas as pd
import yfinance as yf
from config import BENCHMARK_TICKER, WEIGHTS

def _calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = up / (down + 1e-9)
    return 100.0 - (100.0 / (1.0 + rs))

def _calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"]
    tr1 = h - l
    tr2 = (h - c.shift(1)).abs()
    tr3 = (l - c.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def run_deep_technical_audit(ticker: str) -> dict:
    ns_ticker = ticker if ticker.endswith(".NS") else f"{ticker}.NS"
    
    # 1. Fetch Multi-Timeframe Data
    try:
        daily_df = yf.download(ns_ticker, period="1y", interval="1d", progress=False)
        bench_df = yf.download(BENCHMARK_TICKER, period="1y", interval="1d", progress=False)
        weekly_df = yf.download(ns_ticker, period="2y", interval="1wk", progress=False)
        hourly_df = yf.download(ns_ticker, period="1mo", interval="60m", progress=False)
    except Exception as exc:
        return {"Ticker": ticker, "Error": f"Download failed: {exc}"}

    if daily_df.empty or len(daily_df) < 120 or bench_df.empty:
        return {"Ticker": ticker, "Error": "Insufficient historical data"}

    # Flatten MultiIndex columns if returned by yfinance
    for d in (daily_df, bench_df, weekly_df, hourly_df):
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = [col[0] for col in d.columns]

    close = daily_df["Close"]
    high = daily_df["High"]
    low = daily_df["Low"]
    volume = daily_df["Volume"]
    cmp = float(close.iloc[-1])

    # ---------------------------------------------------------
    # 1. WEEKLY CHECK (Stage Analysis & 30-Week SMA)
    # ---------------------------------------------------------
    w_close = weekly_df["Close"]
    w_sma30 = w_close.rolling(30).mean()
    weekly_stage2 = bool((w_close.iloc[-1] > w_sma30.iloc[-1]) and (w_sma30.iloc[-1] > w_sma30.iloc[-4]))

    # ---------------------------------------------------------
    # 2. DAILY TREND STACK (Minervini Stage 2 Template)
    # ---------------------------------------------------------
    ema10 = close.ewm(span=10, adjust=False).mean()
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    ema200 = close.ewm(span=200, adjust=False).mean()

    fast_ema_stack = bool(cmp > ema10.iloc[-1] > ema20.iloc[-1] > ema50.iloc[-1] > ema200.iloc[-1])
    ema20_slope_up = bool(ema20.iloc[-1] > ema20.iloc[-5])

    # ---------------------------------------------------------
    # 3. RELATIVE STRENGTH (RS vs Nifty 50)
    # ---------------------------------------------------------
    bench_close = bench_df["Close"].reindex(close.index).ffill()
    stock_ret_20d = (cmp - close.iloc[-21]) / close.iloc[-21]
    bench_ret_20d = (bench_close.iloc[-1] - bench_close.iloc[-21]) / bench_close.iloc[-21]
    rs_outperforming = bool(stock_ret_20d > bench_ret_20d + 0.03)  # +3% excess alpha

    # ---------------------------------------------------------
    # 4. VOLATILITY CONTRACTION (Bollinger Band Squeeze Release)
    # ---------------------------------------------------------
    sma20 = close.rolling(20).mean()
    sd20 = close.rolling(20).std(ddof=0)
    bb_width = (4.0 * sd20) / (sma20 + 1e-9)
    bb_rank = bb_width.rolling(125).rank(pct=True) * 100.0
    bb_squeeze = bool((bb_rank.iloc[-5:-1] <= 15.0).any())
    bb_expansion = bool(bb_width.iloc[-1] > bb_width.iloc[-3:].min())
    bb_setup = bb_squeeze and bb_expansion

    # ---------------------------------------------------------
    # 5. VOLUME FOOTPRINT (VDU followed by volume surge)
    # ---------------------------------------------------------
    vol_sma20 = volume.rolling(20).mean()
    vol_surge = bool((volume.iloc[-3:] >= 1.4 * vol_sma20.iloc[-3:]).any())
    recent_vdu = bool((volume.iloc[-10:-2] < 0.65 * vol_sma20.iloc[-10:-2]).any())
    volume_quality = vol_surge or (recent_vdu and cmp > ema10.iloc[-1])

    # ---------------------------------------------------------
    # 6. RSI THRUST BAND & OVERHEAD RESISTANCE
    # ---------------------------------------------------------
    rsi14 = float(_calc_rsi(close, 14).iloc[-1])
    rsi_pass = bool(52.0 <= rsi14 <= 68.0)

    high_52w = float(high.rolling(min(252, len(daily_df))).max().iloc[-1])
    overhead_clear = bool(cmp >= high_52w * 0.85)

    # ---------------------------------------------------------
    # 7. HOURLY INTRADAY STRUCTURE
    # ---------------------------------------------------------
    hourly_ok = True
    if not hourly_df.empty and len(hourly_df) >= 20:
        h_close = hourly_df["Close"]
        h_ema20 = h_close.ewm(span=20, adjust=False).mean()
        hourly_ok = bool(h_close.iloc[-1] > h_ema20.iloc[-1])

    # Quantitative Scoring
    score = 0
    checks = {
        "Weekly Stage 2 (Above 30W SMA)": weekly_stage2,
        "Fast EMA Stack (10>20>50>200)": fast_ema_stack and ema20_slope_up,
        "Relative Strength vs Index": rs_outperforming,
        "BB Volatility Squeeze Release": bb_setup,
        "Volume Footprint (VDU/Surge)": volume_quality,
        "RSI Momentum Zone (52-68)": rsi_pass,
        "Overhead Supply Clear (Near 52W High)": overhead_clear,
    }

    if weekly_stage2: score += WEIGHTS["weekly_stage2"]
    if fast_ema_stack and ema20_slope_up: score += WEIGHTS["fast_ema_stack"]
    if rs_outperforming: score += WEIGHTS["relative_strength"]
    if bb_setup: score += WEIGHTS["bollinger_squeeze_break"]
    if volume_quality: score += WEIGHTS["volume_thrust"]
    if rsi_pass: score += WEIGHTS["rsi_thrust_band"]
    if overhead_clear: score += WEIGHTS["overhead_clearance"]

    atr_series = _calc_atr(daily_df, 14)
    atr_val = float(atr_series.iloc[-1])
    stop_loss = round(cmp - (1.5 * atr_val), 2)
    risk_pct = round(((cmp - stop_loss) / cmp) * 100.0, 2)
    target_1 = round(cmp * 1.09, 2)
    target_2 = round(cmp * 1.18, 2)
    rr_ratio = round(9.0 / risk_pct, 2) if risk_pct > 0 else 0.0

    return {
        "Ticker": ticker,
        "CMP": cmp,
        "Score": score,
        "Checks": checks,
        "Hourly_Bullish": hourly_ok,
        "RSI": round(rsi14, 1),
        "ATR": round(atr_val, 2),
        "Stop_Loss": stop_loss,
        "Risk_%": risk_pct,
        "Target_1": target_1,
        "Target_2": target_2,
        "RR_Ratio": rr_ratio,
        "Verdict": "UPWARD MOVEMENT LIKELY" if score >= 70 and hourly_ok else "UNFAVORABLE / WAIT"
    }
