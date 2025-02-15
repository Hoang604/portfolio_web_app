import mysql.connector
from utils import stock_price

class User:
    def __init__(self, user_id=None, name=None, contact_info=None, cash_balance=0, created_at=None, updated_at=None, update_reason=None):
        self.user_id = user_id
        self.name = name
        self.contact_info = contact_info
        self.cash_balance = cash_balance
        self.created_at = created_at
        self.updated_at = updated_at
        self.update_reason = update_reason

    def save(self, mydb=None):
        """Lưu thông tin người dùng vào CSDL (thêm mới hoặc cập nhật)."""
        if not mydb: return False
        try:
            cursor = mydb.cursor()
            if self.user_id is None:
                sql = "INSERT INTO users (name, contact_info, cash_balance) VALUES (%s, %s, %s)"
                val = (self.name, self.contact_info, self.cash_balance)
            else:
                sql = "UPDATE users SET name=%s, contact_info=%s, cash_balance=%s WHERE user_id=%s"
                val = (self.name, self.contact_info, self.cash_balance, self.user_id)
            cursor.execute(sql, val)
            mydb.commit()
            if self.user_id is None: self.user_id = cursor.lastrowid
            print(f"User save: {self.name} (ID: {self.user_id})")
            return True
        except mysql.connector.Error as err: print(f"Error when save User: {err}"); mydb.rollback(); return False

    @staticmethod
    def get_by_id(user_id, mydb=None):
        if not mydb: return None
        try:
            cursor = mydb.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            return User(**result) if result else None
        except mysql.connector.Error as err: print(f"Error get_by_id User: {err}"); return None

    @staticmethod
    def get_all(mydb=None):
        if not mydb: return []
        try:
            cursor = mydb.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users")
            results = cursor.fetchall()
            return [User(**row) for row in results]
        except mysql.connector.Error as err: print(f"Error get_all Users: {err}"); return []

    def delete(self, mydb=None):
        if not self.user_id: print("User don't have ID, cannot delete."); return False
        if not mydb: return False
        try:
            cursor = mydb.cursor()
            cursor.execute("DELETE FROM users WHERE user_id = %s", (self.user_id,))
            mydb.commit()
            print(f"User ID: {self.user_id} has been deleted.")
            return True
        except mysql.connector.Error as err: print(f"Error when delete User: {err}"); mydb.rollback(); return False

    def get_portfolio_holdings_view(self, mydb=None):
        """
        Lấy thông tin chi tiết về danh mục cổ phiếu từ bảng portfolio_holdings,
        kết hợp với giá hiện tại từ get_current_stock_price().

        Returns:
            list of dict: Danh sách các dictionary, mỗi dictionary đại diện cho một dòng
                          trong view, hoặc một list rỗng nếu có lỗi hoặc không có dữ liệu.
        """
        if not self.user_id:
            print("Không thể lấy portfolio holdings cho User chưa có ID.")
            return []

        if not mydb:
            return []

        try:
            cursor = mydb.cursor(dictionary=True)

            sql_query = """
                SELECT
                    s.stock_code,
                    s.company_name,
                    ph.current_quantity,
                    ph.average_cost
                FROM
                    portfolio_holdings ph
                JOIN
                    stocks s ON ph.stock_code = s.stock_code
                WHERE
                    ph.user_id = %s
                ORDER BY
                    s.stock_code;
            """

            cursor.execute(sql_query, (self.user_id,))
            db_results = cursor.fetchall()

            portfolio_view = []
            for row_data in db_results:
                stock_code = row_data['stock_code']
                average_cost = row_data['average_cost']
                current_quantity = row_data['current_quantity']

                current_price = stock_price.get_current_stock_price(stock_code).iloc[0] if not stock_price.get_current_stock_price(stock_code).empty else None
                total_profit_cash = 0
                total_profit_percentage = 0

                if current_price is not None:
                    total_profit_cash = current_quantity * (current_price - average_cost)
                    if average_cost > 0:
                        total_profit_percentage = ((current_price - average_cost) / average_cost) * 100

                portfolio_view.append({
                    'stock_code': stock_code,
                    'company_name': row_data['company_name'],
                    'current_quantity': current_quantity,
                    'average_cost': average_cost,
                    'current_price': current_price,
                    'total_profit_in_cash': total_profit_cash,
                    'total_profit_in_percentage': round(total_profit_percentage,2)
                })

            return portfolio_view

        except mysql.connector.Error as err:
            print(f"Lỗi khi lấy portfolio holdings view cho User {self.name}: {err}")
            return []

    def get_overall_perfomance_view(self, mydb=None):
        """
        Lấy thông tin tổng quan về hiệu suất đầu tư của User từ bảng transactions.

        Returns:
            dict: Dictionary chứa thông tin tổng quan về hiệu suất đầu tư của User,
                  hoặc một dictionary rỗng nếu có lỗi hoặc không có dữ liệu.
        """
        if not self.user_id:
            print("Không thể lấy overall performance cho User chưa có ID.")
            return {}
        if not mydb:
            return {}

        try:
            cursor = mydb.cursor(dictionary=True)

            sql_query = """
                SELECT cash_balance
                FROM users
                WHERE user_id = %s"""
            cursor.execute(sql_query, (self.user_id,))
            db_results = cursor.fetchone()
            cash_balance = db_results['cash_balance'] if db_results else 0
            
            sql_query = """
                SELECT COALESCE(SUM(amount), 0) AS total_investment_value
                from capital_injections
                WHERE user_id = %s"""
            cursor.execute(sql_query, (self.user_id,))
            db_results = cursor.fetchone()
            total_investment_value = db_results['total_investment_value'] if db_results else 0
            
            sql_query = """
                SELECT stock_code, current_quantity
                from portfolio_holdings
                WHERE user_id = %s"""
            cursor.execute(sql_query, (self.user_id,))
            db_results = cursor.fetchall()
            total_current_value = 0
            for row in db_results:
                stock_code = row['stock_code']
                current_quantity = row['current_quantity']
                current_price_series = stock_price.get_current_stock_price(stock_code)
                current_price = current_price_series.values[0] if not current_price_series.empty else None
                if current_price is not None:
                    total_current_value += current_quantity * current_price

            current_asset_value = total_current_value + cash_balance

            return {
                'user_id': self.user_id,
                'name': self.name,
                'total_investment_value': total_investment_value,
                'cash_balance': cash_balance,
                'total_current_value': total_current_value,
                'total_profit_in_cash': current_asset_value - total_investment_value,
                'total_profit_in_percentage': round(((current_asset_value - total_investment_value) / total_investment_value) * 100, 2),
                'total_asset_value': current_asset_value
            }
        except mysql.connector.Error as err:
            print(f"Lỗi khi lấy overall performance cho User {self.name}: {err}")
            return {}

    def __str__(self):
        return f"User(ID: {self.user_id}, Name: {self.name}, Contact: {self.contact_info})"