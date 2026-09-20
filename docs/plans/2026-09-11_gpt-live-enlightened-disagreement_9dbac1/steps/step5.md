# Step 5: Encode the capitalism vs socialism debate

## Goal

Replace the stub `getLiveInstructions()` and `getBackendInstructions()` in `gpt_live_enlightened_disagreement/src/lib/prompts.ts` so both strings are loaded from `gpt_live_enlightened_disagreement/ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md`. The live prompt stays short. The backend prompt holds the Kellogg rules, the capitalist case, and the strongest socialist case. Later steps must not invent extra debate rules in TypeScript string literals.

## Scope

- Caller: `createSessionFromSdp` in `gpt_live_enlightened_disagreement/src/lib/openai-live.ts` (or the session helper from Step 3) already passes `getLiveInstructions()` and `getBackendInstructions()` into Live create.
- Task: read the markdown file from disk, build two prompt strings, prove they contain the required headings and devil's advocate order, and keep `outputFileTracingIncludes` so the serverless bundle still contains the markdown.
- Out of scope: UI copy (Step 6), Vercel deploy (Step 7), changing Live vs Realtime HTTP contracts.

## Files to inspect

- `gpt_live_enlightened_disagreement/ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md`
- `gpt_live_enlightened_disagreement/src/lib/prompts.ts`
- `gpt_live_enlightened_disagreement/src/lib/openai-live.ts`
- `gpt_live_enlightened_disagreement/next.config.ts`
- `gpt_live_enlightened_disagreement/tests/session-route.test.ts`

## Files allowed to change

- `gpt_live_enlightened_disagreement/src/lib/prompts.ts`
- `gpt_live_enlightened_disagreement/src/lib/prompt-file.ts` (create if a separate reader keeps `prompts.ts` thin)
- `gpt_live_enlightened_disagreement/next.config.ts` only to keep or fix `outputFileTracingIncludes` for `/api/session` → `./ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md`
- `gpt_live_enlightened_disagreement/tests/prompts.test.ts` (create)
- `gpt_live_enlightened_disagreement/tests/session-route.test.ts` only if a stub instruction assertion must be updated

## Files forbidden to change

- `gpt_live_enlightened_disagreement/ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md` (do not rewrite rules here; if a required heading is missing, fail the test and go back to Step 1)
- `gpt_live_enlightened_disagreement/src/lib/live-webrtc.ts`
- `gpt_live_enlightened_disagreement/src/app/page.tsx`
- Root Python CI files

## Contracts

### `readPrinciplesMarkdown(): string`

Read `ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md` with `fs.readFileSync` (or `readFile` awaited at first use) from `path.join(process.cwd(), "ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md")`. Throw `Error("ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md is missing")` if the file is absent. Do not fetch Kellogg URLs at runtime.

### `getLiveInstructions(): string`

Return a short spoken-style prompt. It must include:

- One voice: capitalist devil's advocate (argue for capitalism and run the Kellogg moves in the same voice).
- Move order: restate the user's socialist claim, state the strongest version of the user's claim, then argue the capitalist counter.
- When the user starts speaking while the agent is talking, keep listening and do not scold.
- Delegate current facts to the Responses backend (web search).
- Do not seek agreement or a milder middle as the goal of a turn.

The live string must be shorter than `getBackendInstructions()`. Do not paste the Quotes section in full.

### `getBackendInstructions(): string`

Return a longer prompt that includes, as substrings:

- `## Mission`
- `## Non-goals`
- `## Operating rules`
- `## Devil's advocate procedure`
- The twelve rule names from Step 1 (the same heading text as in the markdown).
- An explicit capitalist case the model should argue (property, prices, and dispersed knowledge as the side it defends).
- An explicit strongest-steelman of the socialist case, so the model can restate it before rebutting.
- Hosted web search: use tools when a current fact is needed; do not invent a statistic.

The backend string may include the full markdown body plus a short role header. It must not add a thirteenth operating rule that is absent from the markdown.

## Implement-from-spec phases

### Phase 1. Scope

Caller is Live create's `session.instructions` and `session.delegation.responses.instructions`.

### Phase 2. Scaffold

Keep function names. Point the reader at `process.cwd()`. Bodies may still return placeholders until tests exist.

### Phase 3. Contracts

Lock the required substrings listed in Contracts.

### Phase 4. Test design (failing)

1. **Given** the app working directory **when** `readPrinciplesMarkdown` **then** the string contains `# Enlightened disagreement principles`.
2. **Given** the principles markdown **when** `getBackendInstructions` **then** it contains `## Operating rules` and `## Devil's advocate procedure`.
3. **Given** both getters **when** compared by `length` **then** live length is less than backend length.
4. **Given** `getLiveInstructions` **then** the string contains `restate` (case insensitive) and `steelman` or `strongest` (case insensitive), and contains `capitalis` (case insensitive).
5. **Given** `getBackendInstructions` **then** it contains each of the twelve rule names from Step 1.
6. **Given** `getBackendInstructions` **then** it does not contain `thirteenth rule` or `Rule 13`.
7. **Given** a temp cwd without the markdown file **when** `readPrinciplesMarkdown` **then** it throws `ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md is missing`.

Do not hit OpenAI.

### Phase 5. Implement units of work, in this order

1. `readPrinciplesMarkdown`
2. `getLiveInstructions` from the file plus the short role header
3. `getBackendInstructions` from the file plus the capitalist / steelman header
4. Confirm `next.config.ts` tracing include
5. Re-run session route tests

Each unit is its own Git commit.

## Commands (exact)

From `gpt_live_enlightened_disagreement/`:

```bash
npm test
```

Expected after Phase 4 only: new prompt tests fail. Expected after Phase 5: `npm test` exits 0.

```bash
python3 - <<'PY'
from pathlib import Path
cfg = Path("next.config.ts").read_text()
needle = "ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md"
print("tracing:" + ("yes" if needle in cfg else "no"))
PY
```

Expected output: `tracing:yes`

```bash
npm run build
```

Expected: exit 0.

## Pass / fail

| Check | Pass | Fail |
| --- | --- | --- |
| Source | Prompts read the markdown file | Rules copied only as TypeScript literals with no file read |
| Order | Restate, then strongest case, then capitalist argument | Prompt says only "be a moderator" |
| Length | Live string shorter than backend | Same blob in both |
| Tracing | `next.config.ts` includes the markdown for `/api/session` | File missing from the serverless bundle |
| Invention | No extra operating rule beyond the markdown | New rule invented in `prompts.ts` |

## Out of scope

- Changing caption or WebRTC clients (Step 4)
- Page layout and consent copy (Step 6)
