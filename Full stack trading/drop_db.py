import sqlite3
import config

# Open database connection
connection = sqlite3.connect(config.DB_FILE, timeout=20)

# Switch to WAL mode (reduces locking issues)
connection.execute("PRAGMA journal_mode=WAL;")

cursor = connection.cursor()

# Drop tables
cursor.execute("DROP TABLE IF EXISTS stock_price")
cursor.execute("DROP TABLE IF EXISTS stock")

# Commit and close
connection.commit()
connection.close()

print("Tables dropped successfully.")
