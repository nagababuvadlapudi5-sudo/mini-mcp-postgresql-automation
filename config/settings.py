import os
import json
from dotenv import load_dotenv

load_dotenv()


class Settings:

    DEFAULT_DB = os.getenv("DEFAULT_DB", "CollegeDB")

    # Multiple database configurations
    DATABASES = json.loads(
        os.getenv("DATABASES_JSON", "{}")
    )

    # Permitted tables for each database
    ALLOWED_TABLES = json.loads(
        os.getenv("ALLOWED_TABLES_JSON", "{}")
    )

    # Backward compatibility with your original CollegeDB settings
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "CollegeDB")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "Naga@2345")