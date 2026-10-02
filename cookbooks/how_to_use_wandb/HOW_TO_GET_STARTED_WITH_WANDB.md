# How to get started with Weights and Biases

The first loop in the cookbook is one prompt at a time. You write a prompt and you tag the run. You run the prompt and you read the score in Weights and Biases. Then you write a second prompt and you tag the second run. You run the second prompt and you read the second score next to the first score.

Each prompt attempt is one run. You keep the data, the model, and the metric fixed, and you change the prompt. Both runs show up as rows in the same project, on the team that belongs to the organization `mind_technology_lab-org`.

You implement the scoring yourself. The steps below are the tracking loop around that scoring.

## How the organization fits together

Your login can see two places to put runs.

The organization `mind_technology_lab-org` is the account. It holds billing and membership. Inside it, the team is `mind_technology_lab`. A team is the shared workspace, and projects live on the team. The string you pass to `wandb.init` is the team name. Weights and Biases calls that string the entity. Your default entity is already `mind_technology_lab`, so a run with `entity="mind_technology_lab"` is a run inside `mind_technology_lab-org`. The project URL will look like `https://wandb.ai/mind_technology_lab/<project>`.

`mind_technology_lab-org` is the organization name. It is the parent of the team. Pass `mind_technology_lab` as `entity`.

You also have a personal entity, `markptorres1`, and that one belongs to a separate organization, `markptorres1-org`. A run logged there stays on the personal account. For this cookbook, set `entity` in code so the run stays on the lab team even if a later machine has a different default.

A project is a list of runs under one team. A run is one execution. For this loop, one prompt is one run. Weights and Biases creates the project the first time you call `wandb.init` with that project name, if you have permission to create projects on the team.

## What you hold still

The question is whether a prompt change moved the score. If the rows, the model, or the metric also change, you cannot tell which change moved it.

Use the moral-outrage CSV that `cookbooks/how_to_use_wandb/shared/setup/dataloader.py` loads. The text column is `text`. The gold label column is `outrage`, with `1` for outrage and `0` otherwise. `load_data("sample")` returns the first 1,000 rows of that file and writes `26k_training_data_1000.csv` beside the loader.

The September 19 comparison in `experiments/moral_outrage_classification_2026_09_19/` used a different 1,000 rows, a stratified sample with seed `20260919` (560 gold `0`, 440 gold `1`). On that sample, Jev scored F1 0.732 and the best Bedrock model scored F1 0.753. The F1 scores from the September 19 comparison describe the stratified sample. Your two prompt runs should be compared with each other, on the same rows.

Score the positive class, which is `1`, the same way `experiments/moral_outrage_classification_2026_09_19/shared/metrics.py` does. Log `f1`, `accuracy`, `precision`, and `recall`. If the model returns yes or no, map yes to `1` and no to `0`. If it returns a probability, treat a value of at least `0.5` as `1`.

Pick one model and leave it there for both prompts. Set temperature to `0`. Put the model id in the run config so the record shows that it did not change.

## The script

Run this from the repo root with `uv`, after the loader can read the CSV. `evaluate` is the function you write. It takes the prompt, scores the same rows, and returns the four metrics.

```python
import wandb

ENTITY = "mind_technology_lab"
PROJECT = "how-to-use-wandb-manual-prompt-tuning"
PROMPT_ID = "brady-v1"
PROMPT = (
    "Does this post express moral outrage? Moral outrage means all three of "
    "the following: (1) feelings about a perceived moral violation, (2) anger "
    "or disgust or contempt, and (3) blame or a wish to punish."
)

with wandb.init(
    entity=ENTITY,
    project=PROJECT,
    name=PROMPT_ID,
    tags=["manual", PROMPT_ID],
    config={
        "prompt_id": PROMPT_ID,
        "prompt": PROMPT,
        "model": "<the one model id you chose>",
        "dataset": "26k_training_data.csv",
        "sample": "first_1000",
        "n_rows": 1000,
    },
) as run:
    metrics = evaluate(PROMPT)  # {"f1", "accuracy", "precision", "recall"}
    run.log(metrics)
```

