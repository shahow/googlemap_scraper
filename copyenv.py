import json
import boto3
from dotenv import dotenv_values

SECRET_NAME = "gmap/snowflake"

# 讀取本機 .env
env = dotenv_values(".env")

# 只挑需要放進 Secrets Manager 的設定
secret_data = {
    "SNOWFLAKE_USER": env.get("SNOWFLAKE_USER"),
    "SNOWFLAKE_PASSWORD": env.get("SNOWFLAKE_PASSWORD"),
    "SNOWFLAKE_ACCOUNT": env.get("SNOWFLAKE_ACCOUNT"),
    "SNOWFLAKE_DATABASE": env.get("SNOWFLAKE_DATABASE"),
    "SNOWFLAKE_SCHEMA": env.get("SNOWFLAKE_SCHEMA"),
    "SNOWFLAKE_WAREHOUSE": env.get("SNOWFLAKE_WAREHOUSE"),
    "SNOWFLAKE_ROLE": env.get("SNOWFLAKE_ROLE"),
}

# AWS Secrets Manager
client = boto3.client("secretsmanager", region_name="ap-northeast-1")

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