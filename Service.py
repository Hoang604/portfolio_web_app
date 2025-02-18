from model.User import User
from icecream import ic

class PortfolioService:
    def __init__(self, mydb):
        self.db = mydb

    def get_user_by_id(self, user_id):
        return User.get_by_id(user_id, self.db)

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
    
    def get_profit_data(self, user_id):
        sql_query = f"""
            SELECT
                date, total_investment, profit_percent, total_asset, total_asset_bank, total_asset_index
            FROM
                profit
            WHERE
                user_id = {user_id};
        """
        cursor = self.db.cursor(dictionary=True)
        cursor.execute(sql_query)
        datas = cursor.fetchall()
        for i in range(len(datas)):
            datas[i]['date'] = datas[i]['date'].strftime('%Y-%m-%d')

        return datas
    
    def get_injection_data(self, user_id):
        sql_query = f"""
            SELECT
                injection_date, amount
            FROM
                capital_injections
            WHERE
                user_id = {user_id}
            Order by injection_date DESC;
        """
        cursor = self.db.cursor(dictionary=True)
        cursor.execute(sql_query)
        datas = cursor.fetchall()
        for i in range(len(datas)):
            datas[i]['injection_date'] = datas[i]['injection_date'].strftime('%Y-%m-%d')

        return datas
    
    def get_transaction_data(self, user_id):
        sql_query = f"""
            SELECT
                transaction_date, stock_code, quantity, price_per_share, transaction_type
            FROM
                transactions
            WHERE
                user_id = {user_id}
            Order by transaction_date DESC;
        """
        cursor = self.db.cursor(dictionary=True)
        cursor.execute(sql_query)
        datas = cursor.fetchall()
        for i in range(len(datas)):
            datas[i]['transaction_date'] = datas[i]['transaction_date'].strftime('%Y-%m-%d')

        return datas