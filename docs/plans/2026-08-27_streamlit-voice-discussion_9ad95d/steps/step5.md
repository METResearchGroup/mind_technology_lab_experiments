# Step 5: Run from the repo root and confirm the happy path

Confirm the full path with a real `OPENAI_API_KEY` in the repo-root `.env`. Do not add tests. Do not change the spec file.

## Scope

- **Caller:** The same Streamlit command as Step 4, from the repo root.
- **In scope:** Manual happy-path check, after screenshot if Step 4 had no live audio, README sanity.
- **Out of scope:** New features, JavaScript, test files, editing `SPECS.md`.

## Files to inspect

- `/Users/mark/src/work/mind_technology_lab_experiments/.env` (confirm `OPENAI_API_KEY` is set; do not commit it)
- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/app.py`
- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/README.md`
- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/outputs/` (gitignored)

## Files allowed to change

- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/README.md` (only if the run command or `.env` note is wrong)
- `/Users/mark/src/work/mind_technology_lab_experiments/docs/plans/2026-08-27_streamlit-voice-discussion_9ad95d/images/after/` (replace after-turn screenshot with a real conversation if needed)

## Files forbidden to change

- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/SPECS.md`
- `/Users/mark/src/work/mind_technology_lab_experiments/.env`
- `/Users/mark/src/work/mind_technology_lab_experiments/shared/load_env_vars.py`
- Pipeline or prompt behavior unless Step 5 finds a blocker that makes the happy path impossible (if so, fix the smallest bug in `app.py` or `voice_agent.py` and document it in the commit message)
- Any test file
- Any JavaScript file

## Work

1. From the repo root, confirm the key loads:

```bash
uv run python -c "from shared.load_env_vars import EnvVarsContainer; v = EnvVarsContainer.get_env_var('OPENAI_API_KEY', required=True); print('set' if v.strip() else 'empty')"
```

The command prints:

```text
set
```

If the command raises because the key is missing, stop and tell the operator to put `OPENAI_API_KEY` in `/Users/mark/src/work/mind_technology_lab_experiments/.env`. Do not write a secret into the repo.

2. Start the page:

```bash
uv run streamlit run issue_discussion_platform/app.py
```

The command prints a URL that includes `http://localhost:8501`.

3. In the browser, click the microphone, speak one short English sentence, stop recording, and wait for the reply.
4. Confirm all of the following:
   - The page shows a user line whose text matches what was said (speech-to-text may differ slightly).
   - The page shows an assistant line.
   - The browser plays spoken audio.
   - Exactly one new directory exists under `issue_discussion_platform/outputs/` whose name matches `YYYYMMDD_HHMMSS`.
   - The timestamp directory contains `chat.jsonl`.
5. Inspect the file:

```bash
uv run python -c "from pathlib import Path; p = sorted(Path('issue_discussion_platform/outputs').glob('*/chat.jsonl'))[-1]; print(p); print(p.read_text(encoding='utf-8'))"
```

The command prints the `chat.jsonl` path, then at least two lines of JSON. The first line has `"role": "user"`. The second has `"role": "assistant"`. Both have a `"content"` string.

6. Record a second clip in the same browser tab without refreshing. Confirm the same `chat.jsonl` now has four lines, and the assistant's second reply can refer to the first user line (history is on).
7. Refresh the browser tab. Confirm Streamlit does not add duplicate lines for the previous clip (fingerprint dedup). A refresh may start a new Streamlit session and a new timestamp folder, and a new folder after refresh is acceptable. Duplicates inside the same session folder are not.
8. Update `images/after/after-turn.png` if the Step 4 shot had no real transcripts.
9. Confirm `git status` does not list files under `issue_discussion_platform/outputs/`.
10. Confirm there are still no `test_*.py` files under `issue_discussion_platform/`.

## Pass / fail

| Check | Pass | Fail |
| --- | --- | --- |
| Command | Page started from the repo root with `uv run streamlit run issue_discussion_platform/app.py` | Any `cd issue_discussion_platform` run instructions left in the README |
| Voice | Spoken reply is audible after one recording | Text-only reply, or an exception on the page |
| Transcript | `chat.jsonl` has user then assistant dicts, one object per line | A JSON array, missing roles, or no file |
| Second turn | Same file grows by two lines and history is used | New folder per clip, or the model ignores the first turn |
| Secrets | `.env` untracked, key never printed | Key committed or printed |
| Tests and JS | None added | New tests or JS |

## Done when

The happy flow in [../plan.md](../plan.md) works on the current branch from the repo root, the transcript file matches the schema, and the after screenshot shows a real turn.
