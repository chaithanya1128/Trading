import yfinance
df = yfinance.download('AAPL', start='2024-01-01', end='2024-10-02')
df.to_csv('AAPL.csv')




























