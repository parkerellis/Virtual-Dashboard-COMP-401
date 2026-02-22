from dataclasses import dataclass
from typing import Any, Optional

from .cache import TTLCache
from .clients import FinnhubClient, YFinanceClient

@dataclass
class IngestResult:
    data: Any
    source: str # "live" | "cache_fresh" | "cache_stale"
    last_updated_unix: Optional[float]
    error: Optional[str] = None

class IngestService:
    def __init__(self, finnhub: FinnhubClient, yfin: YFinanceClient, cache: TTLCache):
        self.finnhub = finnhub
        self.yfin = yfin
        self.cache = cache

    def get_quote(self, symbol: str, ttl_seconds: int) -> IngestResult:
        key = f"quote:{symbol.upper()}"
        if self.cache.is_fresh(key):
            e = self.cache.get(key)
            return IngestResult(e.value, "cache_fresh", e.fetched_at)

        stale = self.cache.get(key)
        try:
            q = self.finnhub.quote(symbol.upper())
            e = self.cache.set(key, q, ttl_seconds)
            return IngestResult(e.value, "live", e.fetched_at)
        except Exception as ex:
            if stale:
                # fallback
                return IngestResult(stale.value, "cache_stale", stale.fetched_at, error=str(ex))
            raise  

    def get_history_close(self, symbol: str, period: str, interval: str, ttl_seconds: int) -> IngestResult:
        key = f"history:{symbol.upper()}:{period}:{interval}"
        if self.cache.is_fresh(key):
            e = self.cache.get(key)
            return IngestResult(e.value, "cache_fresh", e.fetched_at)

        stale = self.cache.get(key)
        try:
            df = self.yfin.history_close(symbol.upper(), period=period, interval=interval)
            e = self.cache.set(key, df, ttl_seconds)
            return IngestResult(e.value, "live", e.fetched_at)
        except Exception as ex:
            if stale:
                return IngestResult(stale.value, "cache_stale", stale.fetched_at, error=str(ex))
            raise
