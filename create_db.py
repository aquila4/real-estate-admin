import sqlite3

conn = sqlite3.connect('/mnt/uploads/database.db')

cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    location TEXT,
    description TEXT,
    image TEXT,
    video TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

conn.commit()
conn.close()

print("✅ Database and 'properties' table created.")
