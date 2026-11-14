import re
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def extract_numbered_tickers(raw_text: str) -> list:
    """
    Strictly extracts stock tickers placed immediately after list numbers
    (e.g., '1. SAILIFE', '5.PNB', '2) EMCURE') and ignores all metrics,
    headers, and failed-filter descriptions.
    """
    # Strip any HTML/Markdown formatting tags while preserving line breaks and case
    cleaned = re.sub(r"<[^>]+>", " ", raw_text)
    cleaned = (
        cleaned.replace(".NS", "")
        .replace(".BO", "")
        .replace("*", "")
        .replace("`", "")
    )

    # Match 1- or 2-digit list numbers at the start of a line followed by a ticker
    # Handles both spaced ("5. PNB") and unspaced ("5.PNB") formats
    numbered_matches = re.findall(
        r"(?:^|\n)\s*\d{1,2}\s*[\.\)\:\-]\s*([A-Z][A-Z0-9&-]{1,19})(?=\s|\(|\||\:|\-|,|$)",
        cleaned,
    )

    # Deduplicate while preserving exact rank order (1 to 5)
    seen = set()
    tickers = []
    for symbol in numbered_matches:
        if symbol not in seen:
            seen.add(symbol)
            tickers.append(symbol)

    if tickers:
        return tickers[:5]

    # Fallback ONLY for short direct commands without numbers (e.g., "/analyze TRENT, BEL")
    lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]
    if len(lines) <= 2:
        direct_text = re.sub(r"^/ANALYZE\b", "", cleaned.upper()).strip()
        direct_matches = re.findall(r"\b[A-Z][A-Z0-9&-]{1,19}\b", direct_text)
        reserved = {"ANALYZE", "CHECK", "SWING", "BUY", "SELL", "STOCK", "STOCKS", "START", "HELP"}
        for symbol in direct_matches:
            if symbol not in reserved and symbol not in seen:
                seen.add(symbol)
                tickers.append(symbol)

    return tickers[:5]


def fetch_latest_stock_names(default_tickers=None):
    """
    Polls getUpdates from the Telegram Bot API and extracts the numbered
    stock list from your latest forwarded radar message.
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

            tickers = extract_numbered_tickers(msg_text)
            if tickers:
                print(f"[TELEGRAM BRIDGE] Extracted {len(tickers)} numbered tickers: {tickers}")
                return tickers
    except Exception as exc:
        print(f"[TELEGRAM BRIDGE ERROR] {exc}")

    print("[TELEGRAM BRIDGE] No numbered stock list found in recent messages. Using fallback list.")
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
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=12)
        if resp.status_code == 200:
            return True
        print(f"[TELEGRAM ERROR] HTTP {resp.status_code}: {resp.text}")
        return False
    except Exception as exc:
        print(f"[TELEGRAM DISPATCH ERROR] {exc}")
        return False
