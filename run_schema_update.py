import sys
from app import create_app
from app.models import db
from sqlalchemy import text

def update_schema():
    app = create_app()
    with app.app_context():
        # Get database engine
        engine = db.engine
        
        print("Connecting to database and updating schema...")
        
        # Check database dialect
        db_type = engine.name
        print(f"Database Dialect: {db_type}")
        
        try:
            with engine.connect() as connection:
                # PostgreSQL supports ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...
                # SQLite does not support IF NOT EXISTS directly in ADD COLUMN but we can check if columns exist first or catch exceptions.
                if db_type == 'postgresql':
                    print("Executing PostgreSQL-specific ALTER TABLE statements...")
                    connection.execute(text("""
                        ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS image VARCHAR(250);
                    """))
                    connection.execute(text("""
                        ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);
                    """))
                    connection.execute(text("""
                        ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS image_public_id VARCHAR(250);
                    """))
                    connection.commit()
                else:
                    # SQLite fallback
                    print("Executing SQLite Alterations...")
                    # We will catch errors if the column already exists
                    try:
                        connection.execute(text("ALTER TABLE menu_items ADD COLUMN image VARCHAR(250);"))
                        connection.commit()
                    except Exception as e:
                        print(f"image col check: {e}")
                    
                    try:
                        connection.execute(text("ALTER TABLE menu_items ADD COLUMN image_url VARCHAR(500);"))
                        connection.commit()
                    except Exception as e:
                        print(f"image_url col check: {e}")
                        
                    try:
                        connection.execute(text("ALTER TABLE menu_items ADD COLUMN image_public_id VARCHAR(250);"))
                        connection.commit()
                    except Exception as e:
                        print(f"image_public_id col check: {e}")
                
                print("Database schema successfully verified and updated!")
                
        except Exception as e:
            print(f"Error during schema update: {e}")
            sys.exit(1)

if __name__ == '__main__':
    update_schema()