# Swing-Engine# Swing Momentum Technical Validator

An automated quantitative swing trading validation engine that runs daily at **04:00 AM IST** via GitHub Actions. It reads stock tickers from your Telegram chat, performs multi-timeframe technical analysis (Weekly, Daily, 60-min), computes trade risk brackets (Stop-Loss and Targets), and delivers an institutional AI-reasoned verdict directly to Telegram before the market opens.

---

## ⏰ Execution Timing

- **Automated Schedule:** Runs at **04:00 AM IST** (`22:30 UTC` previous day) Tuesday through Saturday, perfectly processing your nightly stock screens.
- **Manual Trigger:** Run on-demand anytime from the **Actions** tab on GitHub by clicking **Run workflow**.

---

## 📁 Repository Structure

```text
├── .github/
│   └── workflows/
│       └── swing_engine.yml    # Workflow running at 04:00 AM IST (22:30 UTC)
├── config.py                   # Strategy weights, score thresholds, environment variables
├── telegram_bridge.py          # Reads stock tickers from Telegram & sends HTML alerts
├── technical_engine.py         # Multi-timeframe quantitative indicator engine
├── ai_verdict.py               # Gemini 2.5 Flash / rules-based trade reasoning synthesis
├── main.py                     # Central execution pipeline
└── requirements.txt            # Python dependencies
