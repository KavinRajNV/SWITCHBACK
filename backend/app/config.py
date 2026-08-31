import os
from pathlib import Path
from dotenv import load_dotenv

# Find project root (directory containing .env or backend folder)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "development")

    # Defaults to a local mongod so the app runs offline against the bundled
    # snapshot with an otherwise-empty .env; set MONGODB_URI to use Atlas.
    MONGODB_URI: str = os.getenv("MONGODB_URI") or "mongodb://localhost:27017"
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "switchback")

    # Comma-separated browser origins allowed to call the API.
    ALLOWED_ORIGINS: list = [
        o.strip() for o in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",") if o.strip()
    ]


    ADZUNA_APP_ID: str = os.getenv("ADZUNA_APP_ID", "")
    ADZUNA_APP_KEY: str = os.getenv("ADZUNA_APP_KEY", "")
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", os.getenv("openai", ""))

    BASE_DIR: Path = BASE_DIR
    
    # Path resolution for raw data: check Datasets/ or data/raw/
    @property
    def DATA_RAW_DIR(self) -> Path:
        datasets_path = self.BASE_DIR / "Datasets"
        data_raw_path = self.BASE_DIR / "data" / "raw"
        if datasets_path.exists():
            return datasets_path
        elif data_raw_path.exists():
            return data_raw_path
        return datasets_path

    @property
    def DATA_PROCESSED_DIR(self) -> Path:
        processed_path = self.BASE_DIR / "data" / "processed"
        processed_path.mkdir(parents=True, exist_ok=True)
        return processed_path

settings = Settings()
