import os
from kombu import Queue
from flask import Flask
from celery import Celery
from src.config import Config
from src.s3_client import S3Client
from src.rabbitmq_client import RabbitMQClient
from src.converter import ProtobufConverter
from src.Protobuf.Message_pb2 import ApiToSoundExtractor

app = Flask(__name__)
app.config.from_object(Config)
s3_client = S3Client(Config)
rmq_client = RabbitMQClient()

celery = Celery(
    'tasks',
    broker=app.config['RABBITMQ_URL']
)

celery.conf.update({
    'task_serializer': 'json',
    'accept_content': ['json'],
    'broker_connection_retry_on_startup': True,
    'task_routes': {
        'tasks.process_message': {'queue': app.config['RMQ_QUEUE_WRITE']}
    },
    'task_queues': [
        Queue(app.config['RMQ_QUEUE_READ'], routing_key=app.config['RMQ_QUEUE_READ'])
    ],
})

@celery.task(name='tasks.process_message', queue=app.config['RMQ_QUEUE_READ'])
def process_message(message):
    apiToSoundExtractor: ApiToSoundExtractor = ProtobufConverter.json_to_protobuf(message)

    key = f"{apiToSoundExtractor.mediaPod.userUuid}/{apiToSoundExtractor.mediaPod.uuid}/{apiToSoundExtractor.mediaPod.originalVideo.name}"
    tmpFilePath = f"/tmp/{apiToSoundExtractor.mediaPod.originalVideo.name}"
    uuid = os.path.splitext(os.path.basename(tmpFilePath))[0]

    s3_client.download_file(key, tmpFilePath)

    rmq_client.send_message(apiToSoundExtractor, "App\\Protobuf\\SoundExtractorApi")
