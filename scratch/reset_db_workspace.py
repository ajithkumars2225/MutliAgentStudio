import sqlite3

conn = sqlite3.connect("developer_studio.db")
cursor = conn.cursor()

# Update workspace setting
cursor.execute("UPDATE settings SET value = 'C:\\PERSONAL DATA\\2.POC\\AGENTS\\workspace' WHERE key = 'active_workspace'")
conn.commit()

# Print current setting
cursor.execute("SELECT key, value FROM settings WHERE key = 'active_workspace'")
print("Updated Workspace setting:", cursor.fetchone())

conn.close()
