import json
import boto3
from botocore.exceptions import ClientError

def get_secret(secret_name, region_name="us-east-1"):
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        # Retrieve the secret value
        response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://amazon.com
        print(f"Error retrieving secret: {e}")
        raise e

    # Secrets Manager can store secrets as either a string or binary
    if 'SecretString' in response:
        secret = response['SecretString']
        
        # If your secret is stored as Key/Value pairs, it will be a JSON string.
        # You can parse it into a Python dictionary like this:
        try:
            return json.loads(secret)
        except json.JSONDecodeError:
            return secret  # Return plain text if it's not JSON
            
    else:
        # If the secret is binary, decode it
        import base64
        return base64.b64decode(response['SecretBinary'])

# --- How to use it ---
# Replace 'my_secret_name' with your actual secret identifier or ARN
MY_SECRET_NAME = "my_secret_name" 
AWS_REGION = "us-east-1"

secret_data = get_secret(MY_SECRET_NAME, AWS_REGION)

# If it's a JSON object, access keys directly:
if isinstance(secret_data, dict):
    username = secret_data.get("username")
    password = secret_data.get("password")
    print(f"Username: {username}")
else:
    print(f"Secret: {secret_data}")
