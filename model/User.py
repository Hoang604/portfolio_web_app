import mysql.connector


class User:
    def __init__(self, id=None, name=None, contact_info=None, cash_balance=0, total_investment=0, created_at=None, updated_at=None, update_reason=None):
        self.id = id
        self.name = name
        self.contact_info = contact_info
        self.cash_balance = cash_balance
        self.total_investment = total_investment
        self.created_at = created_at
        self.updated_at = updated_at
        self.update_reason = update_reason

    @staticmethod
    def get_by_id(id, mydb=None):
        if not mydb:
            return None
        try:
            cursor = mydb.cursor(dictionary=True)
            cursor.execute("SELECT * FROM portfolio_user WHERE id = %s", (id,))
            result = cursor.fetchone()
            return User(**result) if result else None
        except mysql.connector.Error as err:
            print(f"Error get_by_id User: {err}")
            return None

    @staticmethod
    def get_all(mydb=None) -> list['User']:
        if not mydb:
            return []
        try:
            cursor = mydb.cursor(dictionary=True)
            cursor.execute("SELECT * FROM portfolio_user")
            results = cursor.fetchall()
            return [User(**row) for row in results]
        except mysql.connector.Error as err:
            print(f"Error get_all Users: {err}")
            return []

    def __str__(self):
        return f"User(ID: {self.id}, Name: {self.name}, Contact: {self.contact_info})"