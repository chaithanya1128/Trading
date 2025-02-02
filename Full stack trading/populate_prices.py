import sqlite3
import config
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import TimeFrame
import logging
import time
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=f"price_population_{datetime.now().strftime('%Y%m%d')}.log"
)

def get_stock_data():
    """Fetch stock data from the database."""
    with sqlite3.connect(config.DB_FILE) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT id, symbol, exchange 
            FROM stock 
            WHERE symbol NOT LIKE '%.%'  -- Exclude symbols with periods
            AND symbol NOT LIKE '%/%'    -- Exclude crypto pairs
        """)
        
        return cursor.fetchall()

def init_price_table():
    """Ensure stock_price table exists."""
    with sqlite3.connect(config.DB_FILE) as connection:
        cursor = connection.cursor()
        
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
                FOREIGN KEY (stock_id) REFERENCES stock (id),
                UNIQUE(stock_id, date)
            )
        """)
        
        connection.commit()

def populate_prices():
    """Fetch stock prices from Alpaca API and update the database."""
    init_price_table()
    rows = get_stock_data()
    
    stock_dict = {row["symbol"]: row["id"] for row in rows}
    symbols = list(stock_dict.keys())

    try:
        # Initialize Alpaca API
        api = tradeapi.REST(
            config.API_KEY,
            config.SECRET_KEY,
            base_url=config.API_URL
        )

        chunk_size = 100
        for i in range(0, len(symbols), chunk_size):
            symbol_chunk = symbols[i:i + chunk_size]
            
            try:
                # Get historical data
                bars = api.get_bars(
                    symbol_chunk,
                    TimeFrame.Day,
                    limit=100,
                    adjustment="raw"
                )
                
                with sqlite3.connect(config.DB_FILE) as connection:
                    cursor = connection.cursor()
                    
                    for bar in bars:
                        try:
                            symbol = bar.S
                            stock_id = stock_dict[symbol]
                            
                            cursor.execute("""
                                INSERT OR REPLACE INTO stock_price (
                                    stock_id, date, open, high, low, close, volume
                                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                stock_id,
                                bar.t.date().isoformat(),
                                bar.o,
                                bar.h,
                                bar.l,
                                bar.c,
                                bar.v
                            ))
                            
                            logging.info(f"Processed {symbol} for date {bar.t.date().isoformat()}")
                            
                        except Exception as e:
                            logging.error(f"Error processing bar for {symbol}: {str(e)}")
                            continue
                    
                    connection.commit()
                
                logging.info(f"Completed chunk {i // chunk_size + 1} of {(len(symbols) + chunk_size - 1) // chunk_size}")
                time.sleep(1)  # Rate limit handling
                
            except Exception as e:
                logging.error(f"Error processing chunk {symbol_chunk}: {str(e)}")
                continue

    except Exception as e:
        logging.error(f"Major error in populate_prices: {str(e)}")

if __name__ == "__main__":
    populate_prices()
