from enum import Enum


class TaskTypeEnum(str, Enum):
    TXT2EMBED = "txt2embed"
    TXT2TXT = "txt2txt"
    TXT2IMG = "txt2img"
    IMG2TXT = "img2txt"
    IMG2IMG = "img2img"
    AUDIO2TXT = "audio2txt"
    TXT2AUDIO = "txt2audio"
    CLASSIFICATION = "classification"
    OBJECT_DETECTION = "object_detection"
    QUESTION_ANSWERING = "question_answering"
