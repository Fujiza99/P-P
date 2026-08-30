import os
import yfinance as yf
import pandas as pd
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# รหัส Channel Access Token และ Channel Secret
LINE_ACCESS_TOKEN = "Etho4iyHRF+26XOAAYhY9PYgWK0hGGV+/9wRpORSvV7Q5aVOlwtvtDkLBWkYKyvLaDYHofQBUYXtD6YJ5lGeUGXnukyzo1+c6BD+hCycBXyg4Czs637y0gZEQK0e1N3X4SoLrUH1R89+29gGXlofYgdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "59177a4d4c5e0e538b3a62895b67756f"

line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/", methods=['GET'])
def index():
    return "Stock Line Bot is running!", 200

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    except Exception as e:
        print(f"Error handling webhook: {e}")
        return 'OK', 200
    return 'OK', 200

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    symbol = event.message.text.strip().upper()
    
    # ดึงข้อมูลราคาหุ้น
    search_symbol = symbol
    ticker = yf.Ticker(search_symbol)
    df = ticker.history(period="1y")

    # ถ้าค้นหาเพียวๆ ไม่เจอ และไม่ได้ลงท้ายด้วย .BK ให้ลองเติม .BK (สำหรับหุ้นไทย)
    if df.empty and not search_symbol.endswith(".BK"):
        search_symbol = f"{symbol}.BK"
        ticker = yf.Ticker(search_symbol)
        df = ticker.history(period="1y")

    try:
        # ตัดแถวที่ไม่มีข้อมูลราคา (NaN) ออก เพื่อป้องกันปัญหาแสดงผล "nan"
        df = df.dropna(subset=['Close'])

        if df.empty:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"❌ ไม่พบข้อมูลหุ้น '{symbol}' กรุณาเช็กชื่ออักษรอีกครั้งครับ")
            )
            return

        # คำนวณค่า EMA
        df['EMA5'] = df['Close'].ewm(span=5, adjust=False).mean()
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA100'] = df['Close'].ewm(span=100, adjust=False).mean()
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()

        # ดึงราคาปิดและค่า EMA ล่าสุดที่ไม่ใช่ NaN
        last_price = df['Close'].iloc[-1]
        ema5 = df['EMA5'].iloc[-1]
        ema20 = df['EMA20'].iloc[-1]
        ema100 = df['EMA100'].iloc[-1]
        ema200 = df['EMA200'].iloc[-1]

        # คำนวณแนวรับ-แนวต้าน (High/Low ในรอบ 20 วันล่าสุด)
        recent_high = df['High'].tail(20).max()
        recent_low = df['Low'].tail(20).min()

        reply_text = (
            f"📊 ผลวิเคราะห์หุ้น: {search_symbol}\n"
            f"-------------------\n"
            f"💵 ราคาล่าสุด: {last_price:.2f}\n\n"
            f"📈 เส้นเคลื่อนที่ EMA:\n"
            f"• EMA 5   : {ema5:.2f}\n"
            f"• EMA 20  : {ema20:.2f}\n"
            f"• EMA 100 : {ema100:.2f}\n"
            f"• EMA 200 : {ema200:.2f}\n\n"
            f"🎯 กรอบแนวรับ-แนวต้าน (20 วัน):\n"
            f"• แนวต้าน (High) : {recent_high:.2f}\n"
            f"• แนวรับ (Low)   : {recent_low:.2f}"
        )

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )

    except Exception as e:
        print(f"Error processing stock: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"⚠️ เกิดข้อผิดพลาดในการดึงข้อมูลหุ้น {symbol}\n({str(e)})")
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
