import sqlite3
import config

# Connect to the database (or create it if it doesn't exist)
connection = sqlite3.connect(config.DB_FILE, timeout=10)
cursor = connection.cursor()

# Create the stock table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY,
        symbol TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        exchange TEXT NOT NULL
    )
""")

# Create the stock_price table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_price (
        id INTEGER PRIMARY KEY,
        stock_id INTEGER,
        date TEXT NOT NULL,
        open REAL NOT NULL,
        high REAL NOT NULL,
        low REAL NOT NULL,
        close REAL NOT NULL,
        volume INTEGER NOT NULL,
        sma_20 REAL,
        sma_50 REAL,
        rsi_14 REAL,                
        FOREIGN KEY (stock_id) REFERENCES stock (id)
    )
""")

# Create the strategy table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS strategy (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE
    )
""")

# Create the stock_strategy table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_strategy (
        stock_id INTEGER NOT NULL,
        strategy_id INTEGER NOT NULL,
        FOREIGN KEY (stock_id) REFERENCES stock (id),
        FOREIGN KEY (strategy_id) REFERENCES strategy (id),
        PRIMARY KEY (stock_id, strategy_id)
    )
""")

# Insert predefined strategies (use INSERT OR IGNORE to avoid duplicate errors)
strategies = ['opening_range_breakout', 'opening_range_breakdown']
for strategy in strategies:
    cursor.execute("INSERT OR IGNORE INTO strategy (name) VALUES (?)", (strategy,))

# Commit and close the connection
connection.commit()
connection.close()
