from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


BG = "#0b0f14"
PANEL = "#121923"
GRID = "rgba(255,255,255,0.08)"
TEXT = "#e8edf5"
MUTED = "#94a3b8"
BLUE = "#4da3ff"
YELLOW = "#facc15"
ORANGE = "#fb923c"
RED = "#ef4444"
GREEN = "#22c55e"


def _base_layout(fig: go.Figure, height: int):
    fig.update_layout(
        template=None,
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font={"color": TEXT, "size": 12},
        margin=dict(l=18, r=8, t=8, b=18),
        height=height,
        xaxis=dict(showgrid=True, gridcolor=GRID, zeroline=False, color=MUTED),
        yaxis=dict(showgrid=True, gridcolor=GRID, zeroline=False, color=MUTED),
        showlegend=False,
    )
    return fig


def _empty_fig(title: str, height: int = 220):
    fig = go.Figure()
    fig.add_annotation(
        text=title,
        x=0.5,
        y=0.5,
        showarrow=False,
        xref="paper",
        yref="paper",
        font=dict(color=MUTED, size=13),
    )
    return _base_layout(fig, height)


def _latest_color(z_value: float | None) -> str:
    if z_value is None:
        return BLUE
    az = abs(float(z_value))
    if az >= 3:
        return RED
    if az >= 2:
        return ORANGE
    if az >= 1:
        return YELLOW
    return BLUE


def _price_range_with_padding(price_series: pd.Series) -> tuple[float, float] | None:
    if price_series is None or price_series.empty:
        return None

    y = pd.to_numeric(price_series, errors="coerce").dropna()
    if y.empty:
        return None

    y_min = float(y.min())
    y_max = float(y.max())

    if y_min == y_max:
        pad = max(abs(y_min) * 0.003, 0.25)
    else:
        pad = max((y_max - y_min) * 0.15, abs(y_max) * 0.0025, 0.10)

    return (y_min - pad, y_max + pad)


def make_price_mini_fig(df: pd.DataFrame, symbol: str):
    if df is None or df.empty:
        return _empty_fig(f"{symbol}: waiting for live data", height=180)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["fetched_at"],
            y=df["price"],
            mode="lines",
            line=dict(color=BLUE, width=2),
            hovertemplate="%{x}<br>Price %{y:.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[df["fetched_at"].iloc[-1]],
            y=[df["price"].iloc[-1]],
            mode="markers",
            marker=dict(size=7, color=BLUE),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    y_range = _price_range_with_padding(df["price"])

    _base_layout(fig, 200)
    fig.update_layout(margin=dict(l=10, r=4, t=4, b=14))
    fig.update_xaxes(showticklabels=False)
    fig.update_yaxes(nticks=4)

    if y_range is not None:
        fig.update_yaxes(range=list(y_range), tickformat=",.2f")

    return fig


def _add_threshold_segment_traces(fig: go.Figure, x, y, threshold=2.0):
    x_vals = list(x)
    y_vals = list(y)

    for i in range(len(y_vals) - 1):
        x0, x1 = x_vals[i], x_vals[i + 1]
        y0, y1 = y_vals[i], y_vals[i + 1]

        if pd.isna(y0) or pd.isna(y1):
            continue

        if abs(y0) < threshold and abs(y1) < threshold:
            fig.add_trace(go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                mode="lines",
                line=dict(color=BLUE, width=2.6),
                hoverinfo="skip",
                showlegend=False,
            ))
            continue

        if abs(y0) >= threshold and abs(y1) >= threshold:
            fig.add_trace(go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                mode="lines",
                line=dict(color=YELLOW, width=2.6),
                hoverinfo="skip",
                showlegend=False,
            ))
            continue

        if y0 < threshold and y1 >= threshold:
            thresh = threshold
        elif y0 > -threshold and y1 <= -threshold:
            thresh = -threshold
        elif y0 >= threshold and y1 < threshold:
            thresh = threshold
        elif y0 <= -threshold and y1 > -threshold:
            thresh = -threshold
        else:
            continue

        t = (thresh - y0) / (y1 - y0)
        x_mid = x0 + (x1 - x0) * t
        y_mid = thresh

        fig.add_trace(go.Scatter(
            x=[x0, x_mid],
            y=[y0, y_mid],
            mode="lines",
            line=dict(color=BLUE if abs(y0) < threshold else YELLOW, width=2.6),
            hoverinfo="skip",
            showlegend=False,
        ))

        fig.add_trace(go.Scatter(
            x=[x_mid, x1],
            y=[y_mid, y1],
            mode="lines",
            line=dict(color=YELLOW if abs(y1) >= threshold else BLUE, width=2.6),
            hoverinfo="skip",
            showlegend=False,
        ))


