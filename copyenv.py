import json
import boto3
from dotenv import dotenv_values

SECRET_NAME = "gmap_scraper/SNOWFLAKE_CONFIG"

# 讀取本機 .env
env = dotenv_values(".env")

# 只挑需要放進 Secrets Manager 的設定
    
secret_data = {
    "user": env.get("SNOWFLAKE_USER"),
    "password": env.get("SNOWFLAKE_SERVICE_AGENT_TOKEN"),
    "account": env.get("SNOWFLAKE_ACCOUNT"),
    "database": env.get("SNOWFLAKE_DATABASE"),
    "schema": env.get("SNOWFLAKE_SCHEMA"),
    "warehouse": env.get("SNOWFLAKE_WAREHOUSE"),
    "role": env.get("SNOWFLAKE_ROLE"),
}

# AWS Secrets Manager
client = boto3.client("secretsmanager", region_name="us-east-2")

try:
    response = client.create_secret(
        Name=SECRET_NAME,
        SecretString=json.dumps(secret_data)
    )

    print("Secret created:")
    print(response["ARN"])

except client.exceptions.ResourceExistsException:
    print(f"Secret already exists: {SECRET_NAME}")

    response = client.put_secret_value(
        SecretId=SECRET_NAME,
        SecretString=json.dumps(secret_data)
    )

    print("Secret value updated.")