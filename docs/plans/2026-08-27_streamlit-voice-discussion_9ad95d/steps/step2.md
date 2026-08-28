# Step 2: Write the system prompt

Fill `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/prompts.py` so the voice agent in Step 3 can pass one instruction string into the Agents SDK `Agent`. Follow the labeled-section structure in the realtime prompting guide, and keep only the sections the chained pipeline needs.

## Scope

- **Caller:** `VoiceSession` in `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/voice_agent.py` (still a stub in this step) will pass `SYSTEM_PROMPT` as the agent instructions in Step 3.
- **In scope:** The prompt string only.
- **Out of scope:** Pipeline code, Streamlit, transcript files, tools, live speech-to-speech session settings.

## Files to inspect

- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/prompts.py`
- The realtime prompting guide at https://developers.openai.com/api/docs/guides/realtime-models-prompting (labeled sections, verbosity, language, unclear audio, variety, and the warning not to over-prompt)
- The voice-agents guide at https://developers.openai.com/api/docs/guides/voice-agents (Python path is a chained pipeline, so skip commentary-channel and wait-tool rules)

## Files allowed to change

- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/prompts.py`

## Files forbidden to change

- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/app.py`
- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/voice_agent.py`
- `/Users/mark/src/work/mind_technology_lab_experiments/issue_discussion_platform/SPECS.md`
- `/Users/mark/src/work/mind_technology_lab_experiments/pyproject.toml`
- Any test file

## Implement-from-spec phases for this step

### Phase 0. Scope

The caller is `VoiceSession` using `SYSTEM_PROMPT`. One file changes.

### Phase 1 to 2

`SYSTEM_PROMPT` is already defined in Step 1. Replace the empty string. No new names.

### Phase 3

Skip tests.

### Phase 4 to 5

The prompt string is complete and importable.

## Work

Set `SYSTEM_PROMPT` to one triple-quoted string that contains exactly these headings, in this order, using `#` Markdown headings as in the guide:

1. `# Role and Objective`
2. `# Personality and Tone`
3. `# Language`
4. `# Verbosity`
5. `# Unclear Audio`
6. `# Variety`

Content rules for each section:

- **Role and Objective.** The assistant is a spoken discussion partner that helps the user think through an issue out loud. Success is a short, clear spoken reply that moves the discussion forward. Do not invent an issue tracker, tickets, or tools.
- **Personality and Tone.** Friendly, calm, and concise. Warm without fawning. Spoken pacing, not a written essay.
- **Language.** English is the default. Do not switch language because of accent, filler, or one borrowed word. Switch only if the user clearly asks or speaks a full request in another language.
- **Verbosity.** Direct answers are 1 to 2 short sentences. Ask at most one clarifying question per turn. Do not give long lists unless the user asks for them.
- **Unclear Audio.** After speech-to-text, treat empty, tiny, or obviously garbled text as unclear. Ask once, briefly, to repeat. Do not guess. Do not reuse the same clarification sentence twice in a row.
- **Variety.** Do not start consecutive turns with the same opener. Do not sound like a repeating script.

Do not add `# Tools`, `# Preambles`, `# Message Channels`, `# Entity Capture`, `# Escalation`, or a wait-for-user tool. Tool sections and live-audio wait tools belong to products that have tools or a live speech-to-speech session. The chained pipeline in this experiment has neither.

Do not stack many `always` / `never` / `must` / `only` rules. Prefer a precise sentence over a hard constraint word.

## Commands

From `/Users/mark/src/work/mind_technology_lab_experiments`:

```bash
uv run python -c "from issue_discussion_platform.prompts import SYSTEM_PROMPT; assert SYSTEM_PROMPT.strip(); heads = ['# Role and Objective', '# Personality and Tone', '# Language', '# Verbosity', '# Unclear Audio', '# Variety'];
print('\n'.join(h for h in heads if h in SYSTEM_PROMPT))"
```

The command prints six lines:

```text
# Role and Objective
# Personality and Tone
# Language
# Verbosity
# Unclear Audio
# Variety
```

If a heading is missing, the command omits that heading's line and the step is not done.

## Pass / fail

| Check | Pass | Fail |
| --- | --- | --- |
| Location | Prompt is the `SYSTEM_PROMPT` string in `prompts.py` | Prompt copied into `app.py` or `voice_agent.py` |
| Structure | All six headings present in the order above | Extra tool or live-audio sections, or missing headings |
| Scope | No new files, no tests, `app.py` and `voice_agent.py` unchanged | Pipeline or UI work pulled into this step |

## Done when

`SYSTEM_PROMPT` is a non-empty labeled prompt that a Step 3 agent can use as instructions, and the six headings print from the command above.
