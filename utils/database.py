import mysql.connector
import os

def connect_db():
    """Hàm kết nối đến cơ sở dữ liệu MySQL sử dụng environment variables"""
    try:
        print("MYSQL_HOST:", os.environ.get("MYSQL_HOST"))
        print("MYSQL_PORT:", os.environ.get("MYSQL_PORT"))
        print("MYSQL_USER:", os.environ.get("MYSQL_USER"))
        print("MYSQL_PASSWORD:", os.environ.get("MYSQL_PASSWORD"))
        print("MYSQL_DATABASE:", os.environ.get("MYSQL_DATABASE"))
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