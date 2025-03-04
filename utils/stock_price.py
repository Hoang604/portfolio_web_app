def get_current_stock_price(stock_code, db):
    cursor = db.cursor()
    cursor.execute(f"SELECT price FROM stock_prices where stock_code = '{stock_code}' ORDER BY date DESC LIMIT 1")
    stock_price = cursor.fetchone()
    stock_price = float(stock_price[0]) * 1000
    return stock_price