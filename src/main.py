import os
import ffmpeg
from kombu import Queue
from flask import Flask
from celery import Celery

from src.config import Config
from src.s3_client import S3Client
from src.rabbitmq_client import RabbitMQClient
from src.file_client import FileClient
from src.converter import ProtobufConverter
from src.Protobuf.Message_pb2 import (
    ApiToVideoFormatter,
    MediaPod,
    VideoFormatStyle,
    MediaPodStatus,
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
    protobuf = ApiToVideoFormatter()
    protobuf.mediaPod.CopyFrom(mediaPod)
    protobuf.IsInitialized()

    uuid = os.path.splitext(protobuf.mediaPod.originalVideo.name)[0]
    type = os.path.splitext(protobuf.mediaPod.originalVideo.name)[1]

    key = f"{protobuf.mediaPod.userUuid}/{protobuf.mediaPod.uuid}/{protobuf.mediaPod.originalVideo.name}"
    tmpVideoPath = f"/tmp/{uuid}{type}"
    tmpProcessedVideoPath = f"/tmp/{uuid}_processed{type}"
    keyProcessed = (
        f"{protobuf.mediaPod.userUuid}/{protobuf.mediaPod.uuid}/{uuid}_processed{type}"
    )

    protobuf.mediaPod.processedVideo.CopyFrom(protobuf.mediaPod.originalVideo)
    protobuf.mediaPod.processedVideo.name = f"{uuid}_processed{type}"

    if not s3_client.download_file(key, tmpVideoPath):
        return False

    if protobuf.mediaPod.configuration.format == VideoFormatStyle.Name(
        VideoFormatStyle.ORIGINAL
    ):
        if not s3_client.upload_file(tmpVideoPath, keyProcessed):
            return False

    if protobuf.mediaPod.configuration.format == VideoFormatStyle.Name(
        VideoFormatStyle.ZOOMED_916
    ):
        if not convert_to_zoomed_916(tmpVideoPath, tmpProcessedVideoPath):
            return False
        if not s3_client.upload_file(tmpProcessedVideoPath, keyProcessed):
            return False
        file_client.delete_file(tmpProcessedVideoPath)

    file_client.delete_file(tmpVideoPath)

    protobuf.mediaPod.status = MediaPodStatus.Name(
        MediaPodStatus.VIDEO_FORMATTER_COMPLETE
    )
    rmq_client.send_message(protobuf, "App\\Protobuf\\VideoFormatterToApi")

    return True


def convert_to_zoomed_916(input_video, output_video):
    probe = ffmpeg.probe(input_video)
    video_stream = next(
        (stream for stream in probe["streams"] if stream["codec_type"] == "video"), None
    )

    if not video_stream:
        raise ValueError("video_stream error on parameters.")

    width = int(video_stream["width"])
    height = int(video_stream["height"])
    new_width = int((9 / 16) * height)
    crop_x = max(0, (width - new_width) // 2)

    ffmpeg.input(input_video).filter("crop", new_width, height, crop_x, 0).output(
        output_video,
        vcodec="libx264",
        crf=23,
        preset="fast",
        acodec="aac",
        audio_bitrate="128k",
        map="0:a",
    ).run()

    return True
