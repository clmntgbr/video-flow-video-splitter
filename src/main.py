import re
from kombu import Queue
from flask import Flask
from celery import Celery

from src.config import Config
from src.s3_client import S3Client
from src.rabbitmq_client import RabbitMQClient
from src.file_client import FileClient
from src.converter import ProtobufConverter
from src.Protobuf.Message_pb2 import ApiToSubtitleMerger

app = Flask(__name__)
app.config.from_object(Config)
s3_client = S3Client(Config)
rmq_client = RabbitMQClient()
file_client = FileClient()

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
    apiToSubtitleMerger: ApiToSubtitleMerger = ProtobufConverter.json_to_protobuf(message)
    
    try:
        subtitles = []
        for subtitle in apiToSubtitleMerger.mediaPod.originalVideo.subtitles:
            key = f"{apiToSubtitleMerger.mediaPod.userUuid}/{apiToSubtitleMerger.mediaPod.uuid}/subtitles/{subtitle}"
            if not s3_client.download_file(key, f"/tmp/{subtitle}"):
                raise Exception
            subtitles.append(f"/tmp/{subtitle}")

        subtitles = sorted(subtitles, key=lambda x: int(re.search(r'_(\d+)\.srt$', x).group(1)))

        mergedSubtitles = []
        currentOffset = 0
        subtitleIndex = 1

        for file in subtitles:
            parseSubtitles = parse_srt(file)
            for _, timestamps, text in parseSubtitles:
                new_timestamps = shift_timestamps(timestamps, currentOffset)
                mergedSubtitles.append(f"{subtitleIndex}\n{new_timestamps}\n{text}\n\n")
                subtitleIndex += 1
            
            currentOffset += 300

        srtFile = apiToSubtitleMerger.mediaPod.originalVideo.name.replace(".mp4", ".srt")
        tmpSrtFilePath = f"/tmp/{srtFile}"
        with open(tmpSrtFilePath, 'w', encoding='utf-8') as f:
            f.writelines(mergedSubtitles)

        key = f"{apiToSubtitleMerger.mediaPod.userUuid}/{apiToSubtitleMerger.mediaPod.uuid}/{srtFile}"
        if not s3_client.upload_file(tmpSrtFilePath, key):
            raise Exception
        
        apiToSubtitleMerger.mediaPod.originalVideo.subtitle = srtFile
        apiToSubtitleMerger.mediaPod.status = 'subtitle_merger_complete'
        
        file_client.delete_file(tmpSrtFilePath)
        for subtitle in subtitles:
            file_client.delete_file(subtitle)

        rmq_client.send_message(apiToSubtitleMerger, "App\\Protobuf\\SubtitleMergerToApi")
        return True
    except Exception as e:
        apiToSubtitleMerger.mediaPod.status = 'subtitle_merger_error'
        if not rmq_client.send_message(apiToSubtitleMerger, "App\\Protobuf\\SubtitleMergerToApi"):
            return False

def parse_srt(tmpSrtFilePath):
    subtitles = []
    with open(tmpSrtFilePath, 'r', encoding='utf-8') as file:
        content = file.read().strip()
    
    entries = re.split(r'\n\n+', content)
    for entry in entries:
        lines = entry.split("\n")
        if len(lines) >= 3:
            num = int(lines[0])
            timestamps = lines[1]
            text = "\n".join(lines[2:])
            subtitles.append((num, timestamps, text))
    
    return subtitles

def shift_timestamps(timestamps, offset_seconds):
    def convertToMs(timestamp):
        match = re.match(r"(\d+):(\d+):(\d+),(\d+)", timestamp)
        if not match:
            raise ValueError(f"Format de timestamp invalide : {timestamp}")
        h, m, s, ms = map(int, match.groups())
        return (h * 3600 + m * 60 + s) * 1000 + ms
    
    def convertFromMs(ms):
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    start, end = timestamps.split(" --> ")
    start_ms = convertToMs(start) + offset_seconds * 1000
    end_ms = convertToMs(end) + offset_seconds * 1000
    return f"{convertFromMs(start_ms)} --> {convertFromMs(end_ms)}"
