# Step 3: Create Live sessions and cover the route with tests

## Goal

Add `POST /api/session` that exchanges a browser SDP offer for a GPT-Live-1 WebRTC session, keeps the OpenAI key on the server, and fails clearly on bad origin, missing SDP, missing key, or Live-unavailable. Tests fail first, then pass, against a stubbed OpenAI client.

## Scope

- Caller: `gpt_live_enlightened_disagreement/src/app/api/session/route.ts` `POST`.
- Task: origin check, SDP validation, `client.live.create`, JSON 201 on success, typed errors, Realtime fallback when Live returns 403 or 404.
- Out of scope: browser microphone UI, loading the principles file into prompts (stub instructions are allowed until Step 5), Vercel deploy.

## Files to inspect

- `gpt_live_enlightened_disagreement/src/lib/env.ts`
- `gpt_live_enlightened_disagreement/src/app/page.tsx`
- `gpt_live_enlightened_disagreement/package.json`
- OpenAI WebRTC guide: https://developers.openai.com/api/docs/guides/voice-webrtc
- OpenAI Realtime getting started: https://developers.openai.com/api/docs/guides/realtime

## Files allowed to change

- `gpt_live_enlightened_disagreement/package.json` (add `openai` and `vitest` plus a `test` script)
- `gpt_live_enlightened_disagreement/package-lock.json`
- `gpt_live_enlightened_disagreement/vitest.config.ts` (create)
- `gpt_live_enlightened_disagreement/src/lib/origin.ts` (create)
- `gpt_live_enlightened_disagreement/src/lib/openai-live.ts` (create)
- `gpt_live_enlightened_disagreement/src/app/api/session/route.ts` (create)
- `gpt_live_enlightened_disagreement/src/lib/prompts.ts` (stub `getLiveInstructions()` and `getBackendInstructions()` returning short placeholder strings until Step 5)
- `gpt_live_enlightened_disagreement/tests/origin.test.ts` (create)
- `gpt_live_enlightened_disagreement/tests/session-route.test.ts` (create)
- `gpt_live_enlightened_disagreement/src/lib/env.ts` only if tests need a testable export

## Files forbidden to change

- `gpt_live_enlightened_disagreement/ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md`
- `gpt_live_enlightened_disagreement/src/app/page.tsx` (still health-only)
- Root Python CI files

## Contracts

### `isAllowedOrigin(origin: string | null): boolean`

Return true when `origin` equals one of:

- `getAppOrigin()`
- `http://localhost:3000`
- `http://127.0.0.1:3000`
- `https://${process.env.VERCEL_URL}` when `VERCEL_URL` is set

Otherwise return false. Null origin is false.

### `POST /api/session`

Request JSON: `{ "sdp": string }`. Runtime is Node, not Edge. `export const runtime = "nodejs"`.

| Condition | Status | Body |
| --- | --- | --- |
| Origin not allowed | 403 | `{ "error": "Unexpected request origin" }` |
| `sdp` missing, not a string, or whitespace only | 400 | `{ "error": "An SDP offer is required" }` |
| `OPENAI_API_KEY` missing | 503 | `{ "error": "Set OPENAI_API_KEY on the server" }` |
| Live create succeeds | 201 | `{ "mode": "live", "session": { "id": string }, "transport": { "type": "webrtc", "sdp": string } }` |
| Live create returns 403 or 404 | 201 | `{ "mode": "realtime", "client_secret": string }` after a successful Realtime `client_secrets` call for model `gpt-realtime-2.1` |
| Live create other error, or Realtime fallback fails | 502 | `{ "error": "Live session creation failed" }` |

Live create arguments, using the official SDK:

- `session.model`: `gpt-live-1`
- `session.instructions`: return value of `getLiveInstructions()`
- `session.audio.output.voice`: `marin`
- `session.delegation.type`: `responses`
- `session.delegation.responses.model`: `gpt-5.6-terra`
- `session.delegation.responses.instructions`: return value of `getBackendInstructions()`
- `session.delegation.responses.tools`: `[{ type: "web_search" }]`
- `session.delegation.responses.tool_choice`: `auto`
- `transport.type`: `webrtc`
- `transport.sdp`: the request SDP

Do not send `session.start` on a data channel from the server. Construct `OpenAI` with `maxRetries: 0`.

Realtime fallback (only after Live 403/404): `POST https://api.openai.com/v1/realtime/client_secrets` with JSON `{ "session": { "type": "realtime", "model": "gpt-realtime-2.1", "audio": { "output": { "voice": "marin" } } } }` using the server key. Return `client_secret` from `value` on that response. Do not put the project API key in the response.

Export a `createSessionFromSdp({ origin, sdp })` function so tests call the same logic as the route. The route file may wrap that function.

## Implement-from-spec phases

### Phase 1. Scope

Caller is `POST` in `src/app/api/session/route.ts`. File tree as in Files allowed to change.

### Phase 2. Scaffold

Create the modules with imports that resolve from tests. Bodies may throw `Error("not implemented")`.

### Phase 3. Contracts

Lock the tables above. Do not implement Live HTTP yet.

### Phase 4. Test design (failing)

Write the tests below before filling in `createSessionFromSdp` behavior.

1. **Given** origin `http://localhost:3000` **when** `isAllowedOrigin` **then** true.
2. **Given** origin `https://evil.example` **when** `isAllowedOrigin` **then** false.
3. **Given** `VERCEL_URL=my-app.vercel.app` and origin `https://my-app.vercel.app` **when** `isAllowedOrigin` **then** true.
4. **Given** a missing SDP **when** `createSessionFromSdp` **then** status 400.
5. **Given** a disallowed origin **when** `createSessionFromSdp` **then** status 403.
6. **Given** missing `OPENAI_API_KEY` **when** `createSessionFromSdp` **then** status 503.
7. **Given** a stub `live.create` that returns `{ session: { id: "live_1" }, transport: { type: "webrtc", sdp: "answer" } }` **when** `createSessionFromSdp` with allowed origin and SDP `offer` **then** status 201 and `mode` `live`.
8. **Given** a stub `live.create` that throws with `status: 404` and a stub Realtime secrets call that returns `{ value: "ek_test" }` **when** `createSessionFromSdp` **then** status 201 and `mode` `realtime`.
9. **Given** a stub `live.create` that throws with `status: 500` **when** `createSessionFromSdp` **then** status 502.

Inject the OpenAI client through a parameter or a testable module export. Do not hit the network.

### Phase 5. Implement units of work, in this order

1. `isAllowedOrigin`
2. SDP and key checks
3. Live create success path
4. Live 403/404 fallback
5. Other Live errors to 502
6. Wire `POST` to `createSessionFromSdp`

Each unit is its own Git commit.

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

## Pass / fail

| Check | Pass | Fail |
| --- | --- | --- |
| Tests exist | `tests/session-route.test.ts` and `tests/origin.test.ts` exist | Tests only in comments |
| Order | Tests committed before Live HTTP implementation | Implementation first |
| Key | Response JSON never includes `OPENAI_API_KEY` | Key in body |
| Live vs Realtime | Fallback only on 403/404 | Fallback on every error |
| Health page | `/` still health-only | Debate UI added early |

## Out of scope

- `RTCPeerConnection` in the browser (Step 4)
- Reading the principles markdown into prompts (Step 5 may replace the stub strings)
