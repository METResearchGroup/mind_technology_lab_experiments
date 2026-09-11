# Step 4: Connect microphone audio and captions

## Goal

Wire the browser so a Start click (a user gesture) opens a GPT-Live-1 WebRTC call through `POST /api/session`, plays assistant audio, shows overlapping captions, and releases the microphone on Stop. Follow the official WebRTC sequence at https://developers.openai.com/api/docs/guides/voice-webrtc. Follow transcript events at https://developers.openai.com/api/docs/guides/live-conversations.

## Scope

- Caller: Start click on `gpt_live_enlightened_disagreement/src/app/page.tsx`, which calls `startLiveCall()` in `gpt_live_enlightened_disagreement/src/lib/live-webrtc.ts`.
- Task: Live WebRTC client, caption reducer, Stop that sends `session.close` and waits for `session.closed` for up to 15 seconds, plus a separate Realtime client used only when `mode` is `realtime`.
- Out of scope: loading the principles file into prompts (Step 5), role labels and cost copy (Step 6), Vercel deploy (Step 7).

## Files to inspect

- `gpt_live_enlightened_disagreement/src/app/page.tsx` (health page from Step 2)
- `gpt_live_enlightened_disagreement/src/app/api/session/route.ts`
- `gpt_live_enlightened_disagreement/src/lib/prompts.ts` (stub strings are still allowed)
- https://developers.openai.com/api/docs/guides/voice-webrtc
- https://developers.openai.com/api/docs/guides/live-conversations
- https://developers.openai.com/api/docs/guides/realtime (Realtime fallback client only)

## Files allowed to change

- `gpt_live_enlightened_disagreement/src/app/page.tsx` (add `"use client"` and Start / Stop / status / captions)
- `gpt_live_enlightened_disagreement/src/app/layout.tsx` only if a client page requires a metadata or title change
- `gpt_live_enlightened_disagreement/src/lib/live-webrtc.ts` (create)
- `gpt_live_enlightened_disagreement/src/lib/live-captions.ts` (create)
- `gpt_live_enlightened_disagreement/src/lib/realtime-webrtc.ts` (create; used only when session JSON `mode` is `"realtime"`)
- `gpt_live_enlightened_disagreement/tests/live-captions.test.ts` (create)
- `gpt_live_enlightened_disagreement/tests/live-webrtc.test.ts` (create)
- Screenshot files under `docs/plans/2026-09-11_gpt-live-enlightened-disagreement_9dbac1/images/before/` and `docs/plans/2026-09-11_gpt-live-enlightened-disagreement_9dbac1/images/after/` (create directories only when saving real images)

## Files forbidden to change

- `gpt_live_enlightened_disagreement/ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md`
- `gpt_live_enlightened_disagreement/src/app/api/session/route.ts` contracts from Step 3
- `gpt_live_enlightened_disagreement/src/lib/prompts.ts` (still stub until Step 5)
- Root Python CI files

## Contracts

### `applyTranscriptDelta(state, event)`

`state` is `{ user: string; assistant: string }`.

| `event.type` | Result |
| --- | --- |
| `session.input_transcript.delta` | Append `event.delta` to `user`. Keep `assistant` unchanged. |
| `session.output_transcript.delta` | Append `event.delta` to `assistant`. Keep `user` unchanged. |
| any other type | Return `state` unchanged. |

`delta` is the string field on the Live event. If `delta` is missing, treat it as `""`. Overlapping user and assistant deltas are valid, because GPT-Live-1 can listen and speak at the same time.

### `startLiveCall({ fetchSession, getUserMedia, RTCPeerConnection })`

Pass `fetch`, `getUserMedia`, and `RTCPeerConnection` as arguments so tests never open a real microphone.

Sequence, matching the official WebRTC guide:

1. Call `getUserMedia({ audio: true })` only from a Start click.
2. Construct `RTCPeerConnection`. Attach `ontrack` so remote audio plays through an `<audio>` element with `autoplay`.
3. Add local microphone tracks.
4. Create a data channel labeled `oai-events` before `createOffer`. Register `message` listeners before `createOffer`.
5. `createOffer`, `setLocalDescription`, then wait until `iceGatheringState` is `"complete"` or 10 seconds pass. On ICE timeout, throw `Timed out while gathering ICE candidates`.
6. `POST /api/session` with `{ "sdp": localDescription.sdp }` and `Content-Type: application/json`.
7. If HTTP is not 2xx, throw using the response body text (or `Live session creation failed` if the body is empty).
8. Parse JSON. If `mode === "live"`, `setRemoteDescription({ type: "answer", sdp: result.transport.sdp })`. Do not send `session.start`. Wait until a parsed `session.started` event arrives on `oai-events`.
9. If `mode === "realtime"`, stop the Live peer connection and microphone, then call `startRealtimeCall({ clientSecret: result.client_secret })` from `realtime-webrtc.ts`. Do not handle Realtime events inside `live-webrtc.ts`.

Do not send `session.input_audio.append`. Do not expect `session.output_audio.delta` on the data channel.

### `stopLiveCall()`

