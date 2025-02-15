import mysql.connector
from portfolio_management.model.User import User

class Stock:
    def __init__(self, stock_code=None, company_name=None, created_at=None, updated_at=None):
        self.stock_code = stock_code
        self.company_name = company_name
        self.created_at = created_at
        self.updated_at = updated_at

    def save(self, mydb=None):
        if not mydb: return False
        try:
            cursor = mydb.cursor()
            if self.stock_code is None:
                sql = "INSERT INTO stocks (stock_code, company_name) VALUES (%s, %s)"
                val = (self.stock_code, self.company_name)
            else:
                sql = "UPDATE stocks SET company_name=%s WHERE stock_code=%s"
                val = (self.company_name, self.stock_code)
            cursor.execute(sql, val)
            mydb.commit()
            print(f"Stock saved: {self.stock_code}")
            return True
        except mysql.connector.Error as err: print(f"Error saving Stock: {err}"); mydb.rollback(); return False

    @staticmethod
    def get_by_id(stock_code, mydb=None):
        if not mydb: return None
        try:
            cursor = mydb.cursor(dictionary=True)
            cursor.execute("SELECT * FROM stocks WHERE stock_code = %s", (stock_code,))
            result = cursor.fetchone()
            return Stock(**result) if result else None
        except mysql.connector.Error as err: print(f"Error getting Stock by ID: {err}"); return None

    @staticmethod
    def get_all(mydb=None):
        if not mydb: return []
        try:
            cursor = mydb.cursor(dictionary=True)
            cursor.execute("SELECT * FROM stocks")
            results = cursor.fetchall()
            return [Stock(**row) for row in results]
        except mysql.connector.Error as err: print(f"Error getting all Stocks: {err}"); return []
 
    def delete(self, mydb=None):
        if not self.stock_code: print("Cannot delete Stock without an ID."); return False
        if not mydb: return False
        try:
            cursor = mydb.cursor()
            cursor.execute("DELETE FROM stocks WHERE stock_code = %s", (self.stock_code,))
            mydb.commit()
            print(f"Stock deleted (ID: {self.stock_code})")
            return True
        except mysql.connector.Error as err: print(f"Error deleting Stock: {err}"); mydb.rollback(); return False

    def stock_dividend(self, numerator, denominator, payment_date, mydb=None):
        if not self.stock_code or not mydb:
            print("Cannot process dividend without stock code or database connection")
            return False
            
        try:
            cursor = mydb.cursor()
            sql_query = """
                INSERT INTO dividends 
                (stock_code, payment_date, dividend_type, 
                 stock_ratio_numerator, stock_ratio_denominator)
                VALUES (%s, %s, 'Stock', %s, %s)
            """
            cursor.execute(sql_query, (
                self.stock_code, 
                payment_date,
                numerator,
                denominator
            ))
            mydb.commit()
            print(f"Stock dividend recorded for {self.stock_code}")
            return True
        except mysql.connector.Error as err:
            print(f"Error recording stock dividend: {err}")
            return None
    
    def cash_dividend(self, amount, payment_date, mydb=None):
        if not self.stock_code or not mydb:
            print("Cannot process dividend without stock code or database connection")
            return False
            
        try:
            cursor = mydb.cursor()
            sql_query = """
                INSERT INTO dividends 
                (stock_code, payment_date, dividend_type, cash_amount_per_share)
                VALUES (%s, %s, 'Cash', %s)
            """
            cursor.execute(sql_query, (
                self.stock_code,
                payment_date, 
                amount
            ))
            mydb.commit()
            print(f"Cash dividend recorded for {self.stock_code}")
            return True
        except mysql.connector.Error as err:
            print(f"Error recording cash dividend: {err}")
            return None
    def __str__(self):
        return f"Stock(ID: {self.stock_code}, Code: {self.stock_code}, Company: {self.company_name})"
    
if __name__ == "__main__":
    stock = Stock.get_by_id('MBB')
    stock.stock_dividence(15)