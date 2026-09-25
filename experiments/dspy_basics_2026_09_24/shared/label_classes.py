"""Structured labels for TweetEval tasks."""

from typing import Literal

from pydantic import BaseModel, Field

IronyName = Literal["non_irony", "irony"]


class IronyClassification(BaseModel):
    """Whether a tweet is ironic."""

    label: IronyName = Field(
        description="irony if the tweet is ironic, otherwise non_irony."
    )
