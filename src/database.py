from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from src.config import Config
from src.models import Base
import time

class DatabaseManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_database()
        return cls._instance
    
    def _init_database(self):
        """Initialize database connection with retry logic"""
        max_retries = 5
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                print(f"Attempting database connection (attempt {attempt + 1}/{max_retries})...")
                
                self.engine = create_engine(
                    Config.DATABASE_URL,
                    pool_size=10,
                    max_overflow=5,
                    pool_pre_ping=True,
                    echo=False,
                    connect_args={
                        'connect_timeout': 10,
                        'application_name': 'github_crawler'
                    }
                )

                with self.engine.connect() as conn:
                    result = conn.execute(text("SELECT 1"))
                    result.fetchone()  
                print(" Database connection established successfully")
                break
                
            except OperationalError as e:
                if attempt < max_retries - 1:
                    print(f" Database connection failed (attempt {attempt + 1}/{max_retries}): {str(e)[:100]}")
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    print(f" Failed to connect to database after {max_retries} attempts")
                    print(f"Database URL: {Config.DATABASE_URL}")
                    raise
            except Exception as e:
                print(f" Unexpected error: {type(e).__name__}: {str(e)[:100]}")
                raise
    
    @property
    def session(self):
        if not hasattr(self, '_session'):
            Session = scoped_session(sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            ))
            self._session = Session()
        return self._session
    
    def create_tables(self):
        """Create all tables"""
        try:
            Base.metadata.create_all(self.engine)
            print(" Database tables created")
        except Exception as e:
            print(f" Error creating tables: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        try:
            if hasattr(self, '_session'):
                self._session.close()
                delattr(self, '_session')
            if hasattr(self, 'engine'):
                self.engine.dispose()
        except Exception as e:
            print(f"Warning: Error closing database: {e}")