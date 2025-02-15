import mysql.connector

def connect_db():
    """Hàm kết nối đến cơ sở dữ liệu MySQL"""
    try:
        mydb = mysql.connector.connect(
            host="localhost",
            user="Hoang",
            password="Hoangdeptry_05",
            database="portfolio"
        )
        print("Connected to database")
        return mydb
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None