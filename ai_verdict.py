from config import GEMINI_API_KEY

def generate_reasoning_narrative(metrics: dict) -> str:
    ticker = metrics["Ticker"]
    verdict = metrics["Verdict"]
    score = metrics["Score"]
    cmp = metrics["CMP"]
    sl = metrics["Stop_Loss"]
    tgt1 = metrics["Target_1"]
    rr = metrics["RR_Ratio"]
    risk = metrics["Risk_%"]

    passed = [k for k, v in metrics["Checks"].items() if v]
    failed = [k for k, v in metrics["Checks"].items() if not v]

    # Attempt AI narrative generation via Gemini Free Tier
    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            prompt = (
                f"You are an elite quantitative swing trading risk manager. Analyze this stock for a 1-3 week swing trade:\n"
                f"Ticker: {ticker}\n"
                f"CMP: Rs. {cmp}\n"
                f"Score: {score}/100\n"
                f"Passing Factors: {', '.join(passed)}\n"
                f"Failing Factors: {', '.join(failed)}\n"
                f"RSI: {metrics['RSI']}, Stop Loss: Rs. {sl} (-{risk}%), Target: Rs. {tgt1} (+9%), R:R: 1:{rr}\n"
                f"Intraday Hourly Aligned: {metrics['Hourly_Bullish']}\n\n"
                f"Provide a 3-bullet point executive verdict: "
                f"1. Structural Trend & Base Assessment, "
                f"2. Volume & Volatility Contraction Quality, "
                f"3. Concrete Execution Action Plan (Entry, Invalidation, Target). Keep it concise, professional, and institutional."
            )
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            if response.text:
                return response.text.strip()
        except Exception as e:
            print(f"[GEMINI CALL FAILED] {e}. Falling back to rule-based analysis.")

    # High-quality deterministic fallback
    return (
        f"• <b>Base Structure:</b> {'Strong Stage 2 uptrend with EMA alignment and benchmark outperformance.' if score >= 70 else 'Base is loose or structurally compromised.'}\n"
        f"• <b>Catalyst & Volatility:</b> {'Bollinger bands compressed with recent volume absorption; breakout energy intact.' if 'BB Volatility Squeeze Release' in passed else 'Lacks clean contraction or volume thrust.'}\n"
        f"• <b>Trade Plan:</b> {'Execute near CMP ₹' + str(cmp) + ' with stop at ₹' + str(sl) + ' (-' + str(risk) + '%). Target 1: ₹' + str(tgt1) + '.' if verdict == 'UPWARD MOVEMENT LIKELY' else 'Avoid taking fresh exposure until the pivot tightens.'}"
    )
