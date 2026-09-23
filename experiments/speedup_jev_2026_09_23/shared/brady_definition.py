"""Shared Brady 2021 moral outrage instruction strings.

Run from the experiment folder:

    uv run python -c "from shared.brady_definition import BRADY_MORAL_OUTRAGE_INSTRUCTIONS; print(BRADY_MORAL_OUTRAGE_INSTRUCTIONS)"
"""

BRADY_MORAL_OUTRAGE_DEFINITION = (
    "Moral outrage means all three of the following: (1) feelings about a "
    "perceived moral violation, (2) anger or disgust or contempt, and (3) "
    "blame or a wish to punish."
)

BRADY_MORAL_OUTRAGE_INSTRUCTIONS = (
    "Does this post express moral outrage? " + BRADY_MORAL_OUTRAGE_DEFINITION
)
