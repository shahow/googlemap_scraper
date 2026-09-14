
import snowflake.connector
from snowflake.snowpark import Session
from dotenv import load_dotenv
import os
# Establish a connection
#load_dotenv()  # Load environment variables from .env file
def getConn():
    load_dotenv( dotenv_path=r"C:\Users\User\gmap_test\.env")
    account = os.getenv("SNOWFLAKE_ACCOUNT")
    token = os.getenv("SNOWFLAKE_SERVICE_AGENT_TOKEN")

    connection_options = dict(
        user='HOTSPOT_AGENT',#change to your snowflake username
        password=token,
        account=account,
        warehouse='COMPUTE_WH',
        database='GMAP_DB',
        schema='PUBLIC'
    )
    role = os.getenv("SNOWFLAKE_ROLE")
    if role:
        connection_options["role"] = role

    conn = snowflake.connector.connect(**connection_options)
    cursor = conn.cursor()

    cursor.execute("ALTER SESSION SET TIMEZONE = 'Asia/Taipei'")
    return conn

getConn()
