import threading
import time
from vnstock3 import Vnstock
# Biến toàn cục để lưu giá cổ phiếu
stock_prices = {}

def update_stock_prices():
    global stock_prices
    symbols = ['RAL', 'HPG', 'MBB']
    while True:
        try:
            for symbol in symbols:
                symbol_upper = symbol.upper()
                stock = Vnstock(source="TCBS", show_log=False).stock(symbol=symbol_upper, source='VCI')
                data = stock.trading.price_board(symbols_list=[symbol_upper])
                stock_prices[symbol_upper] = data['match']['match_price']
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
        time.sleep(30)

# Hàm để lấy giá cổ phiếu từ biến đã lưu
def get_current_stock_price(symbol):
    symbol = symbol.upper()
    return stock_prices.get(symbol, None)

# Khởi động thread để cập nhật giá cổ phiếu
thread = threading.Thread(target=update_stock_prices)
thread.daemon = True
thread.start()