def make_z_mini_fig(df: pd.DataFrame, symbol: str):
    if df is None or df.empty or df["z"].dropna().empty:
        return _empty_fig(f"{symbol}: no z-score yet", height=180)

    z = df["z"]
    x = df["fetched_at"]

    latest_z = float(z.dropna().iloc[-1]) if not z.dropna().empty else None
    latest_color = YELLOW if (latest_z is not None and abs(latest_z) >= 2) else BLUE

    fig = go.Figure()
    fig.add_hline(y=0, line_width=1, line_color="rgba(255,255,255,0.30)")
    fig.add_hline(y=2, line_width=1, line_dash="dash", line_color=ORANGE)
    fig.add_hline(y=-2, line_width=1, line_dash="dash", line_color=ORANGE)
    fig.add_hline(y=3, line_width=1, line_dash="dot", line_color=RED)
    fig.add_hline(y=-3, line_width=1, line_dash="dot", line_color=RED)

    _add_threshold_segment_traces(fig, x, z, threshold=2.0)

    fig.add_trace(
        go.Scatter(
            x=[x.iloc[-1]],
            y=[z.iloc[-1]],
            mode="markers",
            marker=dict(size=8, color=latest_color),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    _base_layout(fig, 200)
    fig.update_layout(margin=dict(l=10, r=4, t=4, b=14))
    fig.update_xaxes(showticklabels=False)
    fig.update_yaxes(range=[-4, 4], nticks=5)
    return fig


def make_detail_live_price_fig(df: pd.DataFrame, symbol: str):
    if df is None or df.empty:
        return _empty_fig(f"{symbol}: waiting for live data", height=320)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["fetched_at"],
            y=df["price"],
            mode="lines",
            line=dict(color=BLUE, width=2.8),
            hovertemplate="%{x}<br>Price %{y:.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[df["fetched_at"].iloc[-1]],
            y=[df["price"].iloc[-1]],
            mode="markers",
            marker=dict(size=8, color=BLUE),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    y_range = _price_range_with_padding(df["price"])

    _base_layout(fig, 320)
    fig.update_layout(
        title=None,
        margin=dict(l=56, r=14, t=8, b=36),
    )
    fig.update_xaxes(
        tickformat="%H:%M",
        nticks=6,
    )
    fig.update_yaxes(
        tickformat=",.2f",
        nticks=6,
    )

    if y_range is not None:
        fig.update_yaxes(range=list(y_range))

    return fig


def make_detail_live_z_fig(df: pd.DataFrame, symbol: str):
    if df is None or df.empty or df["z"].dropna().empty:
        return _empty_fig(f"{symbol}: no z-score yet", height=320)

    z = df["z"]
    x = df["fetched_at"]

    latest_z = float(z.dropna().iloc[-1]) if not z.dropna().empty else None
    latest_color = YELLOW if (latest_z is not None and abs(latest_z) >= 2) else BLUE

    fig = go.Figure()
    fig.add_hrect(y0=2, y1=3, fillcolor="rgba(251,146,60,0.08)", line_width=0)
    fig.add_hrect(y0=-3, y1=-2, fillcolor="rgba(251,146,60,0.08)", line_width=0)
    fig.add_hrect(y0=3, y1=4, fillcolor="rgba(239,68,68,0.08)", line_width=0)
    fig.add_hrect(y0=-4, y1=-3, fillcolor="rgba(239,68,68,0.08)", line_width=0)
    fig.add_hline(y=0, line_width=1, line_color="rgba(255,255,255,0.35)")
    fig.add_hline(y=2, line_width=1, line_dash="dash", line_color=ORANGE)
    fig.add_hline(y=-2, line_width=1, line_dash="dash", line_color=ORANGE)
    fig.add_hline(y=3, line_width=1, line_dash="dot", line_color=RED)
    fig.add_hline(y=-3, line_width=1, line_dash="dot", line_color=RED)

    _add_threshold_segment_traces(fig, x, z, threshold=2.0)

    fig.add_trace(
        go.Scatter(
            x=[x.iloc[-1]],
            y=[z.iloc[-1]],
            mode="markers",
            marker=dict(size=9, color=latest_color),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    _base_layout(fig, 320)
    fig.update_layout(margin=dict(l=56, r=14, t=8, b=36))
    fig.update_xaxes(tickformat="%H:%M", nticks=6)
    fig.update_yaxes(range=[-4, 4], nticks=7)
    return fig


def make_hist_vol_fig(hist_df: pd.DataFrame, symbol: str):
    if hist_df is None or hist_df.empty or "vol_60_ann" not in hist_df.columns:
        return _empty_fig(f"{symbol}: no historical vol yet", height=360)

    x = hist_df.index if hist_df.index.name is not None or hist_df.index.dtype != object else hist_df["Date"]
    y = hist_df["vol_60_ann"] * 100.0

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            line=dict(color=GREEN, width=2.6),
            hovertemplate="%{x}<br>60D vol %{y:.2f}%<extra></extra>",
        )
    )
    _base_layout(fig, 360)
    fig.update_yaxes(title="Percent")
    return fig