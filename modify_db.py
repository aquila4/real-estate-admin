import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Add 'description' column
try:
    cursor.execute("ALTER TABLE properties ADD COLUMN description TEXT")
    print("✅ 'description' column added.")
except sqlite3.OperationalError:
    print("⚠️ 'description' column may already exist.")

# Add 'images' column
try:
    cursor.execute("ALTER TABLE properties ADD COLUMN images TEXT")
    print("✅ 'images' column added.")
except sqlite3.OperationalError:
    print("⚠️ 'images' column may already exist.")

# Add 'videos' column
try:
    cursor.execute("ALTER TABLE properties ADD COLUMN videos TEXT")
    print("✅ 'videos' column added.")
except sqlite3.OperationalError:
    print("⚠️ 'videos' column may already exist.")

conn.commit()
conn.close()

print("✅ All required columns checked and updated if needed!")
