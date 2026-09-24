
import snowflake.connector
#from snowflake.snowpark import Session
import json
import boto3
# Establish a connection
#load_dotenv()  # Load environment variables from .env file

def load_aws_secrets(SecretId):
    client = boto3.client(
        service_name='secretsmanager',
        region_name='us-east-2'
    )
    response = client.get_secret_value(
        #SecretId='gmap_scraper/SNOWFLAKE_CONFIG'
        SecretId='gmap_scraper/{0}'.format(SecretId)
    )
    secret_data = json.loads(response["SecretString"])
    return secret_data

def getConn():
    client=boto3.client(
        service_name='secretsmanager',
        region_name='us-east-2'
    )
    response = client.get_secret_value(
        SecretId='gmap_scraper/SNOWFLAKE_CONFIG'
    )
    connection_options = json.loads(response["SecretString"])

    conn = snowflake.connector.connect(**connection_options)
    cursor = conn.cursor()
    """
    try:
        cursor.execute("SELECT CURRENT_VERSION(),CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA()")
        print(cursor.fetchone())
    except Exception as e:
        print(f"Error executing query: {e}")
    """
    cursor.execute("ALTER SESSION SET TIMEZONE = 'Asia/Taipei'")
    return conn

#getConn()
if __name__ == "__main__":
    print(load_aws_secrets("SNOWFLAKE_CONFIG"))
    acc=load_aws_secrets("CWA_APIKEY")

    print(load_aws_secrets("CWA_APIKEY"))
    account = acc.get("CWA_APIKEY")
    print(account)
