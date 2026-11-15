import re
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def extract_numbered_tickers(raw_text: str) -> list:
    """
    Strictly extracts stock tickers placed immediately after list numbers
    (e.g., '1. SAILIFE', '5.PNB', '2) EMCURE') and ignores all metrics,
    headers, and failed-filter descriptions.
    """
    cleaned = re.sub(r"<[^>]+>", " ", raw_text)
    cleaned = (
        cleaned.replace(".NS", "")
        .replace(".BO", "")
        .replace("*", "")
        .replace("`", "")
    )

    numbered_matches = re.findall(
        r"(?:^|\n)\s*\d{1,2}\s*[\.\)\:\-]\s*([A-Z][A-Z0-9&-]{1,19})(?=\s|\(|\||\:|\-|,|$)",
        cleaned,
    )

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
    if not TELEGRAM_BOT_TOKEN:
        print("[WARN] No Telegram Bot Token configured.")
        return default_tickers or []

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    raw_status = "unknown"

    try:
        res = requests.get(url, params={"offset": -10, "limit": 10}, timeout=10)
        data = res.json()
        ok = data.get("ok")
        results = data.get("result") or []
        desc = data.get("description")
        raw_status = f"ok={ok}, count={len(results)}, desc={desc}"
        print(f"[TELEGRAM RAW] {raw_status}")

        if ok and results:
            for update in reversed(results):
                msg_obj = (
                    update.get("message")
                    or update.get("channel_post")
                    or update.get("edited_message")
                    or update.get("edited_channel_post")
                    or {}
                )
                msg_text = msg_obj.get("text") or msg_obj.get("caption") or ""
                if not msg_text:
                    continue

                tickers = extract_numbered_tickers(msg_text)
                if tickers:
                    print(f"[TELEGRAM BRIDGE] Extracted {len(tickers)} numbered tickers: {tickers}")
                    return tickers

            print("[TELEGRAM BRIDGE] Messages found, but none contained a numbered stock list.")
        else:
            print("[TELEGRAM BRIDGE] Telegram returned no usable updates.")
    except Exception as exc:
        raw_status = f"error={exc}"
        print(f"[TELEGRAM BRIDGE ERROR] {exc}")

    if default_tickers:
        print(f"[TELEGRAM BRIDGE] Using provided fallback list: {default_tickers}")
        return default_tickers

    send_telegram_html(
        f"⚠️ <b>Swing-Engine:</b> No forwarded stock list found in Telegram "
        f"(<code>{raw_status}</code>).\n"
        f"Forward your Top 5 list directly to this bot in a 1-on-1 chat and re-run."
    )
    return []


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
    
