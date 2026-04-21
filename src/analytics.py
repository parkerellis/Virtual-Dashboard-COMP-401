import math
import numpy as np
import pandas as pd


# Returns one value: the 60-day annualized volatility
def compute_60d_vol(yfin_client, symbol: str):
    df = yfin_client.history_close(symbol, period="1y", interval="1d")

    if df is None or df.empty:
        raise ValueError(f"No historical data returned for {symbol}")

    df = df.copy()
    df["log_ret"] = np.log(df["Close"] / df["Close"].shift(1))
    df["vol_60_ann"] = df["log_ret"].rolling(60).std() * np.sqrt(252)

    latest = df["vol_60_ann"].dropna().iloc[-1]
    return float(latest)


# Returns a DataFrame with 60-day annualized volatility rolling series
def compute_60d_vol_series(yfin_client, symbol: str, period="1y", window=60):
    df = yfin_client.history_close(symbol, period=period, interval="1d")

    if df is None or df.empty:
        raise ValueError(f"No historical data returned for {symbol}")

    df = df.copy()
    df["log_ret"] = np.log(df["Close"] / df["Close"].shift(1))
    df["vol_60_ann"] = df["log_ret"].rolling(window).std() * np.sqrt(252)
    df = df.dropna()

    return df

# Returns a time-sorted DataFrame.
def prepare_live_price_df(rows):
    if not rows:
        return pd.DataFrame(columns=["fetched_at", "price"])

    df = pd.DataFrame(rows).copy()

    if "fetched_at" not in df.columns or "price" not in df.columns:
        return pd.DataFrame(columns=["fetched_at", "price"])

    df["fetched_at"] = pd.to_datetime(df["fetched_at"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    df = df.dropna(subset=["fetched_at", "price"])
    df = df.sort_values("fetched_at").reset_index(drop=True)

    return df


"""
Given a DataFrame with columns:
- fetched_at
- price

and a daily volatility estimate vol_day,
returns a copy with:
- log_ret
- dt_days
- sigma_dt
- z
"""
def compute_live_z_series(df, vol_day: float, min_dt_days: float = 1e-8):
    out = df.copy()

    if out.empty:
        out["log_ret"] = pd.Series(dtype=float)
        out["dt_days"] = pd.Series(dtype=float)
        out["sigma_dt"] = pd.Series(dtype=float)
        out["z"] = pd.Series(dtype=float)
        return out

    out["log_ret"] = np.log(out["price"] / out["price"].shift(1))
    out["dt_days"] = out["fetched_at"].diff().dt.total_seconds() / 86400.0

    # avoid divide-by-zero or sqrt of non-positive values
    out["dt_days"] = out["dt_days"].clip(lower=min_dt_days)

    out["sigma_dt"] = vol_day * np.sqrt(out["dt_days"])
    out["z"] = out["log_ret"] / out["sigma_dt"]

    return out


def classify_zscore(z: float | None):
    """
    Status labels for the latest z-score.
    Based on abs z-score.
    """
    if z is None or pd.isna(z):
        return "No signal"

    az = abs(float(z))

    if az >= 3.0:
        return "Extreme"
    if az >= 2.0:
        return "Elevated"
    return "Normal"


"""
Builds one reusable stock-card

Returns a dict with:
    symbol
    hist_vol_ann
    vol_day
    latest_price
    latest_z
    status
    df   (contains fetched_at, price, z, etc.)
"""
def build_stock_card_data(symbol: str, rows, hist_vol_ann: float):
    vol_day = hist_vol_ann / math.sqrt(252)

    df = prepare_live_price_df(rows)
    df = compute_live_z_series(df, vol_day)

    latest_price = None
    latest_z = None

    if not df.empty:
        latest_price = float(df["price"].iloc[-1])

        z_non_null = df["z"].dropna()
        if not z_non_null.empty:
            latest_z = float(z_non_null.iloc[-1])

    return {
        "symbol": symbol,
        "hist_vol_ann": float(hist_vol_ann),
        "vol_day": float(vol_day),
        "latest_price": latest_price,
        "latest_z": latest_z,
        "status": classify_zscore(latest_z),
        "df": df,
    }