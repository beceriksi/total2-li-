import ccxt
import pandas as pd
import numpy as np
import os, requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(msg):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": msg}
        requests.post(url, data=data)

def fetch_ohlcv(symbol, timeframe='1h', limit=100):
    try:
        return exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    except Exception:
        return None

def ema(values, period):
    return pd.Series(values).ewm(span=period, adjust=False).mean()

exchange = ccxt.mexc()
markets = exchange.load_markets()

# === BTC Trend Kontrolü ===
btc_data = exchange.fetch_ohlcv('BTC/USDT', timeframe='1h', limit=100)
df = pd.DataFrame(btc_data, columns=['time','open','high','low','close','volume'])
df['ema20'] = ema(df['close'], 20)
df['ema50'] = ema(df['close'], 50)
market_up = df['ema20'].iloc[-1] > df['ema50'].iloc[-1]

market_status = "✅ BTC Trend Pozitif" if market_up else "⚠️ BTC Trend Zayıf"

signals = []
for symbol in markets:
    if not symbol.endswith("/USDT"):
        continue
    try:
        ohlcv = fetch_ohlcv(symbol, '1h', 100)
        if not ohlcv:
            continue
        df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])
        df['ema20'] = ema(df['close'], 20)
        df['rsi'] = pd.Series(df['close']).diff().fillna(0)
        df['gain'] = np.where(df['rsi']>0, df['rsi'], 0)
        df['loss'] = np.where(df['rsi']<0, -df['rsi'], 0)
        avg_gain = df['gain'].rolling(14).mean()
        avg_loss = df['loss'].rolling(14).mean()
        df['rs'] = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + df['rs']))

        last = df.iloc[-1]
        prev = df.iloc[-2]

        vol_change = (last['volume'] - prev['volume']) / prev['volume'] * 100
        if (
            last['close'] > last['ema20'] and
            last['rsi'] < 70 and
            vol_change > 30
        ):
            signals.append(f"✅ {symbol} | RSI {last['rsi']:.1f} | Hacim +{vol_change:.0f}%")

    except Exception:
        continue

# === Mesaj Gönder ===
if signals:
    send_telegram(f"{market_status}\n🔥 Olası AL Sinyalleri:\n" + "\n".join(signals[:30]))
else:
    send_telegram(f"{market_status}\nℹ️ Sinyal Bulunamadı.")
