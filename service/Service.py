from portfolio_web_app.model.User import User
from portfolio_web_app.model.Stock import Stock
from portfolio_web_app.model.CapitalInjection import CapitalInjection
from portfolio_web_app.model.Transaction import Transaction
from icecream import ic

class PortfolioService:
    def __init__(self, mydb):
        self.db = mydb

    def save_user(self, name, contact_info):
        user = User(name=name, contact_info=contact_info)
        if user.save(self.db):
            print("User saved successfully")
        else:
            print("Failed to save user")

    def save_stock(self, stock_code, company_name):
        stock = Stock(stock_code=stock_code, company_name=company_name)
        if stock.save(self.db):
            print("Stock saved successfully")
        else:
            print("Failed to save stock")

    def save_capital_injection(self, user_id, amount, description, injection_date):
        capital_injection = CapitalInjection(user_id=user_id, amount=amount, description=description, injection_date=injection_date)
        if capital_injection.save(self.db):
            print("Capital Injection saved successfully")
        else:
            print("Failed to save capital injection")

    def save_transaction(self, user_id, stock_code, transaction_date, transaction_type, quantity, price):
        transaction = Transaction(
            user_id=user_id,
            stock_code=stock_code,
            transaction_date=transaction_date,
            transaction_type=transaction_type,
            quantity=quantity,
            price_per_share=price
        )
        if transaction.save(self.db):
            print("Transaction saved successfully")
        else:
            print("Failed to save transaction")

    def get_user_by_id(self, user_id):
        return User.get_by_id(user_id, self.db)

    def get_users_dropdown_data(self):
        users = User.get_all(self.db)
        return {user.name: user.user_id for user in users}

    def get_stocks_dropdown_data(self):
        stocks = Stock.get_all(self.db)
        return [stock.stock_code for stock in stocks]

    def get_user_performance_data(self, user_id):
        user = User.get_by_id(user_id=user_id, mydb=self.db)
        user_perf = user.get_overall_perfomance_view(self.db)
        return user_perf
    
    def get_overall_performance_data(self):
        
        users = User.get_all(self.db)
        
        performance_data = []
        for user in users:
            try:
                
                user_perf = user.get_overall_perfomance_view(mydb=self.db)
                performance_data.append(user_perf)
            except Exception as e:
                print(f"Error getting performance for user {user.user_id}: {e}")
        return performance_data

    def get_portfolio_holdings_data(self, user_id):
        user = User.get_by_id(user_id, self.db)
        if user:
            return user.get_portfolio_holdings_view(mydb=self.db)
        return None
    
    def update_stock_for_dividend(self, stock_code, payment_date=None, type=None, amount=None):
        stock = Stock.get_by_id(stock_code, self.db)
        if stock:
            if type == 'Cash':
                stock.cash_dividend(amount=amount, payment_date=payment_date, mydb=self.db)
            elif type == 'Stock':
                stock.stock_dividend(numerator=amount, denominator=100, payment_date=payment_date, mydb=self.db)
        else:
            print("Stock not found")