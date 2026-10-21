# Social science idea generation

One brief goes through a fixed discussion. Each round starts with a different discipline. The other four roles comment twice. A synthesizer, a methodologist, and a critic then produce one revised proposal. After five rounds, seven agents score the revisions and the driver keeps the top three.

The smoke run is round 1 plus a cost note. It stops before rounds 2 through 5 and before the vote.

## Round

```mermaid
flowchart TD
  brief[Brief] --> seed[Seed agent writes a research idea]
  seed --> pass1[Four other agents comment]
  pass1 --> pass2[The same four agents comment again]
  pass2 --> synth[Synthesizer writes the idea]
  synth --> method[Methodologist writes a design]
  method --> critic[Critic names flaws]
  critic --> revised[Methodologist revises the idea and the design]
  revised --> record[Round record]
```

## Five rounds

```mermaid
flowchart TD
  brief[One brief] --> r1[Round 1]
  brief --> r2[Round 2]
  brief --> r3[Round 3]
  brief --> r4[Round 4]
  brief --> r5[Round 5]
  r1 --> vote[Vote]
  r2 --> vote
  r3 --> vote
  r4 --> vote
  r5 --> vote
  vote --> top3[Top three revised proposals]
```

## LangSmith threads

```mermaid
flowchart LR
  roundFn[run_round] --> roundThread[One thread id for every turn in the round]
  voteFn[run_vote] --> voteThread[A separate thread id for the seven ballots]
```

## Smoke

From the repository root, after `src/run_smoke.py` is in place:

```bash
PYTHONPATH=/workspace:/workspace/experiments/social_science_idea_generation_2026_10_21 uv run --project experiments/social_science_idea_generation_2026_10_21 python -m src.run_smoke
```

The command writes `outputs/smoke/<run_id>/round.json` and `cost.json`, uploads both under the experiment prefix in S3, and prints `run_id` and `estimated_cost_usd`.
