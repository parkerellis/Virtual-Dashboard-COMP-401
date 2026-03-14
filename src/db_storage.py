from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import mysql.connector


@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    name: str
    user: str
    password: str


class MariaDBStore:
    def __init__(self, cfg: DBConfig):
        self.cfg = cfg
        self.conn = mysql.connector.connect(
            host=cfg.host,
            port=cfg.port,
            user=cfg.user,
            password=cfg.password,
            database=cfg.name,
        )
        self.conn.autocommit = True

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    @staticmethod
    # Convert unix to utc
    def _unix_to_datetime_utc_naive(ts_unix: float | int | None) -> datetime:
        if ts_unix is None:
            return datetime.now(timezone.utc).replace(tzinfo=None)
        return datetime.fromtimestamp(float(ts_unix), tz=timezone.utc).replace(tzinfo=None)

    # Upsert new stock snapshot - prevents duplicates (i.e. same symbol and fetched at time)
    def upsert_snapshot(
        self,
        symbol: str,
        price,
        change,
        pct_change,
        fetched_at_unix: float | int | None,
    ) -> None:
        fetched_at = self._unix_to_datetime_utc_naive(fetched_at_unix)

        sql = """
        INSERT INTO prices (symbol, price, change_amt, change_pct, fetched_at)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          price=VALUES(price),
          change_amt=VALUES(change_amt),
          change_pct=VALUES(change_pct);
        """

        with self.conn.cursor() as cur:
            cur.execute(sql, (symbol, price, change, pct_change, fetched_at))
            
    # Gets recent snapshots
    def get_recent_snapshots(self, symbol: str, limit: int = 300):
        sql = """
        SELECT price, fetched_at
        FROM prices
        WHERE symbol = %s
        ORDER BY fetched_at DESC
        LIMIT %s;
        """
        with self.conn.cursor(dictionary=True) as cur:
             cur.execute(sql, (symbol, limit))
             rows = cur.fetchall()

        rows.reverse()
        return rows
