import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "rms-super-secret-key-1357924680"
    )

    # -----------------------------
    # Database Configuration
    # -----------------------------

    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        # Render PostgreSQL compatibility
        if database_url.startswith("postgres://"):
            database_url = database_url.replace(
                "postgres://",
                "postgresql://",
                1
            )

        SQLALCHEMY_DATABASE_URI = database_url

    else:
        # Local SQLite database
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "rms.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # -----------------------------
    # Upload Settings
    # -----------------------------

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # -----------------------------
    # Cache
    # -----------------------------

    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300

    # -----------------------------
    # Session
    # -----------------------------

    PERMANENT_SESSION_LIFETIME = 1800