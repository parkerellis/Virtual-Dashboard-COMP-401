import time

from src import ingest
from src.db_storage import MariaDBStore, DBConfig
from src.config import get_settings
from src.clients import FinnhubClient, YFinanceClient
from src.cache import TTLCache
from src.ingest import IngestService
from src.storage import append_snapshot, unix_to_time
from src.analytics import compute_60d_vol

#Writes oruce snapshot to DB
def write_snapshot_batch(ingest: IngestService, store: MariaDBStore, s):
    for sym in s.snapshot_symbols:
        quote_res = ingest.get_quote(sym, ttl_seconds=s.quote_ttl_seconds)
        print(
            "QUOTE:",
            sym,
            quote_res.source,
            "last_updated=",
            unix_to_time(quote_res.last_updated_unix),
            "error=",
            quote_res.error,
        )

        #API fail fallback
        if quote_res.error or not quote_res.data:
            continue

        q = quote_res.data

        #DB snapshot
        store.upsert_snapshot(
            symbol=q["symbol"],
            price=q["price"],
            change=q["change"],
            pct_change=q["pct_change"],
            fetched_at_unix=q["timestamp_unix"],
        )
        print("DB SNAPSHOT WROTE:", q["symbol"])

def main():
    s = get_settings()

    store = MariaDBStore(
    DBConfig(
        host=s.db_host,
        port=s.db_port,
        name=s.db_name,
        user=s.db_user,
        password=s.db_pass,
        )
    )
    cache = TTLCache()

    ingest = IngestService(
        finnhub=FinnhubClient(s.finnhub_api_key),
        yfin=YFinanceClient(),
        cache=cache,
    )

    # 1) Live quote with TTL 
    quote_res = ingest.get_quote("AAPL", ttl_seconds=s.quote_ttl_seconds)
    print("QUOTE:", quote_res.source, "last_updated=", unix_to_time(quote_res.last_updated_unix), "error=", quote_res.error)
    print(quote_res.data)

    # 2) Historical closes with longer TTL
    hist_res = ingest.get_history_close("AAPL", period="6mo", interval="1d", ttl_seconds=s.history_ttl_seconds)
    print("\nHISTORY:", hist_res.source, "last_updated=", unix_to_time(hist_res.last_updated_unix), "error=", hist_res.error)
    print(hist_res.data.tail())

    # 3) Write snapshot to a text file
    q = quote_res.data
    line = append_snapshot(
        path=s.snapshot_file,
        symbol=q["symbol"],
        price=q["price"],
        change=q["change"],
        pct_change=q["pct_change"],
        fetched_at_unix=q["timestamp_unix"],
    )
    print("\nSNAPSHOT WROTE:", line)

    #4) Graphing

    symbol = "AAPL"
    hist_vol_ann = compute_60d_vol(ingest.yfin, symbol)
    print("Latest 60D annualized vol:", hist_vol_ann)

    #5) Write to DB

    try:
         # Write  once
         write_snapshot_batch(ingest, store, s)

        # Run continously, writing every N seconds
         while True:
            time.sleep(s.snapshot_every_seconds)
            write_snapshot_batch(ingest, store, s)

    finally:
        store.close()

    # symbol = "AAPL"



    

if __name__ == "__main__":
    main()
