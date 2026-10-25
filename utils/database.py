import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
import os
import logging
from dotenv import load_dotenv

load_dotenv()

_db_pool = None


def get_db_pool() -> MySQLConnectionPool:
    """Initializes and returns a thread-safe MySQLConnectionPool instance."""
    global _db_pool
    if _db_pool is None:
        try:
            port_val = os.environ.get("MYSQL_PORT")
            port = int(port_val) if port_val else 3306
            _db_pool = MySQLConnectionPool(
                pool_name="portfolio_pool",
                pool_size=10,
                host=os.environ.get("MYSQL_HOST"),
                port=port,
                user=os.environ.get("MYSQL_USER"),
                password=os.environ.get("MYSQL_PASSWORD"),
                database=os.environ.get("MYSQL_DATABASE")
            )
            logging.info("MySQL Connection Pool initialized successfully.")
        except mysql.connector.Error as err:
            logging.critical(f"Failed to initialize MySQL Connection Pool: {err}")
            raise err
    return _db_pool
