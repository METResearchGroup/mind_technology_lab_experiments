# Step 6: Ship the one-page audio UI

## Goal

Replace the Step 4 control sketch with one debate page that states the locked roles, shows connection status, Start and Stop, both captions, and a short cost and consent note. Capture before and after screenshots.

## Scope

- Caller: browser `GET /` on `gpt_live_enlightened_disagreement/src/app/page.tsx`.
- Task: visible copy and layout on the existing Live client. No new OpenAI endpoints.
- Out of scope: custom voices, avatar, chat history persistence, Vercel deploy.

## Files to inspect

- `gpt_live_enlightened_disagreement/src/app/page.tsx`
- `gpt_live_enlightened_disagreement/src/app/layout.tsx`
- `gpt_live_enlightened_disagreement/src/app/globals.css`
- `gpt_live_enlightened_disagreement/src/lib/live-webrtc.ts`
- `docs/plans/2026-09-11_gpt-live-enlightened-disagreement_9dbac1/images/after/call-controls.png` from Step 4

## Files allowed to change

- `gpt_live_enlightened_disagreement/src/app/page.tsx`
- `gpt_live_enlightened_disagreement/src/app/layout.tsx` (`<title>` and metadata only)
- `gpt_live_enlightened_disagreement/src/app/globals.css` (typography, spacing, contrast only)
- Screenshot files under `docs/plans/2026-09-11_gpt-live-enlightened-disagreement_9dbac1/images/before/` and `docs/plans/2026-09-11_gpt-live-enlightened-disagreement_9dbac1/images/after/`

## Files forbidden to change

- `gpt_live_enlightened_disagreement/src/lib/prompts.ts`
- `gpt_live_enlightened_disagreement/src/app/api/session/route.ts`
- `gpt_live_enlightened_disagreement/ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md`
- Adding Tailwind, a component library, or a design-system folder

## Required UI copy (exact visible strings)

The page must include the strings below, visible without opening a dialog:

- Heading: `GPT-Live debate`
- Role line: `You argue for socialism. The agent is a capitalist devil's advocate.`
- Status element with `id="call-status"` whose text is one of: `Idle`, `Connecting`, `Connected`, `Finishing the conversation…`, `Conversation ended.`, or an error string from `/api/session` / `getUserMedia`.
- Button `id="start-call"` label `Start`. Disabled while status is `Connecting` or `Connected`.
- Button `id="stop-call"` label `Stop`. Disabled unless status is `Connected`.
- Caption region `id="user-caption"` labeled `You`.
- Caption region `id="assistant-caption"` labeled `Agent`.
- Cost note: `Voice is billed at $0.05 per minute. Grant the microphone only if you accept that charge. The OpenAI key stays on the server.`

Do not add a role-switch control. Do not add a topic picker.

## Screenshots (required)

Before layout work, with Step 4 controls still on screen:

1. `docs/plans/2026-09-11_gpt-live-enlightened-disagreement_9dbac1/images/before/ui-start.png` of `/`.

After copy and layout:

2. `docs/plans/2026-09-11_gpt-live-enlightened-disagreement_9dbac1/images/after/debate-idle.png` of `/` in `Idle`, showing both role lines, Start, Stop (disabled), empty captions, and the cost note.
3. `docs/plans/2026-09-11_gpt-live-enlightened-disagreement_9dbac1/images/after/debate-error.png`. Unset `OPENAI_API_KEY` in `.env.local`, click Start, grant the microphone if asked, and capture the status line after `POST /api/session` fails. The status line must show `Set OPENAI_API_KEY on the server` or the thrown error text.

Do not create empty placeholder PNG files.

## Work

1. Capture `ui-start.png`.
2. Put the required strings on `page.tsx`. Keep using `startLiveCall` / `stopLiveCall` from Step 4.
3. Style only in `globals.css`: readable type, spacing, and contrast. No animation library.
4. Confirm Start remains a user gesture that calls `getUserMedia`.
5. Capture after screenshots. Commit code and images.

## Commands (exact)

From `gpt_live_enlightened_disagreement/`:

```bash
npm test
```

Expected: exit 0 (Step 3 to Step 5 tests still pass).

```bash
npm run build
```

Expected: exit 0.

```bash
npm run dev
```

Expected: `http://localhost:3000`.

```bash
curl -s http://localhost:3000/ | grep -F "You argue for socialism. The agent is a capitalist devil's advocate."
```

Expected: the role line appears.

```bash
curl -s http://localhost:3000/ | grep -F 'Voice is billed at $0.05 per minute.'
```

Expected: the cost note appears.

```bash
curl -s http://localhost:3000/ | grep -E "start-call|stop-call|user-caption|assistant-caption|call-status"
```

Expected: all five ids appear.

Manual: click Start, grant mic, speak one socialist claim, confirm both caption regions can be non-empty at once, click Stop, confirm the tab releases the microphone.

## Pass / fail

| Check | Pass | Fail |
| --- | --- | --- |
| Roles | Socialism / capitalist devil's advocate copy is visible | Role switcher or swapped roles |
| Controls | Start / Stop / status / two captions | Health-only page remains |
| Cost | `$0.05 per minute` on the page | No billing note |
| CSS | Only `globals.css` | Tailwind or a UI kit added |
| Screenshots | before `ui-start.png` and after `debate-idle.png` exist | Missing image files |

## Out of scope

- Vercel project and Authentication (Step 7)
- Storing recordings
