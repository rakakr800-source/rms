import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'rms-super-secret-key-1357924680')
    
    # Support MySQL, fallback to SQLite for local development convenience
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = os.environ.get('MYSQL_PORT', '3306')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'rms_db')
    
    # If MYSQL_DB is defined or we want to default to MySQL
    DEFAULT_MYSQL_URI = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    
    # We will try to connect to MySQL, if we can't we'll use sqlite
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(os.path.abspath(os.path.dirname(__file__)), 'rms.db')}")
    
    # If the user explicitly sets USE_MYSQL, enforce MySQL
    if os.environ.get('USE_MYSQL') == 'true':
        SQLALCHEMY_DATABASE_URI = DEFAULT_MYSQL_URI
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload folder configuration
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024 # 16 MB limit
    
    # Cache settings
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Session lifetime
    PERMANENT_SESSION_LIFETIME = 1800 # 30 minutes in seconds
