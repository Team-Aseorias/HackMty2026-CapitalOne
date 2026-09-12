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
    nessie_base_url: str = getenv("NESSIE_BASE_URL", "https://api.nessieisreal.com")
    nessie_api_key: str = getenv("NESSIE_API_KEY", "")
    # MONGO_* is canonical. MONGODB_* remains as a migration fallback so an
    # existing deployment does not lose its database connection unexpectedly.
    mongo_uri: str = getenv("MONGO_URI") or getenv("MONGODB_URI", "")
    mongo_db: str = getenv("MONGO_DB") or getenv("MONGODB_DATABASE") or "ancla"
    fraud_cost: float = float(getenv("FRAUD_COST", "1000"))
    verify_cost: float = float(getenv("VERIFY_COST", "5"))
    abandonment_cost_rate: float = float(getenv("ABANDONMENT_COST_RATE", "0.15"))
    nessie_timeout_seconds: float = float(getenv("NESSIE_TIMEOUT_SECONDS", "4"))
    # Demo policy limits; these are not calibrated bank production thresholds.
    max_soft_risk: float = float(getenv("MAX_SOFT_RISK", "0.15"))
    max_soft_expected_loss: float = float(getenv("MAX_SOFT_EXPECTED_LOSS", "15"))
    max_soft_amount: float = float(getenv("MAX_SOFT_AMOUNT", "500"))
    min_personalization_history: int = int(getenv("MIN_PERSONALIZATION_HISTORY", "3"))
    api_key: str = getenv("BACKEND_API_KEY", "")
    demo_mode: bool = getenv("DEMO_MODE", "true").lower() == "true"
    cors_origins: str = getenv("CORS_ORIGINS", "http://localhost:5173")

    def __post_init__(self) -> None:
        if not 0 < self.max_soft_risk < 1:
            raise ValueError("MAX_SOFT_RISK must be between 0 and 1")
        if min(self.max_soft_expected_loss, self.max_soft_amount) <= 0:
            raise ValueError("Soft verification limits must be positive")
        if self.min_personalization_history < 1:
            raise ValueError("MIN_PERSONALIZATION_HISTORY must be positive")


settings = Settings()
