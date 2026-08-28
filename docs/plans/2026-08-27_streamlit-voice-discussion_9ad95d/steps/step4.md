# Step 4: Wire the Streamlit page

Turn `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/app.py` into the microphone page. Capture a before screenshot of the title-only page first. Then record, run one voice turn, show the transcript, play the reply, and append `chat.jsonl`.

## Scope

- **Caller:** A person at `http://localhost:8501` after `uv run streamlit run issue_discussion_platform/app.py` from the repo root.
- **In scope:** Session folder, microphone, transcript display, audio playback, one `VoiceSession` kept in `st.session_state`.
- **Out of scope:** Changing pipeline internals, prompt text, JavaScript, test files, deployment.

## Files to inspect

- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/app.py`
- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/voice_agent.py`
- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/prompts.py`
- `/Users/mark/src/work/mind_technology_lab_experiments/shared/load_env_vars.py`
- Streamlit `st.audio_input` docs (return type is a WAV `UploadedFile`, `sample_rate` supports 24000)

## Files allowed to change

- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/app.py`
- Screenshots under `/Users/mark/src/work/mind_technology_lab_experiments/docs/plans/2026-08-27_streamlit-voice-discussion_9ad95d/images/before/` and `images/after/`

## Files forbidden to change

- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/voice_agent.py`
- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/prompts.py`
- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/SPECS.md`
- `/Users/mark/src/work/mind_technology_lab_experiments/shared/load_env_vars.py`
- Any test file
- Any JavaScript file

## Screenshots (required)

Before editing `app.py` beyond the title stub, with Streamlit running:

1. Save `/Users/mark/src/work/mind_technology_lab_experiments/docs/plans/2026-08-27_streamlit-voice-discussion_9ad95d/images/before/title-page.png`

After the microphone and transcript work (Step 5 may retake if the first after-shot has no real conversation):

2. Save `/Users/mark/src/work/mind_technology_lab_experiments/docs/plans/2026-08-27_streamlit-voice-discussion_9ad95d/images/after/idle.png` (microphone visible, empty or existing transcript)
3. Save `/Users/mark/src/work/mind_technology_lab_experiments/docs/plans/2026-08-27_streamlit-voice-discussion_9ad95d/images/after/after-turn.png` (user and assistant text visible, audio player present)

## Implement-from-spec phases for this step

### Phase 0. Scope

The caller is the Streamlit script. The slice is load session, record, `handle_turn`, show text and audio, then append jsonl.

### Phase 3

Skip tests.

### Phase 4. Flesh in this order

1. Session state: timestamp, output directory, `VoiceSession`, transcript list, last processed recording id
2. Microphone widget
3. Turn handler that calls `handle_turn`, appends jsonl, updates the list, plays audio
4. Transcript rendering

## Work

1. Capture the before screenshot.
2. Do not add `sys.path` inserts. Keep imports as `from issue_discussion_platform.prompts import SYSTEM_PROMPT`, `from issue_discussion_platform.voice_agent import ...`, and `from shared.load_env_vars import EnvVarsContainer` if the page needs to fail fast on a missing key before a turn.
3. On first run of a browser session, set:
   - `timestamp` to local time `datetime.now().strftime("%Y%m%d_%H%M%S")`
   - `session_dir` to `create_session_dir(Path("issue_discussion_platform/outputs"), timestamp)` so the folder is `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/outputs/<timestamp>/` when the process cwd is the repo root
   - `voice_session` to `VoiceSession(instructions=SYSTEM_PROMPT)`
   - `messages` to an empty `list`
   - `last_audio_fingerprint` to `None`
4. Show `st.title("Issue discussion")` and one short line that the person should click the microphone, speak, then stop.
5. Add `st.audio_input("Record a turn", sample_rate=24000)`.
6. When the widget returns a file, read its bytes. Compute a fingerprint (`hashlib.sha256(bytes).hexdigest()`). If it equals `last_audio_fingerprint`, do nothing (Streamlit reruns must not replay the same clip).
7. Otherwise call `asyncio.run(voice_session.handle_turn(wav_bytes))`. On success:
   - Append `{"role": "user", "content": result.user_text}` and `{"role": "assistant", "content": result.assistant_text}` to `messages`
   - Call `append_chat_lines(session_dir / "chat.jsonl", result.user_text, result.assistant_text)`
   - Store `result.reply_wav_bytes` in session state as `last_reply_wav`
   - Set `last_audio_fingerprint` to the fingerprint
8. On `ValueError` or a missing API key error, show `st.error` with the exception text. Do not append jsonl.
9. Render `messages` in order with `st.chat_message(role)` and `st.write(content)` so the transcript is visible on the page.
10. If `last_reply_wav` is set, call `st.audio(last_reply_wav, format="audio/wav", autoplay=True)`.
11. Capture after screenshots. Commit page and images.

## Commands

From `/Users/mark/src/work/mind_technology_lab_experiments`:

```bash
uv run streamlit run issue_discussion_platform/app.py
```

The command prints a URL that includes `http://localhost:8501`. The process stays running.

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/
```

The command prints:

```text
200
```

Manual checks while the server is up:

- The page shows a microphone control.
- After one recording, user text and assistant text appear, and audio plays.
- `issue_discussion_platform/outputs/<timestamp>/chat.jsonl` has two lines for that turn.

## Pass / fail

| Check | Pass | Fail |
| --- | --- | --- |
| Run from root | The `uv run streamlit` command above is the only run method documented | `cd` into the experiment folder, or `sys.path` edits |
| One session file | First load creates one timestamp folder; later turns append the same `chat.jsonl` | A new folder per rerun or per clip |
| Dedup | A Streamlit rerun does not call OpenAI again for the same bytes | Duplicate jsonl pairs on refresh |
| History | One `VoiceSession` in session state for the browser session | A new pipeline (and empty history) on every clip |
| Screenshots | before and after images exist at the paths above | UI shipped with no images |
| Tests | No new `test_*.py` | Any new test file |

## Done when

The page records a turn, shows both transcripts, plays the reply, and appends `chat.jsonl`, with screenshots stored in this plan folder.
