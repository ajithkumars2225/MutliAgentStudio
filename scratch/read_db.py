import sqlite3

conn = sqlite3.connect("developer_studio.db")
cursor = conn.cursor()

# Get recent history
cursor.execute("SELECT id, timestamp, prompt, status FROM requirements_history ORDER BY id DESC LIMIT 10")
for row in cursor.fetchall():
    print(f"ID: {row[0]}")
    print(f"Time: {row[1]}")
    print(f"Prompt preview: {row[2][:200]}...")
    print(f"Status: {row[3]}")
    print("-" * 50)

# Get settings
cursor.execute("SELECT key, value FROM settings")
for row in cursor.fetchall():
    print(f"Setting: {row[0]} = {row[1]}")

conn.close()
