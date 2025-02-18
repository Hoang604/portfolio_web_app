from flask import Flask, render_template
from utils.database import connect_db
from Service import PortfolioService

app = Flask(__name__)

# Kết nối database và khởi tạo PortfolioService
db = connect_db()
service = PortfolioService(db)

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
    stock_values = {}
    for holding in portfolio_data:
        stock_code = holding['stock_code']
        current_value = holding['current_price'] * holding['current_quantity']
        stock_values[stock_code] = current_value
    cursor = db.cursor()
    cursor.execute(f"SELECT cash_balance FROM users WHERE user_id = {user_id}")
    cash_balance = cursor.fetchone()
    cash_balance = float(cash_balance[0])
    stock_values['Cash'] = cash_balance
    chart_labels = list(stock_values.keys())
    chart_data = list(stock_values.values())

    profit_data = service.get_profit_data(user_id)
    profit_chart_labels = []
    profit_chart_total_asset = []
    profit_chart_total_asset_bank = []
    profit_chart_total_asset_index = []
    profit_chart_total_investment = []
    for data in profit_data:
        profit_chart_labels.append(data['date'])
        profit_chart_total_asset.append(data['total_asset'])
        profit_chart_total_asset_bank.append(data['total_asset_bank'])
        profit_chart_total_asset_index.append(data['total_asset_index'])
        profit_chart_total_investment.append(data['total_investment'])

    profit_chart_profit_percent = profit_data[-1]['profit_percent']
    transaction_data = service.get_transaction_data(user_id)
    injection_data = service.get_injection_data(user_id)

    return render_template('user_profile.html',
                           performance_data=performance_data,
                           transaction_data=transaction_data,
                           injection_data=injection_data,
                           user=user,
                           portfolio_data=portfolio_data,
                           chart_labels=chart_labels,
                           chart_data=chart_data,
                           profit_chart_labels=profit_chart_labels,
                           profit_chart_total_asset=profit_chart_total_asset,
                           profit_chart_total_asset_bank=profit_chart_total_asset_bank,
                           profit_chart_total_asset_index=profit_chart_total_asset_index,
                           profit_chart_total_investment=profit_chart_total_investment,
                           profit_chart_profit_percent=profit_chart_profit_percent)

# Định nghĩa custom filter cho Jinja2
@app.template_filter('thousands')
def thousands_filter(value):
    try:
        # Ép kiểu về float và định dạng với dấu phẩy phân cách hàng nghìn, không có chữ số thập phân
        return "{:,.0f}".format(float(value))
    except (ValueError, TypeError):
        return value
if __name__ == '__main__':
    app.run()