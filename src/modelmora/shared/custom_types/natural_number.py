from typing import Annotated

from pydantic import Field

NaturalNumber = Annotated[
    int,
    Field(
        ge=0,
    ),
]