The Brady text above is the instruction the Bedrock runs already used, in `experiments/moral_outrage_classification_2026_09_19/shared/brady_definition.py`. Prompt 1 can be that text, so the first run is a known instruction. Prompt 2 is your rewrite.

## What each `wandb.init` argument means

`entity` is the team that owns the project. For the lab account, the team is `mind_technology_lab`. Weights and Biases uses it as the first part of the URL. Teammates on that team can open the project. A run with the personal entity `markptorres1` would show up under `https://wandb.ai/markptorres1/` instead, on `markptorres1-org`.

`project` is the name of the list that holds the prompt runs. Use one project for every manual prompt, so the runs share a page. `how-to-use-wandb-manual-prompt-tuning` is a name that stays with this cookbook and does not collide with the projects already on the team. You do not create the project in the UI first. The first successful `wandb.init` creates it.

`name` is the human-readable title of the run you are starting. It shows up in the runs table. It does not have to be unique. Weights and Biases also assigns a random run id, and that id is the unique address, in the form `mind_technology_lab/<project>/<run-id>`. Setting `name` to the prompt id, such as `brady-v1`, makes the table readable. If you omit `name`, Weights and Biases assigns a random title such as `earnest-sunset-1`.

`tags` is a list of short labels. Labels are for filtering and grouping. They are short on purpose. `manual` marks every run in this series, so you can later hide other work in the same project. The second tag is the prompt id, such as `brady-v1`, so you can jump to that attempt. You can add tags later in the UI, and you can pass them at the start so the label exists as soon as the run appears.

`config` is the dictionary of settings for this run. Weights and Biases stores it on the run and shows it on the Overview tab. You can filter and group runs by config values. The config is the record of what you ran. The tag is only the label you use to find the run.

The `with` block matters. When the block ends, Weights and Biases calls `finish` for you. `finish` marks the run finished and uploads the summary. If you call `wandb.init` without the `with` block, you need to call `run.finish()` yourself, or the run can sit in a running state after the script has exited.

## What each config field means

`prompt_id` is the short name of this prompt version, the same string you put in `name` and in the second tag. It is repeated in the config so a filter on config can find it even if someone later edits the tags in the UI. Use a new id for each new prompt. Reusing `brady-v1` for a rewritten prompt makes the table ambiguous, because two rows would share a name that no longer means one text.

`prompt` is the full instruction string you sent to the model. Store the whole string. A tag cannot hold it, and a short name cannot reconstruct it. When you open the run weeks later, Config is where you read the exact words that produced the score.

`model` is the id of the model that scored the rows, for example a Bedrock model id or `Qwen/Qwen3.5-4B`. It is a record that you held the model still. If two runs show different model ids, a higher F1 might be the model rather than the prompt.

`dataset` is the file the rows came from, `26k_training_data.csv`. It names the source table. `sample` and `n_rows` say which rows you scored.

`sample` is the rule that picked the rows. `first_1000` means `DataLoader.load_data("sample")`, which is the first 1,000 rows of the CSV in file order. If you later switch to the stratified sample from the September 19 experiment, change this field to something like `stratified_seed_20260919` on those runs. The field is how you tell the two samples apart in the table.

`n_rows` is how many rows `evaluate` actually scored. It should match the sample. If one run scores 50 rows and the next scores 1,000, the F1 values are answers to different questions. Put the count you really used. If you do a short smoke run of 20 rows to confirm the link works, set `n_rows` to 20 and use a prompt id that says so, such as `brady-v1-smoke`. Then run the real comparison at 1,000 rows with its own prompt ids.

## What `run.log` does

`run.log(metrics)` writes the four numbers once, at the end of the attempt. For a single evaluation there is no training curve. Weights and Biases still stores the call as the run history, and it copies the last logged value of each key into the run summary. The runs table shows the summary, so `f1`, `accuracy`, `precision`, and `recall` become columns you can sort.

The keys you pass are the column names. Log the same four keys on every run, with the same spelling. `f1` and `F1` would become two columns.

