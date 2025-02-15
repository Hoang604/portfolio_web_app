import datetime
import pandas as pd
import vnstock3
from database import connect_db
from icecream import ic
import matplotlib.pyplot as plt
import math

def get_stock_price(symbol, start="2024-10-18", end=str(datetime.date.today())):
    """Trả về giá cổ phiếu của symbol theo ngày"""
    try:
        df = vnstock3.Vnstock(source="VCI", show_log=False).stock(symbol=symbol, source='VCI').quote.history(start=start, end=end)
        return df
    except Exception as e:
        ic(f"Error processing {symbol}: {e}")
        return pd.DataFrame()

def get_stock_prices(user_id):
    """Lấy giá cổ phiếu của tất cả các mã cổ phiếu"""
    dataset = []
    mydb = connect_db()
    cursor = mydb.cursor(dictionary=True)
    sql_query = """
        SELECT stock_code
        from portfolio_holdings
        where user_id = %s
    """
    cursor.execute(sql_query, (user_id,))
    stocks = cursor.fetchall()
    stocks = [stock['stock_code'] for stock in stocks]
    ic(stocks)
    if not stocks:
        return dataset
    vnindex = get_stock_price('VNINDEX', start="2024-10-18")
    for stock in stocks:
        df = get_stock_price(stock, start="2024-10-18")
        df['stock_code'] = stock
        drop_columns = ['open', 'high', 'low', 'volume']
        df.drop(columns=drop_columns, inplace=True)
        df['vnindex'] = vnindex['close']
        dataset.append(df)
    mydb.close()
    return dataset


def prepare_stock_price(stock_price):
    """Chuẩn bị dữ liệu cho 1 cổ phiếu để vẽ biểu đồ, tính toán giá điều chỉnh theo cổ tức"""
    mydb = connect_db()
    cursor = mydb.cursor(dictionary=True)
    
    # Lấy tất cả các đợt chia cổ tức, sắp xếp theo thời gian từ mới đến cũ
    sql_query = """
        SELECT dividend_type, payment_date, stock_ratio_numerator, 
               stock_ratio_denominator, cash_amount_per_share
        FROM dividends
        WHERE stock_code = %s
        ORDER BY payment_date DESC
    """
    cursor.execute(sql_query, (stock_price['stock_code'].iloc[0],))
    dividends = cursor.fetchall()
    # Duyệt qua từng đợt chia cổ tức
    for dividend in dividends:
        payment_date = pd.to_datetime(dividend['payment_date'])
        dividend_type = dividend['dividend_type']
        
        # Chỉ điều chỉnh giá cho các ngày trước ngày chia cổ tức
        mask = stock_price['time'] < payment_date
        
        if dividend_type == 'Stock':
            ratio = dividend['stock_ratio_numerator'] / dividend['stock_ratio_denominator']
            stock_price.loc[mask, 'close'] *= (float)(ratio + 1)
                
        elif dividend_type == 'Cash':
            cash_amount = dividend['cash_amount_per_share']
            stock_price.loc[mask, 'close'] += cash_amount
    mydb.close()
    return stock_price

