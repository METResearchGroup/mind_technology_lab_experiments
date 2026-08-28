# Step 3: Run one voice turn and write the transcript

Implement `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/voice_agent.py` so one recorded WAV clip becomes user text, assistant text, and reply WAV bytes. Also implement the helpers that create the session folder and append two JSON lines when the page calls them in Step 4. Follow the Python chained pipeline in the OpenAI voice-agents guide, which means speech to text, then the text agent, then text to speech.

## Scope

- **Caller:** `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/app.py` will call `VoiceSession.handle_turn` in Step 4.
- **In scope:** WAV conversion, chained pipeline, session directory, `chat.jsonl` append. Keep `app.py` on the title-only stub.
- **Out of scope:** Streamlit widgets, JavaScript, live WebRTC, tools, test files.

## Files to inspect

- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/voice_agent.py`
- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/prompts.py`
- `/Users/mark/src/work/mind_technology_lab_experiments/shared/load_env_vars.py`
- https://developers.openai.com/api/docs/guides/voice-agents (Python `VoicePipeline`, `AudioInput`, `SingleAgentVoiceWorkflow`)
- https://openai.github.io/openai-agents-python/voice/pipeline/ (`AudioInput` for a complete clip, stream events)

## Files allowed to change

- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/voice_agent.py`

## Files forbidden to change

- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/app.py`
- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/prompts.py`
- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/SPECS.md`
- `/Users/mark/src/work/mind_technology_lab_experiments/shared/load_env_vars.py`
- Any test file
- Any JavaScript file

## Implement-from-spec phases for this step

### Phase 0. Scope

The caller is `handle_turn`. The happy path takes WAV bytes in and returns transcripts plus reply WAV. Disk writes go through `create_session_dir` and `append_chat_lines`, which Step 4 will call. Do not write files from `handle_turn`. `handle_turn` returns `TurnResult` only. `create_session_dir` and `append_chat_lines` stay separate so the pipeline does not import Streamlit, and so a missing `outputs/` folder stays a page concern.

### Phase 1 to 2

Signatures already frozen in Step 1. Do not rename them.

### Phase 3

Skip tests.

### Phase 4. Flesh in this order

1. `wav_bytes_to_pcm16`
2. `pcm16_to_wav_bytes`
3. `create_session_dir`
4. `append_chat_lines`
5. `VoiceSession.handle_turn`

### Phase 5

A manual `uv run python` snippet from the Commands section writes two jsonl lines and returns without importing Streamlit.

## Contracts

### `ChatLine`

- `role`: `"user"` or `"assistant"`
- `content`: non-empty string for a successful turn

### `TurnResult`

- `user_text`: speech-to-text of the clip
- `assistant_text`: full assistant text that was sent to text-to-speech
- `reply_wav_bytes`: WAV-wrapped PCM of the spoken reply, 1 channel, 16-bit, 24000 Hz

### `create_session_dir(outputs_root, timestamp)`

- Create `outputs_root / timestamp` with `mkdir(parents=True, exist_ok=True)`
- Return that path
- Do not create `chat.jsonl` until the first append

### `append_chat_lines(chat_path, user_text, assistant_text)`

- Open `chat_path` in append mode, UTF-8
- Write two lines, in this order, each `json.dumps` of a dict plus a newline:
  - `{"role": "user", "content": <user_text>}`
  - `{"role": "assistant", "content": <assistant_text>}`
- Do not write a JSON array wrapper
- Create parent directories if they do not exist

### `wav_bytes_to_pcm16`

- Decode with the stdlib `wave` module
- Return a 1-D numpy `int16` array and the file's sample rate
- If channels is 2, keep only channel 0
- Raise `ValueError` with a clear message if the sample width is not 2 bytes

### `pcm16_to_wav_bytes`

- Write a WAV in memory (`io.BytesIO` + `wave`)
- 1 channel, sample width 2, caller-supplied sample rate

### `VoiceSession`

- `__init__(instructions)` builds one `Agent` named `"Issue discussion"` with `instructions=instructions` and model `"gpt-4.1-mini"` (text model for the chained pipeline, not a realtime speech-to-speech model). Wrap it in `SingleAgentVoiceWorkflow`, then `VoicePipeline(workflow=...)`.
- Store the workflow on the instance so later `handle_turn` calls keep history (`SingleAgentVoiceWorkflow` already appends to its input list).
- To capture transcripts, wrap the workflow in a small `VoiceWorkflowBase` subclass in the same file that:
  1. Saves the `transcription` argument as `last_user_text`
  2. Delegates to `SingleAgentVoiceWorkflow.run`
  3. Concatenates yielded text chunks into `last_assistant_text`
  4. Yields the same chunks so text-to-speech still runs
- `handle_turn(wav_bytes)`:
  1. Convert WAV to PCM with `wav_bytes_to_pcm16`
  2. If the sample rate is not 24000, raise `ValueError` telling the caller to record at 24000 Hz (the page will set that on the recorder). Do not resample.
  3. Build `AudioInput(buffer=pcm, frame_rate=24000)`
  4. `await pipeline.run(audio_input)`
  5. Concatenate every `event.data` where `event.type == "voice_stream_event_audio"` and `event.data` is not `None`, as int16
  6. Convert that PCM to WAV bytes at 24000 Hz
  7. Return `TurnResult` using the wrapper's captured texts
- Load `OPENAI_API_KEY` with `EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)` at the start of `handle_turn` (or in `__init__`). Do not print the key.

Do not add tools. Do not use `RealtimeAgent`, WebRTC, or any JavaScript package.

## Commands

From `/Users/mark/src/work/mind_technology_lab_experiments`:

```bash
uv run python - <<'PY'
from pathlib import Path
import json
import numpy as np
from issue_discussion_platform.voice_agent import (
    append_chat_lines,
    create_session_dir,
    pcm16_to_wav_bytes,
    wav_bytes_to_pcm16,
)

pcm = np.zeros(24000, dtype=np.int16)
wav = pcm16_to_wav_bytes(pcm, 24000)
pcm2, rate = wav_bytes_to_pcm16(wav)
assert rate == 24000
assert pcm2.dtype == np.int16
assert len(pcm2) == 24000

root = Path("/tmp/issue-discussion-plan-check")
session = create_session_dir(root, "20990101_000000")
chat = session / "chat.jsonl"
append_chat_lines(chat, "hello", "hi there")
lines = chat.read_text(encoding="utf-8").splitlines()
assert json.loads(lines[0]) == {"role": "user", "content": "hello"}
assert json.loads(lines[1]) == {"role": "assistant", "content": "hi there"}
print("ok")
PY
```

The command prints:

```text
ok
```

Do not call `VoiceSession.handle_turn` in this command. The `handle_turn` path needs a live `OPENAI_API_KEY` and is confirmed in Step 5.

## Pass / fail

| Check | Pass | Fail |
| --- | --- | --- |
| Conversion round trip | The command prints `ok` | Resampling, stereo left mixed in, or a JSON array file |
| Pipeline | `handle_turn` uses `VoicePipeline` + `AudioInput` + captured workflow texts | JavaScript realtime session, or guessing transcripts instead of STT/agent text |
| Disk split | `handle_turn` does not write `chat.jsonl` | Hidden writes inside the pipeline that Step 4 cannot see |
| Page unchanged | `app.py` still title-only | Microphone added early |
| Tests | No new `test_*.py` | Any new test file |

## Done when

WAV helpers and jsonl append work under the command above, and `VoiceSession.handle_turn` is fully implemented for Step 4 to call.
