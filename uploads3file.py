import logging
import boto3
from botocore.exceptions import ClientError
import os

queue_url = "https://sqs.us-east-2.amazonaws.com/127007033369/scraper_result"
def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        if object_name is not None:
            logging.info(f"Uploading file {file_name} to bucket {bucket} with object name {object_name}")
            s3_client.upload_file(file_name, bucket, object_name)
            logging.info(f"File uploaded successfully to {bucket}/{object_name}")
            send_sqs_message(queue_url, f"{object_name}")

    except ClientError as e:
        logging.error(e)
        return False
    return True

def send_sqs_message(queue_url, message_body):
    """Send a message to an SQS queue
    :param queue_url: URL of the SQS queue
    :param message_body: Message body to send
    :return: True if message was sent, else False
    """
    queue_url = queue_url
    sqs_client = boto3.client('sqs')
    try:

        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=message_body
        )
        logging.info(f"Message sent successfully to {queue_url}. Message ID: {response['MessageId']}")
        return True

    except ClientError as e:
        logging.error(e)
        return False

from pathlib import Path
from datetime import datetime


def create_temp_dir():
    base_dir = Path(__file__).resolve().parent / "tmp"
    dir_name = datetime.now().strftime("%Y%m%d%H")

    temp_dir = base_dir / dir_name
    temp_dir.mkdir(parents=True, exist_ok=True)
    return te

if __name__ == "__main__":
    create_temp_dir()