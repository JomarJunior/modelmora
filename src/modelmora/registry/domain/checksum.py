from typing import Annotated

from pydantic import Field

from modelmora.shared.custom_types import ShortString

Checksum = Annotated[
    ShortString,
    Field(
        description="SHA256 checksum comprised of 64 hexadecimal characters prefixed with 'sha256:'.",
        pattern=r"^sha256:[a-fA-F0-9]{64}$",
    ),
]
