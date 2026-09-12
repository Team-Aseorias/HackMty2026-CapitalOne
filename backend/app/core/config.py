from dataclasses import dataclass
from os import getenv
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependencies are installed in production
    load_dotenv = None

if load_dotenv:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")


@dataclass(frozen=True)
class Settings:
    nessie_base_url: str = getenv("NESSIE_BASE_URL", "http://api.reimaginebanking.com")
    nessie_api_key: str = getenv("NESSIE_API_KEY", "")
    mongodb_uri: str = getenv("MONGODB_URI", "")
    mongodb_database: str = getenv("MONGODB_DATABASE", "ancla")
    fraud_cost: float = float(getenv("FRAUD_COST", "1000"))
    verify_cost: float = float(getenv("VERIFY_COST", "5"))
    abandonment_cost_rate: float = float(getenv("ABANDONMENT_COST_RATE", "0.15"))
    nessie_timeout_seconds: float = float(getenv("NESSIE_TIMEOUT_SECONDS", "4"))


settings = Settings()
