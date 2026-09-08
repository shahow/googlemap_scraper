
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

    print("Account:", account)
    print("Token loaded:", bool(token))
    print("Token length:", len(token) if token else 0)

    conn = snowflake.connector.connect(
        user='HOTSPOT_AGENT',#change to your snowflake username
        password=os.getenv('SNOWFLAKE_SERVICE_AGENT_TOKEN'),
        #account=os.getenv('SNOWFLAKE_ACCOUNT'),
        account='evnwclk-nd59466',
        warehouse='COMPUTE_WH',
        database='HOTSPOT',
        schema='PUBLIC'
    )
    print("Connected to Snowflake")
    return conn

getConn()