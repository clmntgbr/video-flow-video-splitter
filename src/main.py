import os
import ffmpeg
import uuid

from kombu import Queue
from flask import Flask
from celery import Celery

from src.config import Config
from src.s3_client import S3Client
from src.rabbitmq_client import RabbitMQClient
from src.file_client import FileClient
from src.converter import ProtobufConverter
from src.Protobuf.Message_pb2 import (
    ApiToVideoSplitter,
    MediaPod,
    Video,
    MediaPodStatus
)

app = Flask(__name__)
app.config.from_object(Config)
s3_client = S3Client(Config)
rmq_client = RabbitMQClient()
file_client = FileClient()

celery = Celery("tasks", broker=app.config["RABBITMQ_URL"])

celery.conf.update(
    {
        "task_serializer": "json",
        "accept_content": ["json"],
        "broker_connection_retry_on_startup": True,
        "task_routes": {
            "tasks.process_message": {"queue": app.config["RMQ_QUEUE_WRITE"]}
        },
        "task_queues": [
            Queue(
                app.config["RMQ_QUEUE_READ"], routing_key=app.config["RMQ_QUEUE_READ"]
            )
        ],
    }
)


@celery.task(name="tasks.process_message", queue=app.config["RMQ_QUEUE_READ"])
def process_message(message):
    mediaPod: MediaPod = ProtobufConverter.json_to_protobuf(message)
    protobuf = ApiToVideoSplitter()
    protobuf.mediaPod.CopyFrom(mediaPod)
    protobuf.IsInitialized()

    id = os.path.splitext(protobuf.mediaPod.originalVideo.name)[0]
    type = os.path.splitext(protobuf.mediaPod.originalVideo.name)[1]

    keyProcessedVideo = f"{protobuf.mediaPod.userUuid}/{protobuf.mediaPod.uuid}/{protobuf.mediaPod.processedVideo.name}"
    tmpProcessedVideoPath = f"/tmp/{id}_processed{type}"
    
    if not s3_client.download_file(keyProcessedVideo, tmpProcessedVideoPath):
        return False
    
    probe = ffmpeg.probe(tmpProcessedVideoPath)
    duration = float(probe['format']['duration'])
    segment_duration = duration / int(protobuf.mediaPod.configuration.split)

    split_video(tmpProcessedVideoPath, id, type, int(protobuf.mediaPod.configuration.split), segment_duration)
    
    x = int(protobuf.mediaPod.configuration.split)
    for value in range(1, x + 1):
        size_in_bytes = os.path.getsize(f'/tmp/{id}_final_part_{value}{type}')
        video = Video(
            uuid=str(uuid.uuid4()),
            name=f'{id}_final_part_{value}{type}',
            mimeType=protobuf.mediaPod.processedVideo.mimeType,
            size=size_in_bytes,
            length=int(segment_duration),
        )

        if not s3_client.upload_file(f'/tmp/{id}_final_part_{value}{type}', f"{protobuf.mediaPod.userUuid}/{protobuf.mediaPod.uuid}/{id}_final_part_{value}{type}"):
            return False
        
        file_client.delete_file(f'/tmp/{id}_final_part_{value}{type}')
        protobuf.mediaPod.finalVideo.append(video)
    
    file_client.delete_file(tmpProcessedVideoPath)

    protobuf.mediaPod.status = MediaPodStatus.Name(
        MediaPodStatus.VIDEO_SPLITTER_COMPLETE
    )
    rmq_client.send_message(protobuf, "App\\Protobuf\\VideoSplitterToApi")

    return True

def split_video(input_file, id, type, parts, segment_duration):
    for i in range(parts):
        start_time = i * segment_duration
        output_file = os.path.join('/tmp', f'{id}_final_part_{i+1}{type}')
        ffmpeg.input(input_file, ss=start_time, t=segment_duration).output(output_file, c='copy').run(overwrite_output=True)
