# Step 1: Make the experiment importable and add root packages

Create the files and the root environment wiring so later steps can import experiment modules and `shared` under `uv run` from the repo root. Do not make voice calls or add Streamlit widgets yet.

## Scope

- **Caller (wired in Step 4):** `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/app.py` started with `uv run streamlit run issue_discussion_platform/app.py` from the repo root.
- **In scope:** Root package install, runtime dependencies, gitignore for outputs, stub modules.
- **Out of scope:** Prompt text, pipeline calls, Streamlit microphone, transcript writes, any test files.

## Files to inspect

- `/Users/mark/src/work/mind_technology_lab_experiments/pyproject.toml`
- `/Users/mark/src/work/mind_technology_lab_experiments/uv.lock`
- `/Users/mark/src/work/mind_technology_lab_experiments/.gitignore`
- `/Users/mark/src/work/mind_technology_lab_experiments/SETUP.md`
- `/Users/mark/src/work/mind_technology_lab_experiments/shared/load_env_vars.py`
- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/SPECS.md` (read only)

## Files allowed to change

- `/Users/mark/src/work/mind_technology_lab_experiments/pyproject.toml`
- `/Users/mark/src/work/mind_technology_lab_experiments/uv.lock`
- `/Users/mark/src/work/mind_technology_lab_experiments/.gitignore`
- `/Users/mark/src/work/mind_technology_lab_experiments/shared/__init__.py` (create)
- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/__init__.py` (create)
- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/app.py` (create, stub)
- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/voice_agent.py` (create, stub)
- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/prompts.py` (create, stub)
- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/README.md` (create)

## Files forbidden to change

- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/SPECS.md`
- `/Users/mark/src/work/mind_technology_lab_experiments/tests/test_scaffold.py`
- Any new file matching `test_*.py`
- Any JavaScript or TypeScript file
- `/Users/mark/src/work/mind_technology_lab_experiments/shared/load_env_vars.py`

## Implement-from-spec phases for this step

### Phase 0. Scope

The caller is the Streamlit script named in the Scope section. The file tree for this step is the allowed-to-change list. Out of scope is listed in the Scope section.

### Phase 1. Scaffold

Create the stub modules with imports that resolve and bodies that raise `NotImplementedError` or render a title only. Do not implement speech, files under `outputs/`, or microphone widgets.

### Phase 2. Contracts

Lock the public names that later steps will fill, matching Step 3. Bodies stay stubs.

### Phase 3. Test design

Skip tests. The plan does not add test files.

### Phase 4. Flesh

Only the packaging, gitignore, README run command, and stub files. No voice behavior.

### Phase 5

Imports resolve under `uv run` from the repo root. The title page loads in the browser.

## Work

1. Add a hatchling build backend to `/Users/mark/src/work/mind_technology_lab_experiments/pyproject.toml` so `uv sync` installs this repo as a package. Include packages `shared` and `issue_discussion_platform` only.
2. Add runtime dependencies (not optional extras):
   - `streamlit>=1.40`
   - `openai-agents[voice]`
   - `python-dotenv`
   - `numpy`
3. Create empty `/Users/mark/src/work/mind_technology_lab_experiments/shared/__init__.py` and `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/__init__.py`.
4. Append this line to `/Users/mark/src/work/mind_technology_lab_experiments/.gitignore`:

   `issue_discussion_platform/outputs/`

5. Create stub `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/prompts.py` that defines `SYSTEM_PROMPT` as an empty string.
6. Create stub `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/voice_agent.py` with these public names and `NotImplementedError` bodies:
   - `ChatLine` dataclass with fields `role` (`Literal["user", "assistant"]`) and `content` (`str`)
   - `TurnResult` dataclass with fields `user_text` (`str`), `assistant_text` (`str`), `reply_wav_bytes` (`bytes`)
   - `create_session_dir(outputs_root: Path, timestamp: str) -> Path`
   - `append_chat_lines(chat_path: Path, user_text: str, assistant_text: str) -> None`
   - `wav_bytes_to_pcm16(wav_bytes: bytes) -> tuple[Any, int]` (numpy int16 array and sample rate). Use `numpy.ndarray` in the annotation if `Any` would fail ruff. Prefer `tuple[npt.NDArray[np.int16], int]`.
   - `pcm16_to_wav_bytes(pcm: npt.NDArray[np.int16], sample_rate: int) -> bytes`
   - `class VoiceSession` with `__init__(self, instructions: str) -> None` and `async def handle_turn(self, wav_bytes: bytes) -> TurnResult`
7. Create stub `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/app.py` that imports `SYSTEM_PROMPT` from `issue_discussion_platform.prompts` and `VoiceSession` from `issue_discussion_platform.voice_agent`, and renders only `st.title("Issue discussion")`. Do not add `sys.path` inserts. Do not call `handle_turn` yet.
8. Write `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/README.md` with the run command from the Commands section below, and a note that `OPENAI_API_KEY` belongs in the repo-root `.env`.
9. Run `uv lock` and `uv sync --extra test` from the repo root so `/Users/mark/src/work/mind_technology_lab_experiments/uv.lock` updates.
10. Commit.

## Commands

From `/Users/mark/src/work/mind_technology_lab_experiments`:

```bash
uv lock
uv sync --extra test
```

The command writes a resolved lockfile, finishes the sync, and exits 0.

```bash
uv run python -c "from shared.load_env_vars import EnvVarsContainer; from issue_discussion_platform.prompts import SYSTEM_PROMPT; from issue_discussion_platform.voice_agent import VoiceSession; print('ok')"
```

The command prints:

```text
ok
```

```bash
uv run streamlit run issue_discussion_platform/app.py
```

The command prints a local URL such as `http://localhost:8501`. Opening the URL shows a page whose title is "Issue discussion". There is no microphone widget yet.

## Pass / fail

| Check | Pass | Fail |
| --- | --- | --- |
| Root env | `streamlit`, `agents`, and `dotenv` import inside `uv run python` | Experiment-local `pyproject.toml` was added |
| Imports | The `python -c` command prints `ok` with no `sys.path` in source | `ModuleNotFoundError` or a `sys.path.insert` in `app.py` |
| Stubs | `app.py`, `voice_agent.py`, and `prompts.py` exist with the names above | Voice API calls or microphone widgets added early |
| Gitignore | `issue_discussion_platform/outputs/` is ignored | Output wav or jsonl files are tracked |
| Tests | No new `test_*.py` files | Any new test file |
| Spec | `SPECS.md` unchanged | `SPECS.md` edited |

## Done when

The root environment can import `shared` and `issue_discussion_platform`, Streamlit serves the title page from the repo root, and the public names in `voice_agent.py` are frozen as stubs.