1. If the data channel is not `open` or `session.started` has not arrived, call cleanup (stop tracks, close channel, close peer) and return.
2. Send `JSON.stringify({ type: "session.close" })`.
3. Keep the peer connection, data channel, and microphone tracks alive until `session.closed` or 15 seconds, whichever comes first.
4. On `session.closed` or on the 15 second timeout, stop tracks, close the channel, and close the peer. Set status to `Conversation ended.` on `session.closed`, or `Incomplete finalization: no session.closed event.` on timeout.

### `startRealtimeCall`

Separate module. Browser POSTs SDP `Content-Type: application/sdp` to `https://api.openai.com/v1/realtime/calls` with `Authorization: Bearer <client_secret>`. Use Realtime event names only in `realtime-webrtc.ts` (`response.output_audio_transcript.delta` or the current GA names from the Realtime guide). Do not import Live event type strings into `realtime-webrtc.ts`, and do not import Realtime event type strings into `live-webrtc.ts`.

## Implement-from-spec phases

### Phase 1. Scope

Caller is the Start click. File tree as in Files allowed to change.

### Phase 2. Scaffold

Create `live-captions.ts`, `live-webrtc.ts`, and `realtime-webrtc.ts` with exports that tests can import. Bodies may throw `Error("not implemented")`. Commit.

### Phase 3. Contracts

Lock the tables above. Do not implement `getUserMedia` yet.

### Phase 4. Test design (failing)

Write the tests below before filling in `startLiveCall`:

1. **Given** `{ user: "", assistant: "" }` **when** `applyTranscriptDelta` with `{ type: "session.input_transcript.delta", delta: "Hi" }` **then** `{ user: "Hi", assistant: "" }`.
2. **Given** that user state **when** `applyTranscriptDelta` with `{ type: "session.output_transcript.delta", delta: "Hello" }` **then** `{ user: "Hi", assistant: "Hello" }`.
3. **Given** two overlapping deltas (input then output without waiting) **when** both are applied **then** both strings are non-empty.
4. **Given** `{ type: "session.started" }` **when** `applyTranscriptDelta` **then** captions unchanged.
5. **Given** a stub peer connection whose ICE state is already `"complete"` and a stub `fetchSession` that returns `{ mode: "live", session: { id: "live_1" }, transport: { type: "webrtc", sdp: "answer" } }` **when** `startLiveCall` **then** `setRemoteDescription` is called with that SDP and `createDataChannel` was called with `"oai-events"` before `createOffer`.
6. **Given** `fetchSession` returns `{ mode: "realtime", client_secret: "ek_test" }` **when** `startLiveCall` **then** the Live module does not call `setRemoteDescription` with a Live answer, and `startRealtimeCall` is called with `ek_test`.
7. **Given** an open data channel after `session.started` **when** `stopLiveCall` **then** the first sent payload is `{"type":"session.close"}`.
8. **Given** no `session.closed` after 15 seconds **when** `stopLiveCall` **then** tracks are stopped (use fake timers).

Inject RTC and fetch. Do not hit OpenAI or a real microphone.

### Phase 5. Implement units of work, in this order

1. `applyTranscriptDelta`
2. ICE + `POST /api/session` + apply Live SDP
3. Caption wiring from `oai-events` messages
4. `stopLiveCall` close timeout
5. Realtime branch that delegates to `realtime-webrtc.ts`
6. Wire Start / Stop on `page.tsx`

Each unit is its own Git commit.

## Screenshots (required)

Capture before changing `page.tsx`:

1. `docs/plans/2026-09-11_gpt-live-enlightened-disagreement_9dbac1/images/before/home.png` with `npm run dev` showing `GPT-Live debate` and `Health: up`.

After Start / Stop exist:

2. `docs/plans/2026-09-11_gpt-live-enlightened-disagreement_9dbac1/images/after/call-controls.png` showing a Start control, a Stop control, and a status line. Captions may be empty. Do not wait for a live OpenAI call to take the shot.

Do not create empty placeholder PNG files.

## Commands (exact)

From `gpt_live_enlightened_disagreement/`:

```bash
npm test
```

Expected after Phase 4 only: Vitest runs, and the new tests fail with `not implemented` or assertion failures, not with `Cannot find module`.

Expected after Phase 5: `npm test` exits 0.

```bash
npm run build
```

Expected: exit 0.

```bash
npm run dev
```

Expected: process listens on `http://localhost:3000`.

```bash
curl -s http://localhost:3000/ | grep -E "Start|Stop|Health: up"
```

Expected: `Start` and `Stop` appear. `Health: up` is gone.

Manual (localhost is allowed without HTTPS): click Start, grant the microphone, wait until status contains `Connected` or a session-error string from `/api/session`. Click Stop. Confirm the browser tab no longer shows a microphone-in-use indicator.

## Pass / fail

| Check | Pass | Fail |
| --- | --- | --- |
| Channel label | `createDataChannel("oai-events")` before `createOffer` | Offer first, or a different label |
| Live start | No `session.start` on the data channel | Client sends `session.start` |
| Captions | Input and output deltas append independently | One caption overwrites the other |
| Stop | `session.close` then wait up to 15s | Peer closed immediately after send |
| Fallback split | Realtime events live only in `realtime-webrtc.ts` | One file handles both event contracts |
| Screenshots | `images/before/home.png` and `images/after/call-controls.png` exist | Missing image files |

## Out of scope

- Prompt text from the principles markdown (Step 5)
- Role labels, cost note, and layout polish (Step 6)
