import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'data', 'app.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE users ADD COLUMN name VARCHAR(255)")
    print("✅ Added 'name' column")
except Exception as e:
    print(f"'name' column: {e}")

try:
    cursor.execute("ALTER TABLE users ADD COLUMN profile_picture VARCHAR(500)")
    print("✅ Added 'profile_picture' column")
except Exception as e:
    print(f"'profile_picture' column: {e}")

try:
    cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
    print("✅ Added 'is_admin' column")
except Exception as e:
    print(f"'is_admin' column: {e}")

try:
    cursor.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1")
    print("✅ Added 'is_active' column")
except Exception as e:
    print(f"'is_active' column: {e}")

conn.commit()

# Set first user as admin
cursor.execute("UPDATE users SET is_admin = 1 WHERE id = (SELECT MIN(id) FROM users)")
conn.commit()

# Show current schema
cursor.execute("PRAGMA table_info(users)")
columns = cursor.fetchall()
print("\n📋 Current schema:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

conn.close()
print("\n✅ Done!")
