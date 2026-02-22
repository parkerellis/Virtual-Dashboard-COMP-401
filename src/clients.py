import finnhub
import yfinance as yf

class FinnhubClient:
    def __init__(self, api_key: str):
        self._client = finnhub.Client(api_key=api_key)

    def quote(self, symbol: str) -> dict:
        q = self._client.quote(symbol)
        # Finnhub keys: c, d, dp, h, l, o, pc, t
        return {
            "symbol": symbol,
            "price": q.get("c"),
            "change": q.get("d"),
            "pct_change": q.get("dp"),
            "timestamp_unix": q.get("t"),
        }

class YFinanceClient:
    def history_close(self, symbol: str, period="6mo", interval="1d"):
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        return df[["Close"]].dropna()
