# setup_db.py
"""
Enhanced Database setup script for Gluvia
This script will:
1. Check PostgreSQL connection
2. Create database if it doesn't exist
3. Create the database tables
4. Create an initial admin user for testing
5. Verify the setup
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, ProgrammingError
from dotenv import load_dotenv
import urllib.parse

from database import Base, User
from auth import hash_password

load_dotenv()

def parse_database_url(database_url):
    """Parse the DATABASE_URL to extract components"""
    if not database_url:
        return None

    # Remove postgresql:// prefix
    url = database_url.replace('postgresql://', '')

    # Split user:password@host:port/database
    if '@' in url:
        auth_part, host_part = url.split('@', 1)
        if ':' in auth_part:
            username, password = auth_part.split(':', 1)
        else:
            username, password = auth_part, ''
    else:
        return None

    if '/' in host_part:
        host_port, database = host_part.split('/', 1)
    else:
        return None

    if ':' in host_port:
        host, port = host_part.split(':', 1)
    else:
        host, port = host_part, '5432'

    return {
        'username': username,
        'password': password,
        'host': host,
        'port': port,
        'database': database
    }

def create_database_if_not_exists(db_config):
    """Create the database if it doesn't exist"""
    try:
        # Connect to PostgreSQL server (not to specific database)
        server_url = f"postgresql://{db_config['username']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/postgres"
        server_engine = create_engine(server_url)

        with server_engine.connect() as conn:
            # Check if database exists
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{db_config['database']}'"))
            if not result.fetchone():
                # Create database
                conn.execute(text("COMMIT"))  # End any existing transaction
                conn.execute(text(f"CREATE DATABASE {db_config['database']}"))
                print(f"✅ Database '{db_config['database']}' created successfully")
            else:
                print(f"ℹ️  Database '{db_config['database']}' already exists")

        server_engine.dispose()
        return True

    except Exception as e:
        print(f"❌ Failed to create database: {str(e)}")
        return False

def check_database_connection(database_url):
    """Test database connection"""
    try:
        engine = create_engine(database_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
        print("✅ Database connection successful")
        return True
    except OperationalError as e:
        if "database" in str(e) and "does not exist" in str(e):
            print("⚠️  Database does not exist, will attempt to create it")
            return False
        else:
            print(f"❌ Database connection failed: {str(e)}")
            print("Make sure PostgreSQL is running and credentials are correct")
            return False
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

def setup_database_tables(database_url):
    """Initialize the database and create tables"""
    try:
        # Create engine and session
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Create all tables
        print("🔧 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")

        # Create session for user creation
        db = SessionLocal()

        try:
            # Check if admin user already exists
            existing_admin = db.query(User).filter(User.username == "admin").first()
            if existing_admin:
                print("⚠️  Admin user already exists")
                print(f"   Username: admin")
                print(f"   Email: {existing_admin.email}")
            else:
                # Create admin user
                print("👤 Creating admin user...")
                admin_user = User(
                    username="admin",
                    email="admin@gluvia.in",
                    hashed_password=hash_password("admin123"),
                    is_active=True
                )
                db.add(admin_user)
                db.commit()
                print("✅ Admin user created successfully")
                print("   Username: admin")
                print("   Password: admin123")
                print("   Email: admin@gluvia.in")

        finally:
            db.close()

        engine.dispose()
        return True

    except Exception as e:
        print(f"❌ Database setup failed: {str(e)}")
        return False

def verify_setup():
    """Verify that everything is working"""
    print("\n🔍 Verifying setup...")

    DATABASE_URL = os.getenv("DATABASE_URL")

    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # Check if tables exist
        tables = engine.table_names() if hasattr(engine, 'table_names') else []

        # Check if admin user exists
        admin_user = db.query(User).filter(User.username == "admin").first()

        db.close()
        engine.dispose()

        if admin_user:
            print("✅ Admin user verification successful")
            print("✅ Database setup verification completed")
            return True
        else:
            print("❌ Admin user not found")
            return False

    except Exception as e:
        print(f"❌ Setup verification failed: {str(e)}")
        return False

def print_next_steps():
    """Print helpful next steps"""
    print("\n" + "="*60)
    print("🎉 Database setup completed successfully!")
    print("="*60)
    print("\n📋 Next Steps:")
    print("1. Start your FastAPI server:")
    print("   uvicorn main:app --reload")
    print("\n2. Test the API:")
    print("   python test_auth.py")
    print("\n3. Login credentials:")
    print("   Username: admin")
    print("   Password: admin123")
    print("\n4. API Endpoints:")
    print("   • POST /register - Register new users")
    print("   • POST /login - User login")
    print("   • POST /upload - Upload prescriptions (requires auth)")
    print("\n5. Access API docs:")
    print("   http://127.0.0.1:8000/docs")

def main():
    print("🚀 Setting up Gluvia Database")
    print("=" * 50)

    # Check if .env file exists
    if not os.path.exists('../.env'):
        print("❌ .env file not found!")
        print("Please create a .env file with DATABASE_URL")
        return False

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in .env file")
        return False

    print(f"���� Database URL: {DATABASE_URL.split('@')[0]}@***")

    # Parse database URL
    db_config = parse_database_url(DATABASE_URL)
    if not db_config:
        print("❌ Invalid DATABASE_URL format")
        return False

    # Step 1: Check initial connection
    print("\n📡 Step 1: Checking database connection...")
    if not check_database_connection(DATABASE_URL):
        # If database doesn't exist, try to create it
        print("\n🏗️  Step 1b: Creating database...")
        if not create_database_if_not_exists(db_config):
            print("❌ Failed to create database. Please check your PostgreSQL setup.")
            return False

        # Try connection again
        if not check_database_connection(DATABASE_URL):
            print("❌ Still cannot connect to database after creation attempt.")
            return False

    # Step 2: Setup tables and admin user
    print("\n🔧 Step 2: Setting up database tables and admin user...")
    if not setup_database_tables(DATABASE_URL):
        return False

    # Step 3: Verify setup
    if not verify_setup():
        return False

    # Step 4: Print next steps
    print_next_steps()
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print("\n❌ Database setup failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)