If the script raises an exception before `run.log`, the run still exists. Its state is failed or crashed, and its summary has no `f1`. Leave that run in the project. Fix the script and start a new `wandb.init`. A new init is a new run id, so the failed attempt stays as a record of the failure.

## Step 1. Confirm the login

In a terminal, run:

```bash
wandb status
```

You should see a settings printout whose `base_url` is `https://api.wandb.ai`. The command should finish without asking you to log in. The `entity` field in that printout can be empty. An empty settings entity means this machine has no entity saved in the local config file. The account default is still `mind_technology_lab`. The `entity` argument in the script is what places the run, so the empty settings field is fine.

If the command tells you to run `wandb login`, stop and log in before you score any rows. A script that starts without a login will try to prompt, or it will fail, and you will not get a project URL.

## Step 2. Run the first prompt

Set `PROMPT_ID` to `brady-v1` and set `PROMPT` to the Brady text. Fill in `model` with the one model you chose. Run the script from the repo root with `uv`.

While `evaluate` is working, the run already exists. Weights and Biases prints a syncing line and two links early, before the scores exist. The first link is the run. The second link is the project. You can open the run while scoring is still going. Overview will show the tags and the config immediately. Summary will gain `f1` only after `run.log` runs and the process finishes the upload.

When the script exits cleanly, the terminal prints the same two links again, plus a short summary of the logged keys and a local log path under `./wandb/`. The local folder is a copy on disk. The page at the run link is the copy you compare later.

Expect a new project if this is the first time you have used that project name. The project page has one row, titled `brady-v1`, tagged `manual` and `brady-v1`.

## Step 3. Read the first run

Open the run link from the terminal.

On the Overview tab, Tags should list `manual` and `brady-v1`. Config should list `prompt_id`, `prompt`, `model`, `dataset`, `sample`, and `n_rows`, and `prompt` should be the full Brady paragraph. Summary should list `f1`, `accuracy`, `precision`, and `recall` as numbers between 0 and 1. The state should be finished.

Also check the command and the git commit on the Overview tab. Weights and Biases records the command that started the run, and it records the git commit of the working directory when git information is available. The command and the git commit tell you which code produced the score. The prompt in config is still the record of the instruction, because the prompt may live only in a variable.

Then open the project link, `https://wandb.ai/mind_technology_lab/how-to-use-wandb-manual-prompt-tuning`. The workspace lists this run as one row. If the row is missing, the `entity` in the script and the entity in the URL differ. The URL's first segment should be `mind_technology_lab`.

## Step 4. Run the second prompt

Edit `PROMPT` to the new instruction. Set `PROMPT_ID` to a new short name, for example `shorter-v2`. Leave `ENTITY`, `PROJECT`, the model, `dataset`, `sample`, and `n_rows` as they were. Run the same script again.

That call creates a second run. It does not update the first one. Weights and Biases addresses a run as `entity/project/run-id`, and each `wandb.init` gets a new run id. The terminal prints a new run link. The project link stays the same.

Expect the project page to show two rows, `brady-v1` and `shorter-v2`. Both carry the tag `manual`. Each carries its own prompt id tag. Opening each run and reading `config.prompt` should show two different instruction strings, and `config.model`, `config.sample`, and `config.n_rows` should match.

## Step 5. Compare the two rows

On the project page, open Runs. You should see both prompt ids. If `f1` is hidden, add the summary fields `f1`, `accuracy`, `precision`, and `recall` as columns. Sort by `f1`. The higher row is the better prompt on this sample, for this model, at this row count.

To see only this series, use the filter above the table. Choose Tags, then "is", then `manual`. The same control filters to one prompt id, which is useful after you have more than two runs.

Click either row to open that run, and read Config to see the exact prompt that produced the score.

## The habit after the first two runs

Write a new prompt. Give it a new `PROMPT_ID`. Keep the tag `manual`. Keep the same 1,000 rows, the same model, and the same four metric keys. Run the script again, and read the new row next to the earlier ones.

A run whose config differs in `model`, `sample`, or `n_rows` is a different experiment. Give that run a tag other than a plain prompt id, or put it in another project, so a sort by `f1` stays a sort among comparable prompts.
