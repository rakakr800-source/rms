import sys
import os
from sqlalchemy import text, inspect

def get_masked_db_url(url):
    if not url:
        return "Not Set"
    # Mask credentials (username:password) in the connection string
    try:
        if "@" in url:
            prefix, rest = url.split("@", 1)
            dialect_and_user = prefix.split("//", 1)
            dialect = dialect_and_user[0]
            host_and_port = rest.split("/", 1)[0]
            return f"{dialect}//****:****@{host_and_port}"
        return url
    except Exception:
        return "Unknown URL format"

def update_schema():
    # 1. Print current environment database URL host
    env_db_url = os.environ.get("DATABASE_URL")
    print(f"[DIAGNOSTIC] Environment DATABASE_URL: {get_masked_db_url(env_db_url)}")

    # 2. Create the Flask app context
    print("[DIAGNOSTIC] Initializing Flask application context...")
    from app import create_app
    from app.models import db
    
    app = create_app()
    with app.app_context():
        # 3. Print the database URI configured inside the Flask application config
        app_db_uri = app.config.get("SQLALCHEMY_DATABASE_URI")
        print(f"[DIAGNOSTIC] Flask Application SQLALCHEMY_DATABASE_URI: {get_masked_db_url(app_db_uri)}")
        
        # Verify they are identical
        if env_db_url and app_db_uri:
            # Simple sanitization for startswith postgres/postgresql
            env_sanitized = env_db_url.replace("postgres://", "postgresql://", 1)
            app_sanitized = app_db_uri.replace("postgres://", "postgresql://", 1)
            if env_sanitized == app_sanitized:
                print("[VERIFICATION SUCCESS] The environment and application database URLs are IDENTICAL.")
            else:
                print("[VERIFICATION WARNING] Database URLs differ!")
                print(f"Env: {get_masked_db_url(env_sanitized)}")
                print(f"App: {get_masked_db_url(app_sanitized)}")
        
        engine = db.engine
        db_type = engine.name
        print(f"[DIAGNOSTIC] Connecting to database dialect: {db_type}")
        
        # 4. Execute migrations / ALTER TABLE statements
        try:
            with engine.connect() as connection:
                if db_type == 'postgresql':
                    print("[MIGRATION] Safely running PostgreSQL ALTER TABLE statements...")
                    connection.execute(text("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS image VARCHAR(250);"))
                    connection.execute(text("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);"))
                    connection.execute(text("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS image_public_id VARCHAR(250);"))
                    connection.commit()
                else:
                    print("[MIGRATION] Safely running SQLite ALTER TABLE fallbacks...")
                    try:
                        connection.execute(text("ALTER TABLE menu_items ADD COLUMN image VARCHAR(250);"))
                        connection.commit()
                    except Exception as e:
                        print(f"[SQLITE INFO] Col 'image' probably already exists: {e}")
                    
                    try:
                        connection.execute(text("ALTER TABLE menu_items ADD COLUMN image_url VARCHAR(500);"))
                        connection.commit()
                    except Exception as e:
                        print(f"[SQLITE INFO] Col 'image_url' probably already exists: {e}")
                        
                    try:
                        connection.execute(text("ALTER TABLE menu_items ADD COLUMN image_public_id VARCHAR(250);"))
                        connection.commit()
                    except Exception as e:
                        print(f"[SQLITE INFO] Col 'image_public_id' probably already exists: {e}")
                        
            print("[MIGRATION SUCCESS] ALTER TABLE queries executed successfully.")
            
        except Exception as sql_err:
            print(f"[MIGRATION ERROR] Failed to apply schema updates: {sql_err}", file=sys.stderr)
            sys.exit(1)

        # 5. Verify the schema columns in menu_items
        print("[VERIFICATION] Fetching and verifying columns for 'menu_items'...")
        try:
            inspector = inspect(engine)
            columns = [col['name'] for col in inspector.get_columns('menu_items')]
            print(f"[VERIFICATION] Found columns in 'menu_items': {columns}")
            
            required_cols = ['image', 'image_url', 'image_public_id']
            missing_cols = [col for col in required_cols if col not in columns]
            
            if missing_cols:
                print(f"[VERIFICATION FAILED] Missing columns in 'menu_items': {missing_cols}", file=sys.stderr)
                sys.exit(1)
            else:
                print("[VERIFICATION SUCCESS] All required columns ('image', 'image_url', 'image_public_id') are PRESENT.")
                
        except Exception as verif_err:
            print(f"[VERIFICATION ERROR] Failed to verify schema: {verif_err}", file=sys.stderr)
            sys.exit(1)

if __name__ == '__main__':
    update_schema()