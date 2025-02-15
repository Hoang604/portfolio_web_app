import mysql.connector

class Transaction:
    def __init__(self, transaction_id=None, user_id=None, stock_code=None, transaction_type=None, quantity=None, price_per_share=None, transaction_date=None, create_at=None, updated_at=None):
        self.transaction_id = transaction_id
        self.user_id = user_id
        self.stock_code = stock_code
        self.transaction_type = transaction_type # 'BUY' or 'SELL'
        self.quantity = quantity
        self.price_per_share = price_per_share
        self.transaction_date = transaction_date # Should use datetime.date object
        self.create_at = create_at
        self.updated_at = updated_at

    def save(self, mydb=None):
        if not mydb: return False
        try:
            cursor = mydb.cursor()
            if self.transaction_id is None:
                sql = "INSERT INTO transactions (user_id, stock_code, transaction_type, quantity, price_per_share, transaction_date) VALUES (%s, %s, %s, %s, %s, %s)"
                val = (self.user_id, self.stock_code, self.transaction_type, self.quantity, self.price_per_share, self.transaction_date)
            else:
                sql = "UPDATE transactions SET user_id=%s, stock_code=%s, transaction_type=%s, quantity=%s, price_per_share=%s, transaction_date=%s WHERE transaction_id=%s"
                val = (self.user_id, self.stock_code, self.transaction_type, self.quantity, self.price_per_share, self.transaction_date, self.transaction_id)
            cursor.execute(sql, val)
            mydb.commit()
            if self.transaction_id is None: self.transaction_id = cursor.lastrowid
            print(f"Transaction saved (ID: {self.transaction_id})")
            return True
        except mysql.connector.Error as err: print(f"Error saving Transaction: {err}"); mydb.rollback(); return False

    @staticmethod
    def get_by_id(transaction_id, mydb=None):
        if not mydb: return None
        try:
            cursor = mydb.cursor(dictionary=True)
            cursor.execute("SELECT * FROM transactions WHERE transaction_id = %s", (transaction_id,))
            result = cursor.fetchone()
            return Transaction(**result) if result else None
        except mysql.connector.Error as err: print(f"Error getting Transaction by ID: {err}"); return None

    @staticmethod
    def get_all(mydb=None):
        if not mydb: return []
        try:
            cursor = mydb.cursor(dictionary=True)
            cursor.execute("SELECT * FROM transactions")
            results = cursor.fetchall()
            return [Transaction(**row) for row in results]
        except mysql.connector.Error as err: print(f"Error getting all Transactions: {err}"); return []

    def delete(self, mydb=None):
        if not self.transaction_id: print("Cannot delete Transaction without an ID."); return False
        if not mydb: return False
        try:
            cursor = mydb.cursor()
            cursor.execute("DELETE FROM transactions WHERE transaction_id = %s", (self.transaction_id,))
            mydb.commit()
            print(f"Transaction deleted (ID: {self.transaction_id})")
            return True
        except mysql.connector.Error as err: print(f"Error deleting Transaction: {err}"); mydb.rollback(); return False

    def __str__(self):
        return f"Transaction(ID: {self.transaction_id}, User ID: {self.user_id}, Stock ID: {self.stock_code}, Type: {self.transaction_type}, Qty: {self.quantity}, Price: {self.price_per_share}, Date: {self.transaction_date})"