from model.User import User

class PortfolioService:
    def __init__(self, mydb):
        self.db = mydb

    def get_user_by_id(self, user_id):
        return User.get_by_id(user_id, self.db)
    
    def get_overall_performance_data(self):
        
        users = User.get_all(self.db)
        
        performance_data = []
        for user in users:
            try:
                user_perf = user.get_overall_perfomance_view(mydb=self.db)
                user_perf.update(self.get_profit_data(user.user_id)[-1])
                pop_keys = ['date', 'total_asset_bank', 'total_asset_index', 'profit_percent']
                for key in pop_keys:
                    user_perf.pop(key)
                
                keys = ['total_investment', 'total_asset']
                for key in keys:
                    user_perf[key] = user_perf[key] * 1000
                user_perf['profit_in_cash'] = user_perf['total_asset'] - user_perf['total_investment']
                user_perf['profit_percent'] = user_perf['profit_in_cash'] / user_perf['total_investment'] * 100
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
                injection_date as date, amount
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
            datas[i]['date'] = datas[i]['date'].strftime('%Y-%m-%d')

        sql_query = f"""
            SELECT
                withdrawal_date as date, - amount as amount
            FROM
                capital_withdrawals
            WHERE
                user_id = {user_id}
            Order by withdrawal_date DESC;
        """
        cursor.execute(sql_query)
        withdrawal_datas = cursor.fetchall()
        for i in range(len(withdrawal_datas)):
            withdrawal_datas[i]['date'] = withdrawal_datas[i]['date'].strftime('%Y-%m-%d')
        datas += withdrawal_datas
        datas.sort(key=lambda x: x['date'], reverse=True)

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