from typing import Annotated

from pydantic import Field

from modelmora.shared.constants.bytes_constants import BYTE
from modelmora.shared.constants.power_of_two_constants import TWO_TO_THE_16

BigString = Annotated[
    str,
    Field(
        min_length=1,
        max_length=TWO_TO_THE_16 * BYTE,
    ),
]
