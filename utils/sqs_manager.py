import json
import logging
import os

import boto3


class SQSManager:
    def __init__(self, queue_name: str = None):
        self.queue_name = queue_name
        self.region = os.getenv('AWS_REGION', 'eu-north-1')
        self.sqs = boto3.client('sqs', region_name=self.region)
        self.queue_url = None

    def create_publisher(self) -> None:
        logging.info(f"Connecting to SQS queue: {self.queue_name}")
        response = self.sqs.get_queue_url(QueueName=self.queue_name)
        self.queue_url = response['QueueUrl']
        logging.info(f"SQS publisher connected: {self.queue_url}")

    def send_message(self, message: dict) -> None:
        logging.info(f"Sending message to {self.queue_name}")
        self.sqs.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(message),
        )
        logging.info("Message sent.")

    def create_subscriber(self) -> None:
        logging.info(f"Connecting to SQS queue: {self.queue_name}")
        response = self.sqs.get_queue_url(QueueName=self.queue_name)
        self.queue_url = response['QueueUrl']
        logging.info(f"SQS subscriber connected: {self.queue_url}")

    def consume_messages(self):
        logging.info(f"Polling messages from {self.queue_name}...")
        response = self.sqs.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20,
        )
        for msg in response.get('Messages', []):
            self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=msg['ReceiptHandle'],
            )
            logging.info(f"Consumed message: {msg['Body'][:80]}...")
            yield json.loads(msg['Body'])
