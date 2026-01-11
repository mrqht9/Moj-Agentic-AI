"""
Test database connections - SQLite and Redis
"""
from app.db.database import engine, init_db, SessionLocal
from app.db.models import User, XAccount
from app.db.redis_client import RedisClient


def test_sqlite_connection():
    """Test SQLite database connection"""
    print("=" * 50)
    print("Testing SQLite Connection...")
    print("=" * 50)
    
    try:
        # Initialize database
        init_db()
        
        # Test connection
        db = SessionLocal()
        
        # Try a simple query
        users_count = db.query(User).count()
        x_accounts_count = db.query(XAccount).count()
        
        print(f"✓ SQLite connected successfully!")
        print(f"  - Users table: {users_count} records")
        print(f"  - X_Accounts table: {x_accounts_count} records")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"✗ SQLite connection failed: {e}")
        return False


def test_redis_connection():
    """Test Redis connection"""
    print("\n" + "=" * 50)
    print("Testing Redis Connection...")
    print("=" * 50)
    
    try:
        if RedisClient.test_connection():
            print("✓ Redis connected successfully!")
            
            # Test set/get
            RedisClient.set_session("test_session", 999, expires=10)
            result = RedisClient.get_session("test_session")
            
            if result == 999:
                print("✓ Redis read/write test passed!")
            
            RedisClient.delete_session("test_session")
            return True
        else:
            print("✗ Redis connection failed")
            print("  Note: Redis server might not be running")
            print("  You can start Redis or skip this for local development")
            return False
            
    except Exception as e:
        print(f"✗ Redis connection error: {e}")
        print("  Note: Redis is optional for basic functionality")
        return False


def run_all_tests():
    """Run all database connection tests"""
    print("\n" + "=" * 60)
    print("   DATABASE CONNECTION TESTS")
    print("=" * 60)
    
    sqlite_ok = test_sqlite_connection()
    redis_ok = test_redis_connection()
    
    print("\n" + "=" * 50)
    print("TEST RESULTS:")
    print("=" * 50)
    print(f"SQLite: {'✓ PASSED' if sqlite_ok else '✗ FAILED'}")
    print(f"Redis:  {'✓ PASSED' if redis_ok else '✗ FAILED (optional)'}")
    print("=" * 50)
    
    return sqlite_ok


if __name__ == "__main__":
    run_all_tests()
