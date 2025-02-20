import os
import re
from kombu import Queue
from flask import Flask
from celery import Celery

from src.config import Config
from src.s3_client import S3Client
from src.rabbitmq_client import RabbitMQClient
from src.file_client import FileClient
from src.converter import ProtobufConverter
from src.Protobuf.Message_pb2 import ApiToSubtitleTransformer, PresetSubtitleFont, Preset, MediaPodStatus

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
    protobuf: ApiToSubtitleTransformer = ProtobufConverter.json_to_protobuf(message)

    try:
        key = f"{protobuf.mediaPod.userUuid}/{protobuf.mediaPod.uuid}/{protobuf.mediaPod.originalVideo.subtitle}"
        uuid = os.path.splitext(protobuf.mediaPod.originalVideo.subtitle)[0]
        tmpSrtFilePath = f"/tmp/{uuid}.srt"
        tmpAssFilePath = f"/tmp/{uuid}.ass"

        print(tmpAssFilePath)
        print(tmpSrtFilePath)

        if not s3_client.download_file(key, tmpSrtFilePath):
            raise Exception
        
        with open(tmpSrtFilePath, "r", encoding="utf-8") as srt_file, open(tmpAssFilePath, "w", encoding="utf-8") as ass_file:
            ass_file.write(get_ass_header(protobuf.mediaPod.preset))

            srt_content = srt_file.read().strip()
            srt_blocks = re.split(r"\n\s*\n", srt_content)

            for block in srt_blocks:
                lines = block.split("\n")
                if len(lines) < 3:
                    continue

                start_time, end_time = lines[1].split(" --> ")
                start_time = srt_time_to_ass(start_time)
                end_time = srt_time_to_ass(end_time)

                text = " ".join(lines[2:])
                formatted_text = split_lines(text)

                ass_file.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{formatted_text}\n")
        
        key = f"{protobuf.mediaPod.userUuid}/{protobuf.mediaPod.uuid}/{uuid}.ass"
        if not s3_client.upload_file(tmpAssFilePath, key):
                raise Exception
        
        protobuf.mediaPod.originalVideo.ass = f"{uuid}.ass"
        protobuf.mediaPod.status = MediaPodStatus.Name(MediaPodStatus.SUBTITLE_TRANSFORMER_COMPLETE)

        file_client.delete_file(tmpAssFilePath)
        file_client.delete_file(tmpSrtFilePath)

        rmq_client.send_message(protobuf, "App\\Protobuf\\SubtitleTransformerToApi")
        return True
    except Exception as e:
        protobuf.mediaPod.status = MediaPodStatus.Name(MediaPodStatus.SUBTITLE_TRANSFORMER_ERROR)
        if not rmq_client.send_message(protobuf, "App\\Protobuf\\SubtitleTransformerToApi"):
            return False

def srt_time_to_ass(srt_time):
    h, m, s = srt_time.split(":")
    s, ms = s.split(",")
    return f"{int(h)}:{int(m):02}:{int(s):02}.{ms[:2]}"

def split_lines(text, max_words=4):
    words = text.split()
    mid = len(words) // 2 if len(words) > max_words else len(words)
    return " ".join(words[:mid]) + r"\N" + " ".join(words[mid:]) if len(words) > max_words else text

def get_ass_header(preset: Preset):
    return f"""
[Script Info]
ScriptType: v4.00+
PlayResX: 384
PlayResY: 288
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname, Fontsize,PrimaryColour, SecondaryColour,OutlineColour, BackColour, Bold, Italic, Underline,StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default, {get_subtitle_font(preset.subtitleFont)},{preset.subtitleSize}, {convert_color(preset.subtitleColor)}, {convert_color(preset.subtitleColor)}, {convert_color(preset.subtitleOutlineColor)},&H00000000, {preset.subtitleBold}, {preset.subtitleItalic},{preset.subtitleUnderline}, 0, 100, 100, 0, 0,1, {preset.subtitleOutlineThickness}, {1 if preset.subtitleShadow != "NONE" else 0},2,10,10,10,0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def get_subtitle_font(subtitleFont: str) -> str :
    if (subtitleFont == PresetSubtitleFont.Name(PresetSubtitleFont.TIMES_NEW_ROMAN)):
        return 'Times New Roman'
    if (subtitleFont == PresetSubtitleFont.Name(PresetSubtitleFont.COURIER_NEW)):
        return 'Courier New'
    return 'Arial'

def convert_color(hex_color):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return '&HFFFFFF'
    r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
    return f"&H{b}{g}{r}"
