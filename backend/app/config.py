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
    MONGODB_URI: str = os.getenv("MONGODB_URI", "")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "switchback")
    
    ADZUNA_APP_ID: str = os.getenv("ADZUNA_APP_ID", "")
    ADZUNA_APP_KEY: str = os.getenv("ADZUNA_APP_KEY", "")
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

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
