import mysql.connector

class CapitalInjection:
    def __init__(self, capital_injection_id=None, user_id=None, injection_date=None, amount=None, description=None, created_at=None, updated_at=None):
        self.capital_injection_id = capital_injection_id
        self.user_id = user_id
        self.injection_date = injection_date # Should use datetime.date object
        self.amount = amount
        self.description = description
        self.created_at = created_at
        self.updated_at = updated_at

    def save(self, mydb=None):
        if not mydb: return False
        try:
            cursor = mydb.cursor()
            if self.capital_injection_id is None:
                sql = "INSERT INTO capital_injections (user_id, injection_date, amount, description) VALUES (%s, %s, %s, %s)"
                val = (self.user_id, self.injection_date, self.amount, self.description)
            else:
                sql = "UPDATE capital_injections SET user_id=%s, injection_date=%s, amount=%s, description=%s WHERE capital_injection_id=%s"
                val = (self.user_id, self.injection_date, self.amount, self.description, self.capital_injection_id)
            cursor.execute(sql, val)
            mydb.commit()
            if self.capital_injection_id is None: self.capital_injection_id = cursor.lastrowid
            print(f"CapitalInjection saved (ID: {self.capital_injection_id})")
            return True
        except mysql.connector.Error as err: print(f"Error saving CapitalInjection: {err}"); mydb.rollback(); return False

    @staticmethod
    def get_by_id(capital_injection_id, mydb=None):
        if not mydb: return None
        try:
            cursor = mydb.cursor(dictionary=True)
            cursor.execute("SELECT * FROM capital_injections WHERE capital_injection_id = %s", (capital_injection_id,))
            result = cursor.fetchone()
            return CapitalInjection(**result) if result else None
        except mysql.connector.Error as err: print(f"Error getting CapitalInjection by ID: {err}"); return None

    @staticmethod
    def get_all(mydb=None):
        if not mydb: return []
        try:
            cursor = mydb.cursor(dictionary=True)
            cursor.execute("SELECT * FROM capital_injections")
            results = cursor.fetchall()
            return [CapitalInjection(**row) for row in results]
        except mysql.connector.Error as err: print(f"Error getting all CapitalInjections: {err}"); return []

    def delete(self, mydb=None):
        if not self.capital_injection_id: print("Cannot delete CapitalInjection without an ID."); return False
        if not mydb: return False
        try:
            cursor = mydb.cursor()
            cursor.execute("DELETE FROM capital_injections WHERE capital_injection_id = %s", (self.capital_injection_id,))
            mydb.commit()
            print(f"CapitalInjection deleted (ID: {self.capital_injection_id})")
            return True
        except mysql.connector.Error as err: print(f"Error deleting CapitalInjection: {err}"); mydb.rollback(); return False

    def __str__(self):
        return f"CapitalInjection(ID: {self.capital_injection_id}, User ID: {self.user_id}, Date: {self.injection_date}, Amount: {self.amount}, Description: {self.description})"