from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import sqlite3
from datetime import datetime
import config

# Initialize FastAPI application
app = FastAPI(title="Stock Market Dashboard")

# Set up Jinja2 templates directory
templates = Jinja2Templates(directory="templates")

def get_db_connection():
    """Create a database connection with row factory."""
    connection = sqlite3.connect(config.DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Home page - lists all stocks with filters."""
    stock_filter = request.query_params.get('filter', '')

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        if stock_filter == 'new_closing_highs':
            cursor.execute("""
                SELECT s.symbol, s.name, s.exchange, sp.close, sp.date 
                FROM stock s
                JOIN stock_price sp ON s.id = sp.stock_id
                WHERE sp.close = (
                    SELECT MAX(close) FROM stock_price WHERE stock_id = sp.stock_id
                ) AND sp.date = (SELECT MAX(date) FROM stock_price)
                ORDER BY s.symbol;
            """)
        else:
            cursor.execute("""
                SELECT s.id, s.symbol, s.name, s.exchange,
                    MIN(sp.low) AS opening_low, MAX(sp.high) AS opening_high
                FROM stock s
                JOIN stock_price sp ON s.id = sp.stock_id
                GROUP BY s.id
                ORDER BY s.symbol;
            """)

        stocks = cursor.fetchall()
        connection.close()

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "stocks": stocks,
                "stock_filter": stock_filter,
                "year": datetime.now().year,
                "title": "Stock Market Dashboard"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stock/{symbol}", response_class=HTMLResponse)
async def stock_detail(request: Request, symbol: str):
    """Displays details of a specific stock."""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT id, symbol, name, exchange FROM stock WHERE symbol = ? LIMIT 1", (symbol.upper(),))
        stock = cursor.fetchone()

        if not stock:
            connection.close()
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

        cursor.execute("SELECT date, open, high, low, close, volume FROM stock_price WHERE stock_id = ? ORDER BY date DESC LIMIT 100", (stock['id'],))
        bars = cursor.fetchall()

        cursor.execute("SELECT id, name FROM strategy")
        strategies = cursor.fetchall()

        connection.close()

        return templates.TemplateResponse(
            "stock_detail.html",
            {
                "request": request,
                "stock": stock,
                "bars": bars,
                "strategies": strategies,
                "title": f"{stock['symbol']} - {stock['name']}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stock/", response_class=HTMLResponse)
async def stock_list(request: Request):
    """Displays a list of all stocks."""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT id, symbol, name, exchange FROM stock ORDER BY symbol;")
        stocks = cursor.fetchall()
        connection.close()

        return templates.TemplateResponse("stock_list.html", {"request": request, "stocks": stocks, "title": "Stock List"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/apply_strategy")
def apply_strategy(strategy_id: int = Form(...), stock_id: int = Form(...)):
    """Applies a selected strategy to a stock."""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("INSERT INTO stock_strategy (stock_id, strategy_id) VALUES (?, ?)", (stock_id, strategy_id))
        connection.commit()
        connection.close()

        return RedirectResponse(url=f"/strategy/{strategy_id}", status_code=303)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
