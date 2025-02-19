stock_prices = {}

def get_current_stock_price(stock_code, db):
    if stock_code in stock_prices:
        return stock_prices[stock_code]
    cursor = db.cursor()
    cursor.execute(f"SELECT price FROM stock_prices where stock_code = '{stock_code}' ORDER BY date DESC LIMIT 1")
    stock_price = cursor.fetchone()
    stock_price = float(stock_price[0]) 
    stock_prices[stock_code] = stock_price
    return stock_price