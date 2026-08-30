import os
import pandas as pd
import requests
import yfinance as yf
from flask import Flask, jsonify, request

app = Flask(__name__)

LINE_ACCESS_TOKEN = os.environ.get("Etho4iyHRF+26XOAAYhY9PYgWK0hGGV+/9wRpORSvV7Q5aVOlwtvtDkLBWkYKyvLaDYHofQBUYXtD6YJ5lGeUGXnukyzo1+c6BD+hCycBXyg4Czs637y0gZEQK0e1N3X4SoLrUH1R89+29gGXlofYgdB04t89/1O/w1cDnyilFU=")


def analyze_stock(ticker_symbol: str):
    ticker_symbol = ticker_symbol.strip().upper()

    # รองรับหุ้นไทยอัตโนมัติ (ถ้าพิมพ์ชื่อหุ้นไทย 3-5 ตัวอักษร ให้เติม .BK)
    if not ticker_symbol.endswith(".BK") and len(ticker_symbol) <= 5:
        # ลองดึงข้อมูลเพื่อเช็คว่าเป็นหุ้นสหรัฐฯ หรือต้องเติม .BK
        df_test = yf.download(
            ticker_symbol, period="5d", progress=False, auto_adjust=False
        )
        if df_test.empty:
            ticker_symbol = f"{ticker_symbol}.BK"

    df = yf.download(
        ticker_symbol,
        period="1y",
        interval="1d",
        progress=False,
        auto_adjust=False,
    )

    if df.empty or len(df) < 200:
        return f"❌ ไม่พบข้อมูลหรือข้อมูลย้อนหลังของหุ้น {ticker_symbol} ไม่เพียงพอ"

    if isinstance(df.columns, pd.MultiIndex):
        close_series = df["Close"][ticker_symbol]
        low_series = df["Low"][ticker_symbol]
        high_series = df["High"][ticker_symbol]
    else:
        close_series = df["Close"]
        low_series = df["Low"]
        high_series = df["High"]

    current_price = float(close_series.iloc[-1])

    ema5 = float(close_series.ewm(span=5, adjust=False).mean().iloc[-1])
    ema20 = float(close_series.ewm(span=20, adjust=False).mean().iloc[-1])
    ema100 = float(close_series.ewm(span=100, adjust=False).mean().iloc[-1])
    ema200 = float(close_series.ewm(span=200, adjust=False).mean().iloc[-1])

    support = float(low_series.tail(30).min())
    resistance = float(high_series.tail(30).max())

    stop_loss = support * 0.98
    target = resistance

    risk = current_price - stop_loss
    reward = target - current_price

    if risk > 0 and reward > 0:
        rr_ratio = round(reward / risk, 2)
    else:
        rr_ratio = 0.0

    if rr_ratio >= 2.0:
        status = f"✅ ผ่านเกณฑ์น่าสนใจ — R:R {rr_ratio} (เกิน 2.0 เท่า)"
    else:
        status = f"❌ ยังไม่ผ่านเกณฑ์ — R:R {rr_ratio} ต่ำกว่า 2.0"

    report = (
        f"📊 {ticker_symbol} — ราคาปัจจุบัน: {current_price:.2f}\n\n"
        f"📈 เส้นค่าเฉลี่ย EMA:\n"
        f"• EMA 5   : {ema5:.2f}\n"
        f"• EMA 20  : {ema20:.2f}\n"
        f"• EMA 100 : {ema100:.2f}\n"
        f"• EMA 200 : {ema200:.2f}\n\n"
        f"🟢 แนวรับ (Support): {support:.2f}\n"
        f"🔴 แนวต้าน (Resistance): {resistance:.2f}\n\n"
        f"🎯 เป้าทำกำไร: {target:.2f}\n"
        f"🛑 จุดตัดขาดทุน: {stop_loss:.2f}\n"
        f"⚖️ Risk:Reward: {rr_ratio}\n\n"
        f"{status}"
    )
    return report


def reply_line_message(reply_token: str, message: str):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}",
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": message}],
    }
    requests.post(url, headers=headers, json=payload)


@app.route("/callback", methods=["POST"])
def callback():
    body = request.get_json()
    events = body.get("events", [])

    for event in events:
        if event.get("type") == "message":
            msg_type = event["message"].get("type")
            if msg_type == "text":
                user_text = event["message"]["text"].strip()
                reply_token = event["replyToken"]

                # ส่งข้อความที่ผู้ใช้พิมพ์ไปวิเคราะห์
                result_report = analyze_stock(user_text)

                # ตอบกลับเข้า LINE แชทเดิมทันที
                reply_line_message(reply_token, result_report)

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(port=5000)
