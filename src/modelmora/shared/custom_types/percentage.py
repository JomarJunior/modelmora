from typing import Annotated

from pydantic import Field

"""We define Percentage as a float value between 0.0 and 100.0 inclusive.
This requires division by 100 when converting from a whole number percentage to a decimal representation.
For example, 75% should be represented as 75.0 in this type, and converted to 0.75 for calculations.
"""
Percentage = Annotated[
    float,
    Field(
        ge=0.0,
        le=100.0,
    ),
]
