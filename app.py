from flask import Flask, render_template
from utils.database import connect_db
from service.Service import PortfolioService

app = Flask(__name__)

service = PortfolioService(connect_db())

@app.route('/', methods=['GET'])
def home():
    users_performance = service.get_overall_performance_data()
    portfolio_data = {}
    for user_perfomance in users_performance:
        portfolio_data[user_perfomance['user_id']] = service.get_portfolio_holdings_data(user_perfomance['user_id'])
    return render_template('home.html', users_performance=users_performance, portfolio_data=portfolio_data)

@app.route('/user/<int:user_id>', methods=['GET'])
def portfolio(user_id):
    user = service.get_user_by_id(user_id=user_id)
    performance_data = service.get_user_performance_data(user_id=user_id)
    performance_data['total_investment_value'] = performance_data['total_investment_value'] / 1000
    performance_data['total_asset_value'] = performance_data['total_asset_value'] / 1000
    portfolio_data = service.get_portfolio_holdings_data(user_id=user_id)
    # Chuẩn bị dữ liệu cho biểu đồ tròn
    stock_values = {} # Dictionary để lưu trữ tổng giá trị cho mỗi mã cổ phiếu
    for holding in portfolio_data:
        stock_code = holding['stock_code']
        current_value = holding['current_price'] * holding['current_quantity'] # Tính giá trị hiện tại
        stock_values [stock_code] = current_value
    # Chuyển đổi dictionary sang dạng list để dễ dùng trong template
    chart_labels = list(stock_values.keys())
    chart_data = list(stock_values.values())

    return render_template('user_profile.html',
                       performance_data=performance_data,
                       user=user,
                       portfolio_data=portfolio_data,
                       chart_labels=chart_labels, # Truyền labels cho biểu đồ
                       chart_data=chart_data)     # Truyền data cho biểu đồ
if __name__ == '__main__':
    app.run()