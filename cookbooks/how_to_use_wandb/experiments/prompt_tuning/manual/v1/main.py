"""Log one manual prompt run to Weights and Biases."""

import wandb
from evaluate import MODEL_ID, evaluate
from prompt import PROMPT

from lib.load_env_vars import EnvVarsContainer

EnvVarsContainer.get_env_var("WANDB_API_KEY", required=True)

ENTITY = "mind_technology_lab"
PROJECT = "how-to-use-wandb-manual-prompt-tuning"
PROMPT_ID = "moral-outrage-prompt-v1"
N_ROWS = 1000

with wandb.init(
    entity=ENTITY,
    project=PROJECT,
    name=PROMPT_ID,
    tags=["manual", PROMPT_ID],
    config={
        "prompt_id": PROMPT_ID,
        "prompt": PROMPT.strip(),
        "model": MODEL_ID,
        "dataset": "26k_training_data.csv",
        "sample": "first_1000",
        "n_rows": N_ROWS,
    },
) as run:
    metrics = evaluate(PROMPT, n_rows=N_ROWS)
    run.log(metrics)
