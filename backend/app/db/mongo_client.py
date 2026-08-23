import sys
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.config import settings

PROTECTED_DATABASES = {"admin", "kisan_ai", "local", "sample_mflix"}

_client_instance: MongoClient | None = None

def get_client() -> MongoClient:
    global _client_instance
    if _client_instance is None:
        if not settings.MONGODB_URI:
            raise ValueError("MONGODB_URI is not set in environment or config.")
        _client_instance = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
    return _client_instance

def assert_db_safety(db_name: str) -> None:
    if db_name.lower() in PROTECTED_DATABASES:
        raise ValueError(
            f"CRITICAL SAFETY VIOLATION: Database '{db_name}' is protected and must NEVER be accessed or modified!"
        )

def get_db(db_name: str | None = None) -> Database:
    target_db_name = db_name or settings.MONGO_DB_NAME
    assert_db_safety(target_db_name)
    client = get_client()
    return client[target_db_name]

def ping() -> bool:
    """
    Checks MongoDB connectivity, lists existing cluster databases,
    and asserts safety before pipeline execution.
    """
    client = get_client()
    try:
        client.admin.command("ping")
        existing_dbs = client.list_database_names()
        print(f"[MongoDB Ping] Connection successful. Existing databases on cluster: {existing_dbs}")
        
        # Verify that configured database is safe
        target_db = settings.MONGO_DB_NAME
        assert_db_safety(target_db)
        print(f"[MongoDB Ping] Target database '{target_db}' is verified safe for Switchback pipeline operations.")
        return True
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"[MongoDB Ping Error] Failed to connect to MongoDB cluster: {e}", file=sys.stderr)
        raise SystemExit(1)
