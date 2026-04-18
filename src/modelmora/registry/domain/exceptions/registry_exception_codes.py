from enum import Enum


class RegistryExceptionCodes(str, Enum):
    INVALID_MODEL = "invalid_model"
    MODEL_ALREADY_EXISTS = "model_already_exists"
    MODEL_NOT_FOUND = "model_not_found"
