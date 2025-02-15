import os
import re
import ffmpeg

from kombu import Queue
from flask import Flask
from celery import Celery
from pydub import AudioSegment

from src.config import Config
from src.s3_client import S3Client
from src.rabbitmq_client import RabbitMQClient
from src.file_client import FileClient
from src.converter import ProtobufConverter
from src.Protobuf.Message_pb2 import ApiToSoundExtractor

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
    apiToSoundExtractor: ApiToSoundExtractor = ProtobufConverter.json_to_protobuf(message)

    try:
        key = f"{apiToSoundExtractor.mediaPod.userUuid}/{apiToSoundExtractor.mediaPod.uuid}/{apiToSoundExtractor.mediaPod.originalVideo.name}"
        tmpFilePath = f"/tmp/{apiToSoundExtractor.mediaPod.originalVideo.name}"
        uuid = os.path.splitext(os.path.basename(tmpFilePath))[0]

        if not s3_client.download_file(key, tmpFilePath):
            return False

        audioFilePath = uuid + ".mp3"
        tmpAudioFilePath = f"/tmp/{audioFilePath}"
        
        probe = ffmpeg.probe(tmpFilePath)
        duration = float(probe['format']['duration'])

        if not extract_sound(tmpFilePath, tmpAudioFilePath):
            return False

        audioFilePath = convert_to_wav(tmpAudioFilePath)

        chunks = chunk_wav(audioFilePath, uuid)

        for chunk in chunks:
            key = f"{apiToSoundExtractor.mediaPod.userUuid}/{apiToSoundExtractor.mediaPod.uuid}/audios/{chunk}"
            if not s3_client.upload_file(f"/tmp/{chunk}", key):
                return False
            file_client.delete_file(f"/tmp/{chunk}")

        file_client.delete_file(tmpAudioFilePath)
        file_client.delete_file(tmpFilePath)

        resultsSorted = sorted(chunks, key=extract_chunk_number)

        apiToSoundExtractor.mediaPod.originalVideo.length = int(duration)
        apiToSoundExtractor.mediaPod.originalVideo.audios.extend(resultsSorted)
        apiToSoundExtractor.mediaPod.status = 'sound_extractor_complete'
        
        rmq_client.send_message(apiToSoundExtractor, "App\\Protobuf\\SoundExtractorApi")

        return True
    except Exception as e:
        apiToSoundExtractor.mediaPod.status = 'sound_extractor_error'
        if not rmq_client.send_message(apiToSoundExtractor, "App\\Protobuf\\SoundExtractorApi"):
            return False

def extract_sound(file: str, audioFilePath: str) -> bool:
    try:
        ffmpeg.input(file).output(f"{audioFilePath}").run()
        print(f"audio successfully extracted: {audioFilePath}")
        return True
    except Exception as e:
        print(f"error extracting audio: {e}")
    return False

def extract_chunk_number(item):
    match = re.search(r'_(\d+)\.wav$', item[0])
    return int(match.group(1)) if match else float('inf')

def convert_to_wav(audioFilePath) -> str:
    audio = AudioSegment.from_mp3(audioFilePath)
    wav_path = audioFilePath.replace(".mp3", ".wav")
    audio.export(wav_path, format="wav", parameters=["-ac", "1", "-ar", "16000"]) 
    return wav_path

def chunk_wav(audioFilePath: str, uuid: str) -> list[str]: 
    audio = AudioSegment.from_mp3(audioFilePath)
    segmentDuration = 5 * 60 * 1000
    chunkFilenames = []

    chunks = [audio[i:i+segmentDuration] for i in range(0, len(audio), segmentDuration)]
    for idx, chunk in enumerate(chunks):
        chunk.export(f"/tmp/{uuid}_{idx+1}.wav", format="wav")
        chunkFilenames.append(f"{uuid}_{idx+1}.wav")

    return chunkFilenames
