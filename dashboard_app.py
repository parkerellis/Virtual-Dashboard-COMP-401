from dash import Dash, dcc, html, Input, Output

from src.config import get_settings
from src.dashboard_data import build_dashboard_snapshot, build_symbol_detail
from src.dashboard_charts import (
    make_detail_live_price_fig,
    make_detail_live_z_fig,
    make_hist_vol_fig,
    make_price_mini_fig,
    make_z_mini_fig,
)


s = get_settings()
app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Live Vol Dashboard"
server = app.server


REFRESH_MS = max(1000, s.quote_ttl_seconds * 1000)
CARD_LIVE_POINTS = 40
DETAIL_LIVE_POINTS = 160


def stat_chip(label: str, value: str, tone: str = "normal"):
    return html.Div(
        className=f"stat-chip stat-{tone}",
        children=[
            html.Div(label, className="stat-label"),
            html.Div(value, className="stat-value"),
        ],
    )


def format_price(x):
    return "--" if x is None else f"{x:,.2f}"


def format_pct(x):
    return "--" if x is None else f"{x:+.2f}%"


def format_vol(x):
    return "--" if x is None else f"{100.0 * x:.2f}%"


def tone_from_status(status: str) -> str:
    status = (status or "").lower()
    if status == "extreme":
        return "danger"
    if status == "elevated":
        return "warn"
    if status == "normal":
        return "ok"
    return "muted"


def render_home_page():
    snapshot = build_dashboard_snapshot(live_points=CARD_LIVE_POINTS)

    cards = []
    for card in snapshot["cards"]:
        symbol = card["symbol"]
        tone = tone_from_status(card["status"])

        cards.append(
            html.A(
                href=f"/symbol/{symbol}",
                className="card-link",
                children=html.Div(
                    className="ticker-card",
                    children=[
                        html.Div(
                            className="card-header",
                            children=[
                                html.Div(symbol, className="ticker-symbol"),
                                html.Div(card["status"], className=f"status-badge status-{tone}"),
                            ],
                        ),
                        html.Div(
                            className="price-row",
                            children=[
                                html.Div(format_price(card["latest_price"]), className="big-price"),
                                html.Div(format_pct(card["pct_change"]), className="pct-change"),
                            ],
                        ),
                        html.Div(
                            className="chips-row",
                            children=[
                                stat_chip("z", "--" if card["latest_z"] is None else f"{card['latest_z']:.2f}", tone),
                                stat_chip("60D vol", format_vol(card["hist_vol_ann"])),
                                stat_chip("pts", str(card["live_points"])),
                            ],
                        ),
                        dcc.Graph(
                            figure=make_price_mini_fig(card["df"], symbol),
                            config={"displayModeBar": False},
                            className="mini-graph",
                        ),
                        dcc.Graph(
                            figure=make_z_mini_fig(card["df"], symbol),
                            config={"displayModeBar": False},
                            className="mini-graph",
                        ),
                        html.Div(
                            className="card-footer",
                            children=[
                                html.Span(card["last_timestamp_text"]),
                                html.Span("Open detail view"),
                            ],
                        ),
                    ],
                ),
            )
        )

    return html.Div(
        className="page-shell",
        children=[
            html.Div(
                className="topbar",
                children=[
                    html.Div(
                        children=[
                            html.Div("COMP 401 - Live Financial Dashboard", className="app-title"),
                            html.Div(
                                "Standardizing live price moves relative to historical volatility using a z-score framework",
                                className="app-subtitle",
                            ),
                        ]
                    ),
                    html.Div(
                        className="topbar-right",
                        children=[
                            html.Div(f"Symbols: {', '.join(snapshot['symbols'])}", className="topbar-meta"),
                            html.Div(f"Ingest: every {s.snapshot_every_seconds}s", className="topbar-meta"),
                            html.Div(f"UI refresh: {s.quote_ttl_seconds}s", className="topbar-meta"),
                            html.Div(f"Updated: {snapshot['generated_at_text']}", className="topbar-meta"),
                        ],
                    ),
                ],
            ),
            html.Div(className="cards-grid", children=cards),
        ],
    )



def render_detail_page(symbol: str):
    detail = build_symbol_detail(symbol, live_points=DETAIL_LIVE_POINTS)
    card = detail["card"]
    tone = tone_from_status(card["status"])

    return html.Div(
        className="page-shell",
        children=[
            html.Div(
                className="topbar",
                children=[
                    html.Div(
                        children=[
                            html.A("← Back to dashboard", href="/", className="back-link"),
                            html.Div(f"{symbol} Detail", className="app-title"),
                            html.Div("Expanded live and historical view", className="app-subtitle"),
                        ]
                    ),
                    html.Div(
                        className="topbar-right",
                        children=[
                            html.Div(f"Updated: {detail['generated_at_text']}", className="topbar-meta"),
                            html.Div(card["last_timestamp_text"], className="topbar-meta"),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="detail-summary-row",
                children=[
                    stat_chip("Last price", format_price(card["latest_price"])),
                    stat_chip("Day change", format_pct(card["pct_change"])),
                    stat_chip("Signal", card["status"], tone),
                    stat_chip("Latest z", "--" if card["latest_z"] is None else f"{card['latest_z']:.2f}", tone),
                    stat_chip("60D vol", format_vol(card["hist_vol_ann"])),
                    stat_chip("Recent abs max z", "--" if detail["max_abs_z"] is None else f"{detail['max_abs_z']:.2f}"),
                ],
            ),
            html.Div(
                className="detail-grid",
                children=[
                    html.Div(
                        className="panel",
                        children=[
                            html.Div("Live price", className="panel-title"),
                            dcc.Graph(
                                figure=make_detail_live_price_fig(card["df"], symbol),
                                config={"displayModeBar": False},
                            ),
                        ],
                    ),
                    html.Div(
                        className="panel",
                        children=[
                            html.Div("Live z-score", className="panel-title"),
                            dcc.Graph(
                                figure=make_detail_live_z_fig(card["df"], symbol),
                                config={"displayModeBar": False},
                            ),
                        ],
                    ),
                    html.Div(
                        className="panel panel-wide",
                        children=[
                            html.Div("Historical 60D annualized volatility", className="panel-title"),
                            dcc.Graph(
                                figure=make_hist_vol_fig(detail["hist_df"], symbol),
                                config={"displayModeBar": False},
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


app.layout = html.Div(
    children=[
        dcc.Location(id="url", refresh=False),
        dcc.Interval(id="refresh", interval=REFRESH_MS, n_intervals=0),
        html.Div(id="page-content"),
    ]
)


@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
    Input("refresh", "n_intervals"),
)
def render_page(pathname, _n):
    pathname = pathname or "/"

    if pathname == "/":
        return render_home_page()

    if pathname.startswith("/symbol/"):
        symbol = pathname.split("/symbol/", 1)[1].strip().upper()
        if symbol: 
            return render_detail_page(symbol)

    return html.Div(
        className="page-shell",
        children=[
            html.A("← Back to dashboard", href="/", className="back-link"),
            html.Div("Page not found", className="app-title"),
        ],
    )


if __name__ == "__main__":
    app.run(debug=True)
