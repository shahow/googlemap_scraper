import mariadb
import sys

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "你的MariaDB密碼",
    "database": "你的資料庫名稱"
}
def getConn():
    conn = mariadb.connect(**DB_CONFIG)
    return conn
