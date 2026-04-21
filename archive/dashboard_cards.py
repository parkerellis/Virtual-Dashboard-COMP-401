import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from matplotlib.animation import FuncAnimation
from matplotlib.collections import LineCollection

from src.config import get_settings
from src.clients import YFinanceClient
from src.db_storage import MariaDBStore, DBConfig
from src.analytics import compute_60d_vol, build_stock_card_data

Z_LIM = 4.0
LIVE_POINTS = 20

BASE_LINE_COLOR = "black"
Z2_COLOR = "#2ca02c"   # green
Z3_COLOR = "#d62728"   # red

THRESHOLD_2 = 2.0
THRESHOLD_3 = 3.0


def plot_price_line(ax, x, y, linewidth=2.6):
    ax.plot(x, y, color=BASE_LINE_COLOR, linewidth=linewidth, zorder=3)


def plot_z_threshold_line(ax, x, y, linewidth=3.0, n_sub=40):
    """
    Black by default.
    Green only where |z| is between 2 and 3.
    Red only where |z| is >= 3.
    """
    if len(x) < 2 or len(y) < 2:
        ax.plot(x, y, color=BASE_LINE_COLOR, linewidth=linewidth, zorder=3)
        return

    x_num = mdates.date2num(x)
    all_segments = []
    all_colors = []

    for i in range(len(y) - 1):
        x0, x1 = x_num[i], x_num[i + 1]
        y0, y1 = float(y[i]), float(y[i + 1])

        ts = np.linspace(0.0, 1.0, n_sub + 1)

        for j in range(n_sub):
            t0, t1 = ts[j], ts[j + 1]

            xs0 = x0 + (x1 - x0) * t0
            xs1 = x0 + (x1 - x0) * t1
            ys0 = y0 + (y1 - y0) * t0
            ys1 = y0 + (y1 - y0) * t1

            y_mid = 0.5 * (ys0 + ys1)
            ay = abs(y_mid)

            if ay >= THRESHOLD_3:
                color = Z3_COLOR
            elif ay >= THRESHOLD_2:
                color = Z2_COLOR
            else:
                color = BASE_LINE_COLOR

            all_segments.append([[xs0, ys0], [xs1, ys1]])
            all_colors.append(color)

    lc = LineCollection(
        all_segments,
        colors=all_colors,
        linewidths=linewidth,
        capstyle="round",
        joinstyle="round",
        zorder=3,
    )
    ax.add_collection(lc)
    ax.autoscale_view()


def classify_z_point_color(z: float):
    az = abs(float(z))
    if az >= THRESHOLD_3:
        return Z3_COLOR
    if az >= THRESHOLD_2:
        return Z2_COLOR
    return BASE_LINE_COLOR

