"""Score one prompt on the moral-outrage sample with GPT-6 Luna on Bedrock."""

from __future__ import annotations

import pandas as pd
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from cookbooks.how_to_use_wandb.shared.setup.dataloader import SAMPLE_ROWS, DataLoader
from shared.aws.s3 import DEFAULT_REGION_NAME

MODEL_ID = "us.openai.gpt-6-luna"
TEXT_COLUMN = "text"
GOLD_COLUMN = "outrage"
MAX_TOKENS = 1024
RETRY_ATTEMPTS = 5


class MoralOutrageLabel(BaseModel):
    """Whether one post expresses moral outrage."""

    moral_outrage: bool = Field(
        description="True when the post expresses moral outrage."
    )


def evaluate(prompt: str, *, n_rows: int = SAMPLE_ROWS) -> dict[str, float]:
    """Return f1, accuracy, precision, and recall for the positive class.

    Loads rows through ``DataLoader``. ``n_rows`` up to 1,000 uses the first
    rows of the sample file. A larger ``n_rows`` loads the full CSV first.
    """
    if n_rows <= 0:
        raise ValueError(f"n_rows must be positive, got {n_rows}")

    frame = _load_rows(n_rows)
    labeler = _labeler()
    instruction = prompt.strip()
    gold = [int(value) for value in frame[GOLD_COLUMN].tolist()]
    predictions: list[int] = []
    row_count = len(frame)
    for index, text in enumerate(frame[TEXT_COLUMN].astype(str).tolist()):
        predictions.append(_label_one(labeler, instruction, text))
        scored = index + 1
        if scored % 100 == 0 or scored == row_count:
            print(f"scored {scored}/{row_count}", flush=True)
    return _classification_report(gold, predictions)


def _load_rows(n_rows: int) -> pd.DataFrame:
    mode = "sample" if n_rows <= SAMPLE_ROWS else "full"
    frame = DataLoader().load_data(mode).head(n_rows)
    missing = {TEXT_COLUMN, GOLD_COLUMN} - set(frame.columns)
    if missing:
        raise ValueError(f"Training CSV is missing columns: {sorted(missing)}")
    if len(frame) != n_rows:
        raise ValueError(f"Expected {n_rows} rows, got {len(frame)}")
    if frame[GOLD_COLUMN].isna().any() or frame[TEXT_COLUMN].isna().any():
        raise ValueError("Training CSV has empty text or outrage values")
    return frame


def _labeler() -> Runnable:
    """Return a chat model that parses each post into ``MoralOutrageLabel``.

    Bedrock uses the AWS CLI credential chain.
    """
    chat = ChatBedrockConverse(
        model=MODEL_ID,
        region_name=DEFAULT_REGION_NAME,
        max_tokens=MAX_TOKENS,
        max_retries=RETRY_ATTEMPTS,
    )
    return chat.with_structured_output(MoralOutrageLabel)


def _label_one(labeler: Runnable, prompt: str, text: str) -> int:
    parsed = labeler.invoke([SystemMessage(content=prompt), HumanMessage(content=text)])
    if not isinstance(parsed, MoralOutrageLabel):
        raise TypeError(f"Expected MoralOutrageLabel, got {type(parsed)}")
    return int(parsed.moral_outrage)


def _classification_report(gold: list[int], pred: list[int]) -> dict[str, float]:
    if len(gold) != len(pred):
        raise ValueError("gold and pred must have the same length")
    true_positive = 0
    false_positive = 0
    false_negative = 0
    true_negative = 0
    for gold_label, pred_label in zip(gold, pred, strict=True):
        if gold_label == 1 and pred_label == 1:
            true_positive += 1
        elif gold_label == 0 and pred_label == 1:
            false_positive += 1
        elif gold_label == 1 and pred_label == 0:
            false_negative += 1
        else:
            true_negative += 1
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    return {
        "f1": _ratio(2 * precision * recall, precision + recall),
        "accuracy": _ratio(
            true_positive + true_negative,
            true_positive + true_negative + false_positive + false_negative,
        ),
        "precision": precision,
        "recall": recall,
    }


def _ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
