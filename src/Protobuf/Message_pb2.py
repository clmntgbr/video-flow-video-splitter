# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: Message.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\rMessage.proto\x12\x0c\x41pp.Protobuf\"?\n\x13\x41piToSoundExtractor\x12(\n\x08mediaPod\x18\x01 \x01(\x0b\x32\x16.App.Protobuf.MediaPod\"?\n\x13SoundExtractorToApi\x12(\n\x08mediaPod\x18\x01 \x01(\x0b\x32\x16.App.Protobuf.MediaPod\"B\n\x16\x41piToSubtitleGenerator\x12(\n\x08mediaPod\x18\x01 \x01(\x0b\x32\x16.App.Protobuf.MediaPod\"B\n\x16SubtitleGeneratorToApi\x12(\n\x08mediaPod\x18\x01 \x01(\x0b\x32\x16.App.Protobuf.MediaPod\"?\n\x13\x41piToSubtitleMerger\x12(\n\x08mediaPod\x18\x01 \x01(\x0b\x32\x16.App.Protobuf.MediaPod\"?\n\x13SubtitleMergerToApi\x12(\n\x08mediaPod\x18\x01 \x01(\x0b\x32\x16.App.Protobuf.MediaPod\"D\n\x18\x41piToSubtitleIncrustator\x12(\n\x08mediaPod\x18\x01 \x01(\x0b\x32\x16.App.Protobuf.MediaPod\"D\n\x18SubtitleIncrustatorToApi\x12(\n\x08mediaPod\x18\x01 \x01(\x0b\x32\x16.App.Protobuf.MediaPod\"\x8a\x01\n\x08MediaPod\x12\x0c\n\x04uuid\x18\x01 \x01(\t\x12\x10\n\x08userUuid\x18\x02 \x01(\t\x12*\n\roriginalVideo\x18\x03 \x01(\x0b\x32\x13.App.Protobuf.Video\x12\"\n\x05video\x18\x04 \x01(\x0b\x32\x13.App.Protobuf.Video\x12\x0e\n\x06status\x18\x05 \x01(\t\"\xa0\x01\n\x05Video\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x10\n\x08mimeType\x18\x02 \x01(\t\x12\x0c\n\x04size\x18\x03 \x01(\x03\x12\x0e\n\x06length\x18\x04 \x01(\x03\x12\x10\n\x08subtitle\x18\x05 \x01(\t\x12\x11\n\tsubtitles\x18\x06 \x03(\t\x12\x0e\n\x06\x61udios\x18\x07 \x03(\t\x12$\n\x06preset\x18\x08 \x01(\x0b\x32\x14.App.Protobuf.Preset\"`\n\x06Preset\x12\x14\n\x0csubtitleFont\x18\x01 \x01(\t\x12\x14\n\x0csubtitleSize\x18\x02 \x01(\t\x12\x15\n\rsubtitleColor\x18\x03 \x01(\t\x12\x13\n\x0bvideoFormat\x18\x04 \x01(\tB*\xca\x02\x0c\x41pp\\Protobuf\xe2\x02\x18\x41pp\\Protobuf\\GPBMetadatab\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'Message_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  DESCRIPTOR._serialized_options = b'\312\002\014App\\Protobuf\342\002\030App\\Protobuf\\GPBMetadata'
  _APITOSOUNDEXTRACTOR._serialized_start=31
  _APITOSOUNDEXTRACTOR._serialized_end=94
  _SOUNDEXTRACTORTOAPI._serialized_start=96
  _SOUNDEXTRACTORTOAPI._serialized_end=159
  _APITOSUBTITLEGENERATOR._serialized_start=161
  _APITOSUBTITLEGENERATOR._serialized_end=227
  _SUBTITLEGENERATORTOAPI._serialized_start=229
  _SUBTITLEGENERATORTOAPI._serialized_end=295
  _APITOSUBTITLEMERGER._serialized_start=297
  _APITOSUBTITLEMERGER._serialized_end=360
  _SUBTITLEMERGERTOAPI._serialized_start=362
  _SUBTITLEMERGERTOAPI._serialized_end=425
  _APITOSUBTITLEINCRUSTATOR._serialized_start=427
  _APITOSUBTITLEINCRUSTATOR._serialized_end=495
  _SUBTITLEINCRUSTATORTOAPI._serialized_start=497
  _SUBTITLEINCRUSTATORTOAPI._serialized_end=565
  _MEDIAPOD._serialized_start=568
  _MEDIAPOD._serialized_end=706
  _VIDEO._serialized_start=709
  _VIDEO._serialized_end=869
  _PRESET._serialized_start=871
  _PRESET._serialized_end=967
# @@protoc_insertion_point(module_scope)
