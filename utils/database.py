import mysql.connector
import os

def connect_db():
    """Hàm kết nối đến cơ sở dữ liệu MySQL sử dụng environment variables"""
    try:
        print(os.environ.get("MYSQL_HOST"))
        mydb = mysql.connector.connect(
            host=os.environ.get("MYSQL_HOST"),
            port=os.environ.get("MYSQL_PORT"),
            user=os.environ.get("MYSQL_USER"),
            password=os.environ.get("MYSQL_PASSWORD"),
            database=os.environ.get("MYSQL_DATABASE")
        )

        print("Connected to database")
        return mydb
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None