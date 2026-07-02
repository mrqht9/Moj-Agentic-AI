from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# SQLite database path
DB_PATH = Path(__file__).parent.parent.parent / "data" / "app.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables + apply lightweight in-place migrations."""
    from app.db.models import User, XAccount, SocialAccount, Conversation, Message, ScheduleEvent, TelegramIntegration
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")

    # ─── Lightweight migrations (SQLite ALTER TABLE) ───
    # نضيف أعمدة جديدة على جداول موجودة بدون كسر البيانات
    _apply_lightweight_migrations()


def _apply_lightweight_migrations():
    """يطبّق ALTER TABLE بسيطة لإضافة أعمدة جديدة على جداول موجودة."""
    migrations = [
        # (table_name, column_name, column_definition)
        ("social_accounts", "category", "VARCHAR(50)"),
    ]

    with engine.connect() as con:
        for table, column, definition in migrations:
            try:
                # نتحقق هل العمود موجود
                cols = con.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
                col_names = [c[1] for c in cols]
                if column in col_names:
                    continue

                con.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                # نضيف index لو ينفع
                if column == "category":
                    con.exec_driver_sql(
                        f"CREATE INDEX IF NOT EXISTS ix_{table}_{column} ON {table}({column})"
                    )
                con.commit()
                print(f"[Migration] ✅ أضفت العمود {column} إلى {table}")
            except Exception as e:
                print(f"[Migration] ⚠️ فشل ترقية {table}.{column}: {e}")
