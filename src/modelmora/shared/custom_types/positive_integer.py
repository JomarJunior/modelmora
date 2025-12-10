from typing import Annotated

from pydantic import Field

PositiveInteger = Annotated[
    int,
    Field(
        gt=0,
    ),
]
