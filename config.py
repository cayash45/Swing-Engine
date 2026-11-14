import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

BENCHMARK_TICKER = "^NSEI"

# Multi-Timeframe Scoring Weights (Total = 100)
WEIGHTS = {
    "weekly_stage2": 15,
    "fast_ema_stack": 15,
    "relative_strength": 15,
    "bollinger_squeeze_break": 15,
    "volume_thrust": 15,
    "rsi_thrust_band": 10,
    "overhead_clearance": 15,
}

PASSING_THRESHOLD = 70  # Score >= 70 confirms upward probability
