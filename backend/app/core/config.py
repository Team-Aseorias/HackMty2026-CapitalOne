import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    MONGO_URI: str = os.getenv("MONGO_URI", "")
    MONGO_DB: str = os.getenv("MONGO_DB", "ancla")
    NESSIE_BASE_URL: str = os.getenv("NESSIE_BASE_URL", "")
    NESSIE_API_KEY: str = os.getenv("NESSIE_API_KEY", "")

settings = Settings()