import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

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

    symbols = list(s.snapshot_symbols)
    print("symbols:", symbols)

    # historical baseline for each symbol
    hist_vol_ann = {}
    vol_day = {}
    hist_series = {}

    for symbol in symbols:
        hist_vol_ann[symbol] = compute_60d_vol(ingest.yfin, symbol)
        vol_day[symbol] = hist_vol_ann[symbol] / math.sqrt(252)
        hist_series[symbol] = compute_60d_vol_series(ingest.yfin, symbol)

    fig, axes = plt.subplots(3, len(symbols), figsize=(4 * len(symbols), 10), squeeze=False)

    # Update live stock data and replot
    def update(_):
        for i, symbol in enumerate(symbols):
            rows = store.get_recent_snapshots(symbol, 10)
            if len(rows) < 2:
                continue

            df = pd.DataFrame(rows)
            df["fetched_at"] = pd.to_datetime(df["fetched_at"])

            df["price"] = pd.to_numeric(df["price"], errors="coerce")
            df = df.dropna(subset=["price"])

            df["log_ret"] = np.log(df["price"] / df["price"].shift(1))

            # compute delta time
            df["dt_days"] = df["fetched_at"].diff().dt.total_seconds() / 86400
            df["sigma_dt"] = vol_day[symbol] * np.sqrt(df["dt_days"])
            df["z"] = df["log_ret"] / df["sigma_dt"]

            ax_price = axes[0, i]
            ax_z = axes[1, i]
            ax_histvol = axes[2, i]

            ax_price.clear()
            ax_z.clear()
            ax_histvol.clear()

            xvals = df["fetched_at"]

            ax_price.plot(xvals, df["price"])
            ax_price.set_title(f"{symbol} Live Price — 60D Vol={hist_vol_ann[symbol]:.2%}")
            ax_price.grid(True)

            ax_z.plot(xvals, df["z"])
            ax_z.axhline(2, linestyle="--")
            ax_z.axhline(-2, linestyle="--")
            ax_z.axhline(3, linestyle=":")
            ax_z.axhline(-3, linestyle=":")
            ax_z.set_title("Live Move vs 60D Historical Vol (z-score)")
            ax_z.grid(True)

            series_df = hist_series[symbol]

            ax_histvol.plot(series_df.index, series_df["vol_60_ann"])
            ax_histvol.set_title("YFinance: 60-Day Rolling Volatility (Annualized)")
            ax_histvol.set_ylabel("Vol")
            ax_histvol.grid(True)

            # force  same x-axis range
            x_min = xvals.min()
            x_max = xvals.max()
            ax_price.set_xlim(x_min, x_max)
            ax_z.set_xlim(x_min, x_max)

            # force tick locations on both live plots with artificial timestamps
            live_ticks = pd.date_range(start=x_min, end=x_max, periods=5)
            ax_price.set_xticks(live_ticks)
            ax_z.set_xticks(live_ticks)
            
            #Real timestamps:
            #n = len(xvals)
            #tick_idx = np.linspace(0, n - 1, 5).astype(int)
            #live_ticks = xvals.iloc[tick_idx]

            #ax_price.set_xticks(live_ticks)
            #ax_z.set_xticks(live_ticks)

            # same formatter on both
            live_formatter = mdates.DateFormatter("%m-%d\n%H:%M")
            ax_price.xaxis.set_major_formatter(live_formatter)
            ax_z.xaxis.set_major_formatter(live_formatter)

            ax_price.tick_params(axis="x")
            ax_z.tick_params(axis="x")



        plt.tight_layout()

    ani = FuncAnimation(fig, update, interval=s.quote_ttl_seconds * 1000)
    plt.show()


if __name__ == "__main__":
    main()
