import numpy as np
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from src.config import get_settings
from src.clients import YFinanceClient
from src.db_storage import MariaDBStore, DBConfig
from src.analytics import compute_60d_vol, build_stock_card_data


SYMBOL = "XOM"

THRESHOLD_2 = 2.0
THRESHOLD_3 = 3.0
Z_LIM = 4.0
LIVE_POINTS = 20
AUTO_REFRESH_SECONDS = 10


def densify_series(x, y, n_sub=40):
    x = pd.to_datetime(x)
    y = np.asarray(y, dtype=float)

    if len(x) < 2 or len(y) < 2:
        return x, y

    x_out = []
    y_out = []

    for i in range(len(y) - 1):
        x0 = x.iloc[i]
        x1 = x.iloc[i + 1]
        y0 = y[i]
        y1 = y[i + 1]

        ts = np.linspace(0.0, 1.0, n_sub + 1)

        for j, t in enumerate(ts):
            if i > 0 and j == 0:
                continue

            xt = x0 + (x1 - x0) * t
            yt = y0 + (y1 - y0) * t

            x_out.append(xt)
            y_out.append(yt)

    return pd.to_datetime(x_out), np.asarray(y_out, dtype=float)


def masked_values(values, condition):
    out = np.asarray(values, dtype=float).copy()
    out[~condition] = np.nan
    return out


def latest_point_color(z):
    return "#2ca02c" if abs(float(z)) >= THRESHOLD_2 else "black"


def make_figure(card_data):
    df = card_data["df"]
    symbol = card_data["symbol"]
    hist_vol_ann = card_data["hist_vol_ann"]
    latest_price = card_data["latest_price"]
    latest_z = card_data["latest_z"]
    status = card_data["status"]

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.58, 0.42],
        vertical_spacing=0.10,
    )

    if df.empty or len(df) < 2:
        fig.update_layout(
            height=700,
            paper_bgcolor="white",
            plot_bgcolor="white",
            title=f"{symbol} | Waiting for more snapshots...",
        )
        return fig

    xvals = pd.to_datetime(df["fetched_at"])
    prices = df["price"].to_numpy(dtype=float)
    zvals = df["z"].to_numpy(dtype=float)

    latest_price_text = f"{latest_price:.2f}" if latest_price is not None else "NA"
    latest_z_text = f"{latest_z:.2f}" if latest_z is not None else "NA"

    # -------- Top panel: live price --------
    fig.add_trace(
        go.Scatter(
            x=xvals,
            y=prices,
            mode="lines",
            line=dict(color="black", width=3),
            hovertemplate="Time: %{x}<br>Price: %{y:.2f}<extra></extra>",
            showlegend=False,
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=[xvals.iloc[-1]],
            y=[prices[-1]],
            mode="markers",
            marker=dict(color="black", size=8),
            hovertemplate="Time: %{x}<br>Price: %{y:.2f}<extra></extra>",
            showlegend=False,
        ),
        row=1,
        col=1,
    )

    # -------- Bottom panel: live move / z --------
    x_dense, z_dense = densify_series(xvals, zvals, n_sub=50)
    abs_z = np.abs(z_dense)

    z_black = masked_values(z_dense, abs_z < THRESHOLD_2)
    z_green = masked_values(z_dense, abs_z >= THRESHOLD_2)

    fig.add_trace(
        go.Scatter(
            x=x_dense,
            y=z_black,
            mode="lines",
            line=dict(color="black", width=4),
            hovertemplate="Time: %{x}<br>z: %{y:.2f}<extra></extra>",
            connectgaps=False,
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=x_dense,
            y=z_green,
            mode="lines",
            line=dict(color="#2ca02c", width=4),
            hovertemplate="Time: %{x}<br>z: %{y:.2f}<extra></extra>",
            connectgaps=False,
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=[xvals.iloc[-1]],
            y=[zvals[-1]],
            mode="markers",
            marker=dict(
                color=latest_point_color(zvals[-1]),
                size=9,
                line=dict(color="white", width=1),
            ),
            hovertemplate="Time: %{x}<br>z: %{y:.2f}<extra></extra>",
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    # threshold lines
    fig.add_hline(
        y=0,
        line_color="gray",
        line_width=1.2,
        opacity=0.8,
        row=2,
        col=1,
    )

    fig.add_hline(
        y=THRESHOLD_2,
        line_color="black",
        line_dash="dash",
        line_width=1.7,
        opacity=0.9,
        row=2,
        col=1,
    )
    fig.add_hline(
        y=-THRESHOLD_2,
        line_color="black",
        line_dash="dash",
        line_width=1.7,
        opacity=0.9,
        row=2,
        col=1,
    )

    fig.add_hline(
        y=THRESHOLD_3,
        line_color="black",
        line_dash="dot",
        line_width=2.2,
        opacity=1.0,
        row=2,
        col=1,
    )
    fig.add_hline(
        y=-THRESHOLD_3,
        line_color="black",
        line_dash="dot",
        line_width=2.2,
        opacity=1.0,
        row=2,
        col=1,
    )

    fig.update_yaxes(
        title_text="Price",
        showgrid=True,
        gridcolor="rgba(0,0,0,0.08)",
        row=1,
        col=1,
    )

    fig.update_yaxes(
        title_text="z",
        range=[-Z_LIM, Z_LIM],
        showgrid=True,
        gridcolor="rgba(0,0,0,0.08)",
        row=2,
        col=1,
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(0,0,0,0.08)",
        tickformat="%m-%d\n%H:%M",
        row=2,
        col=1,
    )

    fig.update_layout(
        height=760,
        width=980,
        margin=dict(l=55, r=35, t=80, b=55),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(size=14, color="black"),
        title=(
            f"{symbol} | {latest_price_text}"
            f"<br><sup>60D Vol {hist_vol_ann:.1%} | z {latest_z_text} | {status}</sup>"
        ),
        showlegend=False,
    )

    return fig


def build_html(fig_html):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="{AUTO_REFRESH_SECONDS}">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{SYMBOL} Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 28px;
            font-family: Arial, sans-serif;
            background: white;
            color: black;
        }}

        .wrapper {{
            max-width: 1050px;
            margin: 0 auto;
        }}

        .note {{
            margin-bottom: 14px;
            color: #444;
            font-size: 14px;
        }}

        .card {{
            background: white;
            border: 1px solid #dddddd;
            border-radius: 14px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.04);
            padding: 10px 10px 0 10px;
        }}
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="note">
            Auto-refreshes every {AUTO_REFRESH_SECONDS} seconds. Uses current DB snapshots.
        </div>
        <div class="card">
            {fig_html}
        </div>
    </div>
</body>
</html>
"""


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

    hist_vol_ann = compute_60d_vol(yfin, SYMBOL)
    rows = store.get_recent_snapshots(SYMBOL, LIVE_POINTS)

    card_data = build_stock_card_data(
        symbol=SYMBOL,
        rows=rows,
        hist_vol_ann=hist_vol_ann,
    )

    fig = make_figure(card_data)

    fig_html = fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={
            "displayModeBar": True,
            "responsive": True,
        },
    )

    full_html = build_html(fig_html)

    with open("dashboard.html", "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"Wrote dashboard.html for {SYMBOL}")

    store.close()


if __name__ == "__main__":
    main()