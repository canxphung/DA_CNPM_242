from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config.config import DATABASE_URL

# Create a new SQLAlchemy engine instance
engine = create_engine(DATABASE_URL, echo=True)

# Create a configured "Session" class
Session = sessionmaker(bind=engine)

# Create a base class for declarative models
Base = declarative_base()

def get_db_session():
    """
    Create a new database session.
    """
    db = Session()
    try:
        yield db
    finally:
        db.close()
    return db