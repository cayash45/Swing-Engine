import re
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def fetch_latest_stock_names(default_tickers=None):
    """
    Polls getUpdates from the Telegram Bot API to extract stock tickers 
    from the user's latest message or command.
    """
    if default_tickers is None:
        default_tickers = ["TRENT", "BEL", "HAL", "DIXON", "PERSISTENT"]

    if not TELEGRAM_BOT_TOKEN:
        print("[WARN] No Telegram Bot Token configured. Using fallback tickers.")
        return default_tickers

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        res = requests.get(url, params={"offset": -5, "limit": 5}, timeout=10)
        data = res.json()
        if not data.get("ok") or not data.get("result"):
            return default_tickers

        # Search for message text in reverse chronological order
        for update in reversed(data["result"]):
            msg = update.get("message", {}).get("text", "")
            if not msg:
                continue

            # Extracts capital ticker symbols (e.g., "TRENT, BEL", "Analyze HAL")
            clean_text = msg.upper().replace(".NS", "").replace("/ANALYZE", "")
            found = re.findall(r"\b[A-Z]{3,12}\b", clean_text)
            
            # Exclude common command words
            reserved = {"ANALYZE", "CHECK", "SWING", "BUY", "SELL", "STOCK", "STOCKS", "START"}
            filtered = [t for t in found if t not in reserved]
            
            if len(filtered) >= 1:
                return filtered[:5]
    except Exception as exc:
        print(f"[TELEGRAM BRIDGE ERROR] {exc}")

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
