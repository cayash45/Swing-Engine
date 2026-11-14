import html
from config import PASSING_THRESHOLD
from telegram_bridge import fetch_latest_stock_names, send_telegram_html
from technical_engine import run_deep_technical_audit
from ai_verdict import generate_reasoning_narrative

def main():
    print("=" * 65)
    print("STARTING MULTI-TIMEFRAME SWING VALIDATION ENGINE")
    print("=" * 65)

    tickers = fetch_latest_stock_names()
    print(f"Auditing Stock Candidates: {tickers}")

    summary_cards = []

    for ticker in tickers:
        print(f"\nAnalyzing {ticker}...")
        metrics = run_deep_technical_audit(ticker)
        if "Error" in metrics:
            print(f"Skipping {ticker}: {metrics['Error']}")
            continue

        narrative = generate_reasoning_narrative(metrics)
        icon = "🟢 <b>BUY (UPWARD BIAS CONFIRMED)</b>" if metrics["Score"] >= PASSING_THRESHOLD else "🔴 <b>NO TRADE (HIGH FAILURE RISK)</b>"

        passed_checks = [k for k, v in metrics["Checks"].items() if v]
        failed_checks = [k for k, v in metrics["Checks"].items() if not v]

        card = (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 <b>{metrics['Ticker']}</b> | CMP: ₹{metrics['CMP']:,.2f}\n"
            f"📊 <b>Score:</b> {metrics['Score']}/100 | {icon}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Stop Loss:</b> ₹{metrics['Stop_Loss']:,.2f} (-{metrics['Risk_%']}%)\n"
            f"• <b>Target 1 (+9%):</b> ₹{metrics['Target_1']:,.2f} | <b>Target 2 (+18%):</b> ₹{metrics['Target_2']:,.2f}\n"
            f"• <b>Risk/Reward:</b> 1:{metrics['RR_Ratio']} | <b>RSI (14D):</b> {metrics['RSI']}\n"
            f"• <b>Passed:</b> {len(passed_checks)}/7 checks\n"
        )
        if failed_checks:
            card += f"• <b>Failed Filters:</b> <i>{html.escape(', '.join(failed_checks))}</i>\n"

        card += f"\n📝 <b>Executive Reasoning:</b>\n{narrative}\n"
        summary_cards.append(card)

    if not summary_cards:
        print("No valid candidates evaluated.")
        return

    full_message = "⚡ <b>INSTITUTIONAL SWING VALIDATION REPORT</b>\n" + "\n".join(summary_cards)
    
    # Split messages if approaching Telegram's 4,096 char limit
    if len(full_message) <= 3900:
        send_telegram_html(full_message)
    else:
        for card in summary_cards:
            send_telegram_html(card)

    print("\n[SUCCESS] Analysis dispatched to Telegram.")

if __name__ == "__main__":
    main()
