from datetime import datetime, timezone


#Text file storage (OLD)
def append_snapshot(
    path: str,
    symbol: str,
    price,
    change,
    pct_change,
    fetched_at_unix: float | None,
):
    now_time = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    fetched_time = (
        datetime.fromtimestamp(fetched_at_unix, tz=timezone.utc)
        .strftime("%Y-%m-%d %H:%M:%S UTC")
        if fetched_at_unix is not None
        else "N/A"
    )

    line = (
        f"{now_time}  {symbol}  "
        f"price={price}  change={change} ({pct_change}%)  "
        f"fetched_at_unix={fetched_at_unix}  fetched_at_realtime={fetched_time}\n"
    )

    with open(path, "a", encoding="utf-8") as f:
        f.write(line)

    return line.strip()


def unix_to_time(ts: float | int | None) -> str:
    if ts is None:
        return "N/A"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
