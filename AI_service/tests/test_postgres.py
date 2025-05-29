# scripts/test_postgresql_connection.py
import os
import sys
from pathlib import Path

# Setup path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

# Test connection
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv('DATABASE_URL')
print(f"Attempting to connect to: {DATABASE_URL}")

try:
    # Tạo engine
    engine = create_engine(DATABASE_URL)
    
    # Test kết nối
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.scalar()
        print(f"✓ Connected successfully!")
        print(f"PostgreSQL version: {version}")
        
        # Kiểm tra current database
        result = conn.execute(text("SELECT current_database()"))
        db_name = result.scalar()
        print(f"Current database: {db_name}")
        
        # Kiểm tra current user
        result = conn.execute(text("SELECT current_user"))
        user_name = result.scalar()
        print(f"Current user: {user_name}")
        
except Exception as e:
    print(f"✗ Connection failed: {e}")
    print("\nTroubleshooting tips:")
    print("1. Ensure PostgreSQL service is running")
    print("2. Check username and password in .env")
    print("3. Verify database 'greenhouse_ai_db' exists")
    print("4. Check PostgreSQL logs for more details")