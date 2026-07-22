import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
from contextlib import contextmanager
from typing import Generator
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


@contextmanager
def get_db_connection() -> Generator[mysql.connector.MySQLConnection, None, None]:
    """Context manager yielding a connection from the pool and automatically releasing it back."""
    pool = get_db_pool()
    conn = pool.get_connection()
    try:
        yield conn
    finally:
        conn.close()


def connect_db():
    """Backward-compatible function returning a connection from the pool."""
    try:
        pool = get_db_pool()
        return pool.get_connection()
    except Exception as err:
        logging.error(f"Error getting connection from pool: {err}")
        return None