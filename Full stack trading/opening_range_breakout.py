import sqlite3
import config
import alpaca_trade_api as tradeapi
import smtplib
import ssl
from datetime import datetime, timedelta
import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Create an SSL context for secure email
context = ssl.create_default_context()

# Connect to the database
connection = sqlite3.connect(config.DB_FILE, timeout=30)
connection.row_factory = sqlite3.Row

cursor = connection.cursor()

# Get the strategy ID for 'opening_range_breakout'
cursor.execute("""
    SELECT id FROM strategy WHERE name = 'opening_range_breakout'
""")
strategy_id = cursor.fetchone()['id']

# Fetch the stocks associated with the strategy
cursor.execute("""
    SELECT symbol, name
    FROM stock
    JOIN stock_strategy ON stock_strategy.stock_id = stock.id
    WHERE stock_strategy.strategy_id = ?
""", (strategy_id,))
stocks = cursor.fetchall()

# Extract symbols from the fetched data
symbols = [str(stock['symbol']).strip() for stock in stocks]
logging.debug("Symbols fetched: %s", symbols)

# Initialize the Alpaca API
api = tradeapi.REST(config.API_KEY, config.SECRET_KEY, base_url=config.API_URL)

# Fetch all existing orders
orders = api.list_orders(status='all', limit=500, after='2025-01-10T13:30:00Z')
existing_order_symbols = [order.symbol for order in orders]

# Define the past date range
past_date = (datetime.today() - timedelta(days=10)).date()  # Example: 10 days ago
past_date_iso = past_date.isoformat()
start_minute_bar = f"{past_date_iso}T09:30:00-05:00"  # Adjust for time zone
end_minute_bar = f"{past_date_iso}T09:45:00-05:00"

# Messages for notifications
messages = []

# Fetch and process minute bars for each symbol
for symbol in symbols:
    try:
        logging.info("Processing symbol: %s", symbol)

        # Retrieve historical minute bars using Alpaca API
        minute_bars = api.get_bars(
            symbol,
            timeframe="1Min",
            start=past_date_iso,
            end=past_date_iso
        ).df

        # Ensure the index is a datetime object
        minute_bars.index = pd.to_datetime(minute_bars.index)

        # Filter data for the opening range
        opening_range_mask = (minute_bars.index >= pd.to_datetime(start_minute_bar)) & \
                             (minute_bars.index < pd.to_datetime(end_minute_bar))
        opening_range_bars = minute_bars.loc[opening_range_mask]
        opening_range_low = opening_range_bars['low'].min()
        opening_range_high = opening_range_bars['high'].max()
        opening_range = opening_range_high - opening_range_low

        # Filter data for after the opening range
        after_opening_range_mask = minute_bars.index >= pd.to_datetime(end_minute_bar)
        after_opening_range_bars = minute_bars.loc[after_opening_range_mask]
        after_opening_range_breakout = after_opening_range_bars[
            after_opening_range_bars['close'] > opening_range_high
        ]

        # Place orders for symbols breaking out of the opening range
        if not after_opening_range_breakout.empty:
            if symbol not in existing_order_symbols:
                limit_price = round(after_opening_range_breakout.iloc[0]['close'], 2)
                opening_range = round(opening_range, 2)  # Round to 2 decimal places
                messages.append(
                    f"Placing order for {symbol} at {limit_price}, closed above {opening_range_high}\n\n{after_opening_range_breakout.iloc[0]}\n\n"
                )
                logging.info(
                    "Placing order for %s at %s, closed above %s at %s",
                    symbol, limit_price, opening_range_high, after_opening_range_breakout.iloc[0]
                )
            else:
                logging.info("Already an order for %s, skipping", symbol)
    except Exception as e:
        logging.error("Error fetching data for %s: %s", symbol, e)

# Print and log messages
for message in messages:
    logging.info("Order Message: %s", message)
print(messages)

# Send email notification
try:
    with smtplib.SMTP_SSL(config.EMAIL_HOST, config.EMAIL_PORT, context=context) as server:
        server.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
        current_date = datetime.today().strftime('%Y-%m-%d')

        email_body = f"Subject: Trade Notifications for {current_date}\n\n"
        email_body += "\n\n".join(messages) if messages else "No breakout opportunities found."

        server.sendmail(
            config.EMAIL_ADDRESS,  # From
            config.EMAIL_ADDRESS,  # To
            email_body  # Email body
        )
    logging.info("Email sent successfully!")
except smtplib.SMTPAuthenticationError as e:
    logging.error("SMTP Authentication Error: %s", e)
except Exception as e:
    logging.error("Error sending email: %s", e)

    

