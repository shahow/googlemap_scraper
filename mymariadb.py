import mariadb
import sys

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "AaBb123",
    "database": "hotspot"
}
def getConn():
    conn = mariadb.connect(**DB_CONFIG)
    return conn