def prepare_stock_profit(stock_price, user_id):
    mydb = connect_db()
    cursor = mydb.cursor(dictionary=True)
    sql_query = """
        SELECT user_id, stock_code, transaction_date, transaction_type, price_per_share, quantity
        FROM transactions
        WHERE stock_code = %s and user_id = %s
        ORDER BY transaction_date
    """
    cursor.execute(sql_query, (stock_price['stock_code'].iloc[0], user_id))
    transactions = cursor.fetchall()
    mydb.close()
    if not transactions:
        return stock_price

    def calculate_pure_profit(stock_price, transactions):
        """Tính toán Lợi nhuận thực nhận được từ cổ phiếu"""
        stock_price['stock_profit'] = 0.0
        stock_price['vnindex_profit'] = 0
        stock_price['bank_profit'] = 0

        transactions[0]['avg_price'] = float(transactions[0]['price_per_share'])/1000
        transactions[0]['total_invest_value'] = float(transactions[0]['price_per_share'] * transactions[0]['quantity'])
        transactions[0]['total_quantity'] = float(transactions[0]['quantity'])

        for i in range(1, len(transactions)):
            transactions[i]['total_invest_value'] = (float(transactions[i]['price_per_share'] * transactions[i]['quantity']) +
                                                    transactions[i - 1]['total_invest_value'])
            transactions[i]['total_quantity'] = float(transactions[i]['quantity']) + transactions[i - 1]['total_quantity']
            transactions[i]['avg_price'] = (transactions[i]['total_invest_value'] / 1000) / transactions[i]['total_quantity']
        
        mydb = connect_db()
        cursor = mydb.cursor(dictionary=True)
        
        # Lấy tất cả các đợt chia cổ tức, sắp xếp theo thời gian từ mới đến cũ
        sql_query = """
            SELECT dividend_type, payment_date, stock_ratio_numerator, 
                stock_ratio_denominator, cash_amount_per_share
            FROM dividends
            WHERE stock_code = %s
            ORDER BY payment_date DESC
        """
        cursor.execute(sql_query, (stock_price['stock_code'].iloc[0],))
        dividends = cursor.fetchall()

        # Thêm một transaction giả để xử lý chia cổ tức
        for dividend in dividends:
            payment_date = pd.to_datetime(dividend['payment_date'])
            dividend_type = dividend['dividend_type']

            insert_index = 0
            for i, transaction in enumerate(transactions):

                if pd.to_datetime(transaction['transaction_date']) < payment_date:
                    insert_index += 1
                    continue
                break
                
            tax = 0.05
            current_quantity = ((transactions[insert_index - 1]['total_invest_value'] / 1000) /
                                 transactions[insert_index - 1]['avg_price'])
            if dividend_type == 'Stock':
                amount = float(dividend['stock_ratio_numerator'] / dividend['stock_ratio_denominator'])
                total_quan = transactions[insert_index - 1]['total_quantity'] * (1 + amount)
                avg_pric = transactions[insert_index - 1]['avg_price'] / (1 + amount)
                total_tax = current_quantity * amount * avg_pric * tax
            elif dividend_type == 'Cash':
                amount = dividend['cash_amount_per_share']
                avg_pric = transactions[insert_index - 1]['avg_price'] - amount
                total_tax = current_quantity * amount * tax
                total_quan = (transactions[insert_index - 1]['total_invest_value'] - total_tax) / avg_pric / 1000
            
            transactions.insert(insert_index, {
                'transaction_date': payment_date,
                'avg_price': avg_pric,
                'total_invest_value': transactions[insert_index - 1]['total_invest_value'] - total_tax,
                'total_quantity': total_quan,
                'transaction_type': 'BUY',
                'price_per_share': avg_pric * 1000,
                'quantity': total_quan
            })

        # Tính lợi nhuận
        avg_index_price = stock_price.loc[0, 'vnindex']
        total_index_quantity = transactions[0]['total_invest_value'] / avg_index_price
        index = 0
        for j, transaction in enumerate(transactions):
            if j == len(transactions) - 1:
                next_transaction_date = pd.to_datetime(datetime.date.today() + datetime.timedelta(days=1))
            else:
                next_transaction_date = pd.to_datetime(transactions[j + 1]['transaction_date'])

            avg_price = transaction['avg_price']

            for i in range(index, len(stock_price)):
                row = stock_price.loc[i]
                if row['time'] < next_transaction_date:
                    stock_price.loc[i, 'stock_profit'] = (row['close'] - avg_price)/avg_price * transaction['total_invest_value']
                    stock_price.loc[i, 'vnindex_profit'] = ((row['vnindex'] - avg_index_price)/avg_index_price *
                                                             transaction['total_invest_value'])
                    time = (row['time'] - pd.to_datetime(transactions[0]['transaction_date'])).days
                    if time < 0:
                        time = 0
                        bank_profit = 0
                    elif i > 0:
                        bank_profit = (transaction['total_invest_value'] + sum(stock_price['bank_profit'][:i])) * (math.pow(1.06, 1/365) - 1) + stock_price['bank_profit'][i - 1]
                    else:
                        bank_profit = (transaction['total_invest_value'] + sum(stock_price['bank_profit'][:i])) * (math.pow(1.06, 1/365) - 1)
                    stock_price.loc[i, 'bank_profit'] = bank_profit
                else:
                    if j == len(transactions) - 1:
                        break
                    # for next iteration
                    next_index_quantity  = ((transactions[j + 1]['total_invest_value'] - transaction['total_invest_value'])
                                             / stock_price.loc[i - 1, 'vnindex'])

                    total_index_quantity += next_index_quantity
                    avg_index_price = (transactions[j + 1]['total_invest_value']) / total_index_quantity
                    index = i
                    break
            mask = stock_price['time'] < pd.to_datetime(transactions[0]['transaction_date'])
            stock_price.loc[mask, 'stock_profit'] = 0
            stock_price.loc[mask, 'vnindex_profit'] = 0
            stock_price.loc[mask, 'bank_profit'] = 0
            ic(stock_price['bank_profit'])
        return stock_price

    stock_price = calculate_pure_profit(stock_price, transactions)
    return stock_price

pd.set_option('display.max_rows', None)


def prepare_data(user_id=None):
    stock_prices = get_stock_prices(user_id)
    if not stock_prices:
        return None
    for i in range(len(stock_prices)):
        stock_prices[i] = prepare_stock_price(stock_prices[i])
        stock_prices[i] = prepare_stock_profit(stock_prices[i], 1)
    df = pd.DataFrame()
    df['time'] = stock_prices[0]['time']
    df['profit'] = 0
    df['vnindex_profit'] = 0
    df['bank_profit'] = 0
    for i in range(len(stock_prices)):
        df['profit'] += stock_prices[i]['stock_profit']
        df['vnindex_profit'] += stock_prices[i]['vnindex_profit']
        df['bank_profit'] += stock_prices[i]['bank_profit']
    return df

def plot():
    data = prepare_data(user_id=1)
    if data is None:
        print("No data to plot")
        return
    ic(data)
    fig, ax = plt.subplots()
    ax.plot(data['time'], data['profit'], label='My Portfolio Profit', color='green')
    ax.plot(data['time'], data['vnindex_profit'], label='VNIndex Profit', color='blue')
    ax.plot(data['time'], data['bank_profit'], label='Bank Profit (6% per year)', color='red')
    ax.legend()
    plt.show()

plot()
