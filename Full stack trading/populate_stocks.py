import sqlite3
import alpaca_trade_api as tradeapi
import config
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=f'stock_population_{datetime.now().strftime("%Y%m%d")}.log'
)

def init_db():
    """Initialize the database with required tables."""
    with sqlite3.connect(config.DB_FILE) as connection:
        cursor = connection.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                exchange TEXT NOT NULL
            )
        """)
        
        connection.commit()

def populate_stocks():
    """Fetch stocks from Alpaca and store them in the database."""
    init_db()
    
    with sqlite3.connect(config.DB_FILE) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        
        try:
            # Initialize Alpaca API
            api = tradeapi.REST(
                config.API_KEY,
                config.SECRET_KEY,
                base_url=config.API_URL
            )
            
            # Get existing stock symbols
            cursor.execute("SELECT symbol FROM stock")
            existing_symbols = {row['symbol'] for row in cursor.fetchall()}
            
            # Fetch Alpaca assets
            assets = api.list_assets()
            new_stocks = 0
            
            for asset in assets:
                if (
                    asset.status == 'active' and 
                    asset.tradable and 
                    '/' not in asset.symbol and  # Exclude crypto
                    asset.symbol not in existing_symbols
                ):
                    cursor.execute("""
                        INSERT OR IGNORE INTO stock (symbol, name, exchange)
                        VALUES (?, ?, ?)
                    """, (asset.symbol, asset.name, asset.exchange))
                    
                    new_stocks += 1
                    logging.info(f"Added new stock: {asset.symbol} - {asset.name}")
            
            connection.commit()
            logging.info(f"Successfully added {new_stocks} new stocks to database")
        
        except Exception as e:
            logging.error(f"Error populating stocks: {str(e)}")

if __name__ == "__main__":
    populate_stocks()
