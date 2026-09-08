
import snowflake.connector
from snowflake.snowpark import Session
import os
# Establish a connection
def getConn():
    conn = snowflake.connector.connect(
        user='shahow11',#change to your snowflake username
        #password=os.getenv('SNOWFLAKE_PASSWORD'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        passcode="429849",
        account='evnwclk-nd59466',
        warehouse='COMPUTE_WH',
        database='HOTSPOT',
        schema='PUBLIC'
    )
    return conn

getConn()