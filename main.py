import ccxt
import pandas as pd
import numpy as np
import time, os, requests

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

# === TOTAL2 MARKET FİLTRESİ ===
total2 = exchange.fetch_ohlcv('TOTAL2/USDT', timeframe='1h', limit=100)
if total2:
    df = pd.DataFrame(total2, columns=['time','open','high','low','close','volume'])
    df['ema20'] = ema(df['close'], 20)
    df['ema50'] = ema(df['close'], 50)
    market_up = df['ema20'].iloc[-1] > df['ema50'].iloc[-1]
else:
    market_up = True  # yedek: veri alınamazsa engelleme yok

if not market_up:
    send_telegram("❌ Piyasa zayıf (TOTAL2 EMA20 < EMA50). Sinyal yok.")
    exit()

# === ALTCOİN SİNYALLERİ ===
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

if signals:
    send_telegram("🔥 TOTAL2 Pozitif — Olası AL Sinyalleri:\n" + "\n".join(signals[:30]))
else:
    send_telegram("ℹ️ TOTAL2 Pozitif ama güçlü altcoin sinyali bulunamadı.")
