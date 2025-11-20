import json
import os
from typing import Any, ClassVar, Dict, TypeVar

import yaml
from pydantic import BaseModel

T = TypeVar("T", bound="BaseConfig")


class BaseConfig(BaseModel):
    """Base configuration settings."""

    config_name: ClassVar[str] = "BaseConfig"

    @classmethod
    def from_env(cls: type[T]) -> T:
        """Create configuration instance from environment variables."""
        attributes: Dict[str, Any] = {}
        for field_name, field in cls.model_fields.items():
            env_value = os.getenv(f"{cls.config_name}_{field_name}".upper())
            if env_value is not None:
                # Try to parse JSON for list/dict types
                if env_value.startswith(("[", "{")):
                    try:
                        attributes[field_name] = json.loads(env_value)
                    except json.JSONDecodeError:
                        attributes[field_name] = env_value
                else:
                    attributes[field_name] = env_value
            elif field.is_required():
                raise ValueError(f"Environment variable '{field_name.upper()}' is required but not set.")
        return cls.model_validate(attributes)

    @classmethod
    def from_yaml(cls: type[T], file_path: str) -> T:
        """Create configuration instance from a YAML file."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file)
            if data is None:
                raise ValueError(f"YAML file '{file_path}' is empty or invalid.")
            return cls.model_validate(data)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Configuration file not found: {file_path}") from e
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML file '{file_path}': {e}") from e

    @classmethod
    def from_json(cls: type[T], file_path: str) -> T:
        """Create configuration instance from a JSON file."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            return cls.model_validate(data)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Configuration file not found: {file_path}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parsing JSON file '{file_path}': {e}") from e

    def __str__(self) -> str:
        """String representation of the configuration."""
        string_representation = f"{self.config_name} Configuration:\n"
        type_config = self.__class__
        for field_name, _ in type_config.model_fields.items():
            value = getattr(self, field_name)
            if issubclass(type(value), BaseConfig):
                nested_str = str(value).replace("\n", "\n  ")
                string_representation += f"{field_name}:\n  {nested_str}\n"
            else:
                string_representation += f"{field_name}: {str(value)}\n"
        return string_representation.strip()
