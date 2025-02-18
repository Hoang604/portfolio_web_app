from model.User import User

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