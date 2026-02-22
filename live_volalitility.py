import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from src.config import get_settings
from src.clients import FinnhubClient, YFinanceClient
from src.cache import TTLCache
from src.ingest import IngestService
from src.db_storage import MariaDBStore, DBConfig
from src.analytics import compute_60d_vol, compute_60d_vol_series



def main():
    s = get_settings()

    ingest = IngestService(
        finnhub=FinnhubClient(s.finnhub_api_key),
        yfin=YFinanceClient(),
        cache=TTLCache(),
    )

    store = MariaDBStore(DBConfig(
        host=s.db_host,
        port=s.db_port,
        name=s.db_name,
        user=s.db_user,
        password=s.db_pass,
    ))

    symbol = "AAPL"

    # historical baseline
    hist_vol_ann = compute_60d_vol(ingest.yfin, symbol)
    vol_day = hist_vol_ann / math.sqrt(252)

    hist_series = compute_60d_vol_series(ingest.yfin, symbol) 

    fig, (ax_price, ax_z, ax_histvol) = plt.subplots(3, 1, figsize=(10, 9), sharex=False)

    def update(_):
        rows = store.get_recent_snapshots(symbol, 25)
        if len(rows) < 2:
            return

        df = pd.DataFrame(rows)
        df["fetched_at"] = pd.to_datetime(df["fetched_at"])

        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        df = df.dropna(subset=["price"])

        df["log_ret"] = np.log(df["price"] / df["price"].shift(1))

        # compute delta time
        df["dt_days"] = df["fetched_at"].diff().dt.total_seconds() / 86400
        df["sigma_dt"] = vol_day * np.sqrt(df["dt_days"])
        df["z"] = df["log_ret"] / df["sigma_dt"]

        #print(df.head())
        #print(df.tail())
        #print(df.dtypes)

        ax_price.clear()
        ax_z.clear()

        ax_price.plot(df["fetched_at"], df["price"])
        ax_price.set_title(f"{symbol} Live Price — 60D Vol={hist_vol_ann:.2%}")
        ax_price.grid(True)

        ax_z.plot(df["fetched_at"], df["z"])
        ax_z.axhline(2, linestyle="--")
        ax_z.axhline(-2, linestyle="--")
        ax_z.axhline(3, linestyle=":")
        ax_z.axhline(-3, linestyle=":")
        ax_z.set_title("Live Move vs 60D Historical Vol (z-score)")
        ax_z.grid(True)

        ax_histvol.clear()
        ax_histvol.plot(hist_series.index, hist_series["vol_60_ann"])
        ax_histvol.set_title("YFinance: 60-Day Rolling Volatility (Annualized)")
        ax_histvol.set_ylabel("Vol")
        ax_histvol.grid(True)

        plt.tight_layout()

    ani = FuncAnimation(fig, update, interval=s.quote_ttl_seconds * 1000)
    plt.show()


if __name__ == "__main__":
    main()
