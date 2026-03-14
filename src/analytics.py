import numpy as np

# Returns one value: the 60-day annualized volatility
def compute_60d_vol(yfin_client, symbol: str):
    # 1 year daily closes
    df = yfin_client.history_close(symbol, period="1y", interval="1d")

    if df is None or df.empty:
        raise ValueError("No historical data returned")

    df = df.copy()
    # Calculate log returns and 60-day annualized volatility
    df["log_ret"] = np.log(df["Close"] / df["Close"].shift(1))
    df["vol_60_ann"] = df["log_ret"].rolling(60).std() * np.sqrt(252)

    print(df.head())
    print(df.tail())
    print(df.dtypes)   

    latest = df["vol_60_ann"].dropna().iloc[-1]
    return float(latest)

# Returns a DataFrame with 60-day annualized volatility - Rolling
def compute_60d_vol_series(yfin_client, symbol: str, period="1y", window=60):
    df = yfin_client.history_close(symbol, period=period, interval="1d")
    if df is None or df.empty:
        raise ValueError("No historical data returned")

    df = df.copy()

    # log returns
    df["log_ret"] = np.log(df["Close"] / df["Close"].shift(1))
    df["vol_60_ann"] = df["log_ret"].rolling(window).std() * np.sqrt(252)

    # drop rows that don't have 60 days yet
    df = df.dropna()  

    return df  
