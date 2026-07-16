import sqlite3

conn = sqlite3.connect("developer_studio.db")
cursor = conn.cursor()

# Set active provider to nvidia
cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('provider', 'nvidia')")

# Set nvidia API Key
cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('nvidia_api_key', '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')")

# Set nvidia Model ID
cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('nvidia_model', 'z-ai/glm-5.2')")

conn.commit()

# Print settings to verify
cursor.execute("SELECT key, value FROM settings WHERE key IN ('provider', 'nvidia_api_key', 'nvidia_model')")
print("Settings updated successfully:")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]}")

conn.close()
