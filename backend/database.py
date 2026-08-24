import os
import json
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger("quantummedai.database")

# Base backend directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
os.makedirs(DB_DIR, exist_ok=True)

# User persistence backup path for ephemeral cloud containers (e.g. Render free tier restarts)
USERS_BACKUP_PATH = os.path.join(DB_DIR, "users_backup.json")

# Database URL resolution: PostgreSQL if provided via env, otherwise persistent SQLite
RAW_DB_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_URI")

if RAW_DB_URL:
    # Render and Heroku use postgres:// which SQLAlchemy 1.4+ / 2.0 requires to be postgresql://
    if RAW_DB_URL.startswith("postgres://"):
        DATABASE_URL = RAW_DB_URL.replace("postgres://", "postgresql://", 1)
    else:
        DATABASE_URL = RAW_DB_URL
    
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True
    )
else:
    DB_PATH = os.path.join(DB_DIR, "quantum_med_ai.db")
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

# Database session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for all models
Base = declarative_base()


def load_users_backup() -> dict:
    """Loads cached users from the persistent backup JSON file."""
    if os.path.exists(USERS_BACKUP_PATH):
        try:
            with open(USERS_BACKUP_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read users_backup.json: {e}")
    return {}


def save_user_to_backup(full_name: str, email: str, password_hash: str, gender: str = None, age: int = None, phone: str = None):
    """Persists a registered user into the local JSON backup to survive cloud container redeployments."""
    try:
        users = load_users_backup()
        clean_email = email.lower().strip()
        users[clean_email] = {
            "full_name": full_name,
            "email": clean_email,
            "password": password_hash,
            "gender": gender,
            "age": age,
            "phone": phone
        }
        with open(USERS_BACKUP_PATH, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save user to users_backup.json: {e}")


def get_user_from_backup(email: str):
    """Retrieves a user profile from the persistent backup by email."""
    users = load_users_backup()
    return users.get(email.lower().strip())