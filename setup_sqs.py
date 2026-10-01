import logging
import boto3

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

REGION = 'eu-north-1'
QUEUES = ['truck-events', 'dock-events']

if __name__ == "__main__":
    sqs = boto3.client('sqs', region_name=REGION)

    for queue_name in QUEUES:
        try:
            url = sqs.get_queue_url(QueueName=queue_name)['QueueUrl']
            logging.info(f"Queue '{queue_name}' accesible: {url}")
        except Exception as e:
            logging.error(f"Queue '{queue_name}' NO accesible: {e}")

    logging.info("Done. Listing all queues:")
    for url in sqs.list_queues(QueueNamePrefix='').get('QueueUrls', []):
        logging.info(f"  {url}")