def draw_stock_card(fig, outer_spec, card_data):
    inner = outer_spec.subgridspec(2, 1, height_ratios=[1.0, 1.0], hspace=0.10)

    ax_price = fig.add_subplot(inner[0, 0])
    ax_z = fig.add_subplot(inner[1, 0])

    symbol = card_data["symbol"]
    hist_vol_ann = card_data["hist_vol_ann"]
    latest_price = card_data["latest_price"]
    latest_z = card_data["latest_z"]
    status = card_data["status"]
    df = card_data["df"]

    for ax in (ax_price, ax_z):
        ax.set_facecolor("white")
        for spine in ax.spines.values():
            spine.set_color("#d9d9d9")
            spine.set_linewidth(0.9)
        ax.grid(True, alpha=0.12, linewidth=0.8)

    if df.empty or len(df) < 2:
        ax_price.text(
            0.02, 1.03, f"{symbol}",
            transform=ax_price.transAxes,
            ha="left", va="bottom",
            fontsize=12, fontweight="bold"
        )
        ax_price.text(
            0.5, 0.5, "Waiting for more snapshots...",
            ha="center", va="center", transform=ax_price.transAxes, fontsize=10
        )
        ax_z.text(
            0.5, 0.5, "No z-score yet",
            ha="center", va="center", transform=ax_z.transAxes, fontsize=10
        )
        ax_price.set_xticks([])
        ax_price.set_yticks([])
        ax_z.set_xticks([])
        ax_z.set_yticks([])
        return

    xvals = df["fetched_at"]
    prices = df["price"].to_numpy()
    zvals = df["z"].to_numpy()

    latest_price_text = f"{latest_price:.2f}" if latest_price is not None else "NA"
    latest_z_text = f"{latest_z:.2f}" if latest_z is not None else "NA"

    # Card header text
    ax_price.text(
        0.01, 1.03,
        f"{symbol}  |  {latest_price_text}",
        transform=ax_price.transAxes,
        ha="left", va="bottom",
        fontsize=12, fontweight="bold"
    )
    ax_price.text(
        0.99, 1.03,
        f"60D Vol {hist_vol_ann:.1%}   z {latest_z_text}   {status}",
        transform=ax_price.transAxes,
        ha="right", va="bottom",
        fontsize=10
    )

        # Top: live price
    plot_price_line(ax_price, xvals, prices, linewidth=2.4)
    ax_price.scatter(
        xvals.iloc[-1],
        prices[-1],
        s=28,
        color="black",
        zorder=4,
    )

    # Bottom: z-score / live move
    ax_z.axhline(0, color="#8c8c8c", linewidth=1.0, alpha=0.65)

    ax_z.axhline(THRESHOLD_2, color="black", linestyle="--", linewidth=1.5, alpha=0.8)
    ax_z.axhline(-THRESHOLD_2, color="black", linestyle="--", linewidth=1.5, alpha=0.8)

    ax_z.axhline(THRESHOLD_3, color="black", linestyle=":", linewidth=2.0, alpha=0.5)
    ax_z.axhline(-THRESHOLD_3, color="black", linestyle=":", linewidth=2.0, alpha=0.5)

    plot_z_threshold_line(
        ax_z,
        xvals.to_list(),
        zvals,
        linewidth=3.0,
        n_sub=40,
    )

    last_color = classify_z_point_color(float(zvals[-1]))
    ax_z.scatter(
        xvals.iloc[-1],
        zvals[-1],
        s=42,
        color=last_color,
        edgecolor="white",
        linewidth=0.6,
        zorder=4,
    )

    ax_z.set_ylim(-Z_LIM, Z_LIM)
    ax_z.set_ylabel("z", fontsize=9)

    # shared x formatting
    x_min = xvals.min()
    x_max = xvals.max()

    ax_price.set_xlim(x_min, x_max)
    ax_z.set_xlim(x_min, x_max)

    live_ticks = np.linspace(mdates.date2num(x_min), mdates.date2num(x_max), 4)
    live_ticks = mdates.num2date(live_ticks)

    ax_price.set_xticks(live_ticks)
    ax_z.set_xticks(live_ticks)

    formatter = mdates.DateFormatter("%m-%d\n%H:%M")
    ax_price.xaxis.set_major_formatter(formatter)
    ax_z.xaxis.set_major_formatter(formatter)

    # Hide top chart x labels for cleaner card look
    ax_price.tick_params(axis="x", labelbottom=False)
    ax_price.tick_params(axis="y", labelsize=8)
    ax_z.tick_params(axis="x", labelsize=8)
    ax_z.tick_params(axis="y", labelsize=8)


def main():
    s = get_settings()

    store = MariaDBStore(DBConfig(
        host=s.db_host,
        port=s.db_port,
        name=s.db_name,
        user=s.db_user,
        password=s.db_pass,
    ))

    yfin = YFinanceClient()
    symbols = list(s.snapshot_symbols)

    print("dashboard card symbols:", symbols)

    hist_vol_ann = {}
    for symbol in symbols:
        hist_vol_ann[symbol] = compute_60d_vol(yfin, symbol)

    n = len(symbols)
    ncols = min(4, n) if n > 0 else 1
    nrows = math.ceil(n / ncols)

    fig = plt.figure(figsize=(5.0 * ncols, 5.8 * nrows))
    fig.patch.set_facecolor("white")

    def update(_):
        fig.clear()
        outer = fig.add_gridspec(nrows, ncols, hspace=0.32, wspace=0.22)

        for idx, symbol in enumerate(symbols):
            r = idx // ncols
            c = idx % ncols

            rows = store.get_recent_snapshots(symbol, LIVE_POINTS)
            card_data = build_stock_card_data(
                symbol=symbol,
                rows=rows,
                hist_vol_ann=hist_vol_ann[symbol],
            )

            draw_stock_card(
                fig=fig,
                outer_spec=outer[r, c],
                card_data=card_data,
            )

        fig.suptitle(
            "Live Price + Live Move vs 60D Historical Volatility",
            fontsize=18,
            fontweight="bold",
            y=0.98,
        )

    ani = FuncAnimation(
        fig,
        update,
        interval=s.quote_ttl_seconds * 1000,
        cache_frame_data=False,
    )

    plt.show()
    store.close()


if __name__ == "__main__":
    main()