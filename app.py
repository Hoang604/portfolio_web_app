from flask import Flask, render_template
from utils.database import connect_db
from Service import PortfolioService
import logging

# Cấu hình logging: ghi log vào file 'app.log' với level DEBUG
logging.basicConfig(filename='/tmp/app.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(lineno)d - %(message)s')

logging.info('Ứng dụng Flask app.py bắt đầu khởi tạo...') # Log khi ứng dụng bắt đầu chạy

app = Flask(__name__)

logging.info('Kết nối đến database...') # Log trước khi kết nối database
try:
    db = connect_db()
    logging.info('Kết nối database thành công.') # Log nếu kết nối thành công
except Exception as e:
    logging.error(f'Lỗi kết nối database: {e}') # Log lỗi nếu kết nối thất bại
    # Có thể quyết định xử lý lỗi ở đây, ví dụ như dừng ứng dụng nếu không có database
    # raise e # Tái raise exception nếu muốn dừng ứng dụng khi lỗi database

logging.info('Khởi tạo PortfolioService...') # Log trước khi khởi tạo service
try:
    service = PortfolioService(db)
    logging.info('PortfolioService khởi tạo thành công.') # Log nếu service khởi tạo thành công
except Exception as e:
    logging.error(f'Lỗi khởi tạo PortfolioService: {e}') # Log lỗi nếu service không khởi tạo được
    # Tương tự, có thể xử lý lỗi ở đây nếu service không khởi tạo được
    # raise e

logging.info('Ứng dụng Flask app.py đã khởi tạo xong.') # Log khi ứng dụng khởi tạo xong

@app.route('/', methods=['GET'])
def home():
    logging.info('Route "/" (home) được gọi.') # Log khi route home được gọi
    try:
        users_performance = service.get_overall_performance_data()
        portfolio_data = {}
        for user_perfomance in users_performance:
            portfolio_data[user_perfomance['user_id']] = service.get_portfolio_holdings_data(user_perfomance['user_id'])
        logging.debug('Dữ liệu users_performance và portfolio_data đã được lấy thành công.') # Log debug khi lấy dữ liệu thành công
        return render_template('home.html', users_performance=users_performance, portfolio_data=portfolio_data)
    except Exception as e:
        logging.error(f'Lỗi trong route "/": {e}') # Log lỗi nếu có lỗi trong route
        return "Đã có lỗi xảy ra khi tải trang chủ.", 500 # Trả về thông báo lỗi cho người dùng (có thể tùy chỉnh)
    finally:
        logging.info('Route "/" (home) đã hoàn thành xử lý.') # Log khi route home hoàn thành

@app.route('/user/<int:user_id>', methods=['GET'])
def portfolio(user_id):
    logging.info(f'Route "/user/{user_id}" (portfolio) được gọi cho user_id: {user_id}.') # Log khi route portfolio được gọi
    try:
        user = service.get_user_by_id(user_id=user_id)
        performance_data = service.get_user_performance_data(user_id=user_id)
        performance_data['total_investment_value'] = performance_data['total_investment_value'] / 1000
        performance_data['total_asset_value'] = performance_data['total_asset_value'] / 1000
        portfolio_data = service.get_portfolio_holdings_data(user_id=user_id)
        stock_values = {}
        for holding in portfolio_data:
            stock_code = holding['stock_code']
            current_value = holding['current_price'] * holding['current_quantity']
            stock_values [stock_code] = current_value
        chart_labels = list(stock_values.keys())
        chart_data = list(stock_values.values())
        logging.debug(f'Dữ liệu cho user_id {user_id} đã được lấy thành công.') # Log debug khi lấy dữ liệu thành công
        return render_template('user_profile.html',
                           performance_data=performance_data,
                           user=user,
                           portfolio_data=portfolio_data,
                           chart_labels=chart_labels,
                           chart_data=chart_data)
    except Exception as e:
        logging.error(f'Lỗi trong route "/user/<user_id>": {e}') # Log lỗi nếu có lỗi trong route
        return "Đã có lỗi xảy ra khi tải trang hồ sơ người dùng.", 500 # Trả về thông báo lỗi
    finally:
        logging.info(f'Route "/user/{user_id}" (portfolio) đã hoàn thành xử lý cho user_id: {user_id}.') # Log khi route portfolio hoàn thành

if __name__ == '__main__':
    logging.info('Chuẩn bị gọi app.run() ...') # Log ngay trước app.run()
    app.run(debug=True, host='0.0.0.0', port=8080) # Để app có thể truy cập từ bên ngoài localhost
    logging.info('app.run() đã hoàn thành (nếu có)...') # Log ngay sau app.run() - có thể không bao giờ được gọi khi app chạy liên tục