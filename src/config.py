import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    finnhub_api_key: str
    quote_ttl_seconds: int 
    history_ttl_seconds: int
    snapshot_file: str 

      # DB 
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_pass: str

    # Continuous 
    snapshot_symbols: tuple[str, ...]
    snapshot_every_seconds: int

# Gets 'settings' / default values from .env variables
def get_settings() -> Settings:
    key = os.getenv("FINNHUB_API_KEY").strip()
    if not key:
        raise RuntimeError("Missing FINNHUB_API_KEY. Put it in a .env file in project root.")

    syms_raw = os.getenv("SNAPSHOT_SYMBOLS")
    symbols = tuple(s.strip().upper() for s in syms_raw.split(",") if s.strip())

    return Settings(
        finnhub_api_key=key,
        quote_ttl_seconds=int(os.getenv("QUOTE_TTL_SECONDS")),
        history_ttl_seconds=int(os.getenv("HISTORY_TTL_SECONDS")),
        snapshot_file=os.getenv("SNAPSHOT_FILE"),

        # DB
        db_host=os.getenv("DB_HOST"),
        db_port=int(os.getenv("DB_PORT")),
        db_name=os.getenv("DB_NAME"),
        db_user=os.getenv("DB_USER"),
        db_pass=os.getenv("DB_PASS"),

        # Continuous
        snapshot_symbols=symbols,
        snapshot_every_seconds=int(os.getenv("SNAPSHOT_EVERY_SECONDS")),
    )
