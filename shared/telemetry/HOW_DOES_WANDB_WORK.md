# How Weights & Biases works here

We use Weights & Biases (`wandb`) to track our AI/ML training runs. We store this shared tooling in `shared/telemetry/wandb.py`.

You start a Weights & Biases run through `shared.telemetry.wandb.start_run`. You pass the project, the group, and the run name. The organization and the team are already set in [wandb.py](./wandb.py), and they stay the same for every experiment that calls `start_run`.

## What you pass in

```python
from shared.telemetry.wandb import start_run

with start_run(
    project="predict_keep_remove_jev_gepa_2026_09_23",
    group="jev_gepa_rebuilt",
    name="R5_gepa_original_test_eval",
) as run:
    run.log({"accuracy": 0.91})
```

`start_run` also accepts an optional `config` dictionary. Put the inputs there, e.g. the learning rate. You store the dictionary on the run, so you can filter the table by the learning rate later.

`start_run` sets `WANDB_ORGANIZATION`, `WANDB_ENTITY`, `WANDB_PROJECT`, `WANDB_RUN_GROUP`, and `WANDB_NAME` for the rest of the process.

## Organization and team

Wandb requires us to pass in a value for `Organization` and `Team`. This is already pre-configured to use lab-wide defaults.

**Organization.** The organization is `mind_technology_lab-org`. An organization is the account that holds the lab's teams, billing, and admin settings. You don't pass the organization when you call `start_run`, because `start_run` sets the organization.

**Entity.** The entity is `mind_technology_lab`. An entity is the username or the team name that owns projects, and the entity is the first part of a run URL. A team is the shared workspace inside the organization. `start_run` sets the entity to `mind_technology_lab`, so you store the run in the shared workspace.

## Project, group, run name, and run id

**Project.** A project is the set of runs you want in one table and on the same charts. You choose the project name, and the project name is the middle part of the run URL. Give a new dated experiment its own project. Existing examples in the `Wandb` entity include `predict_keep_remove_jev_gepa_2026_09_23` and `dspy_gepa_optimization_2026_09_30` .

**Group.** A group is a label on runs inside one project that belong to one experiment. You choose the group name. Use the same project and the same group when the runs are variants of one experiment, e.g. a training run next to its evaluation run. In the table, you can expand runs that share a group from one row. For a new round on the same charts, keep the project and change the group. You can still read the group name on each row, because the project is unchanged.

You may want, for example, ablations of the same architecture that use different hyperparameter configurations to be part of one group. All the work related to building and validating that single model may be part of a single project.

**Run name.** The run name is the display name you choose for one run. Give each run its own name, so you can tell the rows apart. You can edit the run name in the UI after the run starts.

**Run id.** The run id is the short id you receive when the run starts. The run id stays fixed for the life of the run, and you find the run id in the run URL. You use the run id when you need one exact run, e.g. when you open the run URL. You don't pass a run id to `start_run`.

## Tags and config

You can define a config object, which let you define additional fields like `tag`. This helps you organize your runs even more.

Config is the dictionary of inputs, and metrics are the numbers you record during the run. Keep inputs in `config`, and record metrics with `run.log`. You can then read the metrics on a chart, and you can filter rows by the inputs.

## Logging

### Log

Call `run.log` when you have a new metric, with a dictionary such as `run.log({"loss": loss})`. You add one step to the run history on each call.

### Summary

The summary is the single value shown for each metric in the run table. The summary for each key is the latest value you passed to `run.log`. Set a final value with `run.summary["accuracy"] = 0.91` when you compute the number once, at the end.

### Artifact

An artifact is a versioned file attached to a run, e.g. a small metrics table. Create an artifact with `run.log_artifact` when you want the metrics table linked from the run. Put large experiment files in the lab S3 bucket, `mind-technology-lab-experiments`, under the same prefix as the local folder.

### Completion

You finish the run by leaving the `with` block. If the block raises, the run state is failed. Call `run.finish()` yourself when you don't use a `with` block. You can upload logs only after the machine has a key, and `start_run` doesn't store one.

## Login

### How do I log into wandb?

The API key comes from the `WANDB_API_KEY` environment variable. This is a single lab-wide API key, stored in AWS Secrets Manager. Get that value (e.g., ask Claude to grab it using the `secretsmanager.py` file). Run `wandb login` once on the machine, and the key stays on the machine for later runs.

Keep the key out of `config` and out of the run name, and keep the key out of `wandb.py`.

### No wifi?

If the machine has no network, set `WANDB_MODE=offline` before `start_run`. You then have a local run file, and you upload the run later with `wandb sync`.
