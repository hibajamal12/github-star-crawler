import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import DatabaseManager
from src.models import Base

def main():
    print(" Setting up database...")
    
    try:
        db = DatabaseManager()
  
        db.create_tables()
        
        print(" Database setup completed successfully!")
     
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f" Created tables: {', '.join(tables)}")
        
    except Exception as e:
        print(f" Error during database setup: {e}")
        sys.exit(1)
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    main()