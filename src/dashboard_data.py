from __future__ import annotations

from datetime import datetime
from functools import lru_cache
import math

import pandas as pd

from src.analytics import build_stock_card_data, compute_60d_vol, compute_60d_vol_series
from src.clients import YFinanceClient
from src.config import get_settings
from src.db_storage import DBConfig, MariaDBStore


SESSION_GAP_HOURS = 1.0


@lru_cache(maxsize=1)
def _settings():
    return get_settings()


@lru_cache(maxsize=1)
def _yfin_client():
    return YFinanceClient()


def _store() -> MariaDBStore:
    s = _settings()
    return MariaDBStore(
        DBConfig(
            host=s.db_host,
            port=s.db_port,
            name=s.db_name,
            user=s.db_user,
            password=s.db_pass,
        )
    )


@lru_cache(maxsize=128)
def _hist_vol_for_symbol(symbol: str) -> float:
    return compute_60d_vol(_yfin_client(), symbol)


@lru_cache(maxsize=128)
def _hist_vol_series_for_symbol(symbol: str):
    return compute_60d_vol_series(_yfin_client(), symbol, period="1y", window=60)


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "No live snapshots yet"
    return dt.strftime("Last snapshot %Y-%m-%d %H:%M:%S")


def _safe_float(value):
    if value is None:
        return None
    try:
        if math.isnan(value):
            return None
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return None


def _filter_to_latest_session(rows, gap_hours: float = SESSION_GAP_HOURS):
    if not rows:
        return []

    df = pd.DataFrame(rows).copy()

    if "fetched_at" not in df.columns:
        return rows

    df["fetched_at"] = pd.to_datetime(df["fetched_at"], errors="coerce")
    df = df.dropna(subset=["fetched_at"]).sort_values("fetched_at").reset_index(drop=True)

    if df.empty:
        return []

    gap_seconds = gap_hours * 3600.0
    dt_seconds = df["fetched_at"].diff().dt.total_seconds()

    breakpoints = dt_seconds[dt_seconds > gap_seconds].index

    if len(breakpoints) > 0:
        start_idx = int(breakpoints[-1])
        df = df.iloc[start_idx:].reset_index(drop=True)

    return df.to_dict("records")


def build_dashboard_snapshot(live_points: int = 40) -> dict:
    s = _settings()
    store = _store()
    cards = []

    try:
        for symbol in s.snapshot_symbols:
            rows = store.get_recent_snapshots(symbol, limit=live_points)
            rows = _filter_to_latest_session(rows, gap_hours=1.0)

            hist_vol_ann = _hist_vol_for_symbol(symbol)
            card = build_stock_card_data(symbol=symbol, rows=rows, hist_vol_ann=hist_vol_ann)

            latest_ts = None
            pct_change = None
            if rows:
                latest_ts = rows[-1].get("fetched_at")

            with store.conn.cursor(dictionary=True) as cur:
                cur.execute(
                    """
                    SELECT change_pct, fetched_at
                    FROM prices
                    WHERE symbol = %s
                    ORDER BY fetched_at DESC
                    LIMIT 1
                    """,
                    (symbol,),
                )
                latest_row = cur.fetchone()
                if latest_row:
                    pct_change = _safe_float(latest_row.get("change_pct"))
                    latest_ts = latest_row.get("fetched_at") or latest_ts

            card["pct_change"] = pct_change
            card["last_timestamp_text"] = _fmt_dt(latest_ts)
            card["live_points"] = 0 if card["df"] is None else len(card["df"])
            cards.append(card)
    finally:
        store.close()

    return {
        "symbols": list(s.snapshot_symbols),
        "cards": cards,
        "generated_at_text": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def build_symbol_detail(symbol: str, live_points: int = 160) -> dict:
    symbol = symbol.upper()
    store = _store()

    try:
        rows = store.get_recent_snapshots(symbol, limit=live_points)
        rows = _filter_to_latest_session(rows, gap_hours=1.0)

        latest_pct_change = None
        latest_ts = None
        with store.conn.cursor(dictionary=True) as cur:
            cur.execute(
                """
                SELECT change_pct, fetched_at
                FROM prices
                WHERE symbol = %s
                ORDER BY fetched_at DESC
                LIMIT 1
                """,
                (symbol,),
            )
            latest_row = cur.fetchone()
            if latest_row:
                latest_pct_change = _safe_float(latest_row.get("change_pct"))
                latest_ts = latest_row.get("fetched_at")
    finally:
        store.close()

    hist_vol_ann = _hist_vol_for_symbol(symbol)
    hist_df = _hist_vol_series_for_symbol(symbol).copy()
    card = build_stock_card_data(symbol=symbol, rows=rows, hist_vol_ann=hist_vol_ann)
    card["pct_change"] = latest_pct_change
    card["last_timestamp_text"] = _fmt_dt(latest_ts)

    z_non_null = card["df"]["z"].dropna() if not card["df"].empty else None
    max_abs_z = None
    if z_non_null is not None and not z_non_null.empty:
        max_abs_z = float(z_non_null.abs().max())

    return {
        "symbol": symbol,
        "card": card,
        "hist_df": hist_df,
        "max_abs_z": max_abs_z,
        "generated_at_text": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }