import io
import re
import requests
import pandas as pd
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# Words and indicator acronyms to ignore in forwarded screener alerts
STOPWORDS = {
    "ANALYZE", "CHECK", "SWING", "BUY", "SELL", "STOCK", "STOCKS", "START",
    "HELP", "ALERT", "CMP", "TGT", "TARGET", "STOP", "LOSS", "NSE", "BSE",
    "PRICE", "HIGH", "LOW", "DATE", "TIME", "IST", "INR", "VOLUME", "VOL",
    "RSI", "EMA", "SMA", "ATR", "ROC", "NIFTY", "RADAR", "SCORE", "FAILED",
    "FILTER", "FILTERS", "NONE", "ALL", "PASSED", "ENTRY", "EXIT", "HORIZON",
    "WEEK", "WEEKS", "DAY", "DAYS", "TOP", "LIST", "SCAN", "SCANNER", "JAN",
    "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"
}

def _get_valid_nse_symbols() -> set:
    """Fetches active NSE equity symbols to filter out any non-stock words."""
    url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            df = pd.read_csv(io.StringIO(resp.text))
            return set(df[df["SERIES"] == "EQ"]["SYMBOL"].dropna().str.strip().tolist())
    except Exception:
        pass
    return set()

def extract_tickers_from_forwarded_msg(raw_text: str) -> list:
    """
    Extracts up to 5 stock tickers from a rich forwarded Telegram message
    containing CMP, scores, and failed filter descriptions.
    """
    # Strip any HTML/Markdown formatting symbols while preserving case
    cleaned = re.sub(r"<[^>]+>", " ", raw_text)
    cleaned = cleaned.replace(".NS", "").replace(".BO", "").replace("*", "").replace("`", "")

    # Layer 1: Look for numbered/ranked stock entries (e.g., "1. PFOCUS", "2) PAYTM")
    # Matching on case-preserved text ignores Title-Case words like "Score" or "Failed"
    ranked_matches = re.findall(
        r"(?:^|\n)\s*[\•\-]?\s*\d+[\.\)\:]\s*([A-Z][A-Z0-9&-]{1,14})\b",
        cleaned
    )

    candidates = ranked_matches if ranked_matches else re.findall(r"\b[A-Z][A-Z0-9&-]{1,14}\b", cleaned)

    # Deduplicate while preserving order and removing metric acronyms
    unique_candidates = []
    seen = set()
    for sym in candidates:
        if sym not in STOPWORDS and sym not in seen:
            seen.add(sym)
            unique_candidates.append(sym)

    # Layer 2: Cross-check against official NSE symbols if available
    valid_nse = _get_valid_nse_symbols()
    if valid_nse:
        verified = [s for s in unique_candidates if s in valid_nse]
        if verified:
            return verified[:5]

    return unique_candidates[:5]

def fetch_latest_stock_names(default_tickers=None):
    """
    Polls getUpdates from the Telegram Bot API to extract stock tickers
    from your latest forwarded or direct message.
    """
    if default_tickers is None:
        default_tickers = ["TRENT", "BEL", "HAL", "DIXON", "PERSISTENT"]

    if not TELEGRAM_BOT_TOKEN:
        print("[WARN] No Telegram Bot Token configured. Using fallback tickers.")
        return default_tickers

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        res = requests.get(url, params={"offset": -10, "limit": 10}, timeout=10)
        data = res.json()
        if not data.get("ok") or not data.get("result"):
            return default_tickers

        for update in reversed(data["result"]):
            msg_obj = update.get("message") or update.get("channel_post") or {}
            msg_text = msg_obj.get("text") or msg_obj.get("caption") or ""
            if not msg_text:
                continue

            tickers = extract_tickers_from_forwarded_msg(msg_text)
            if tickers:
                print(f"[TELEGRAM BRIDGE] Extracted {len(tickers)} tickers from forwarded alert: {tickers}")
                return tickers
    except Exception as exc:
        print(f"[TELEGRAM BRIDGE ERROR] {exc}")

    print("[TELEGRAM BRIDGE] No valid tickers found in recent messages. Using fallback list.")
    return default_tickers

def send_telegram_html(message: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(message)
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        resp = requests.post(url, json=payload, timeout=12)
        return resp.status_code == 200
    except Exception as exc:
        print(f"[TELEGRAM DISPATCH ERROR] {exc}")
        return False
