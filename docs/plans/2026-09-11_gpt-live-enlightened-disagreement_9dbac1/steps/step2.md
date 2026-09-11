# Step 2: Scaffold the Next.js experiment

## Goal

Stand up a Next.js App Router app at `gpt_live_enlightened_disagreement/` that boots locally, shows a health page, and documents server-only env. No OpenAI calls in this step.

## Scope

- Caller: `npm run dev` in `gpt_live_enlightened_disagreement/` then `GET /` renders the health page.
- Task: create the app, env example, README, and a health line that does not print secrets.
- Out of scope: session route, WebRTC, prompts, Vercel project.

## Files to inspect

- `gpt_live_enlightened_disagreement/ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md` (must already exist from Step 1; do not move it)
- Root `.gitignore` (already ignores `node_modules/`, `.next/`, `.env.*` except `.env.example`)
- `SETUP.md` (root Python tooling does not run this app)

## Files allowed to change

- `gpt_live_enlightened_disagreement/package.json`
- `gpt_live_enlightened_disagreement/package-lock.json`
- `gpt_live_enlightened_disagreement/tsconfig.json`
- `gpt_live_enlightened_disagreement/next.config.ts`
- `gpt_live_enlightened_disagreement/next-env.d.ts`
- `gpt_live_enlightened_disagreement/.env.example`
- `gpt_live_enlightened_disagreement/README.md`
- `gpt_live_enlightened_disagreement/src/app/layout.tsx`
- `gpt_live_enlightened_disagreement/src/app/page.tsx`
- `gpt_live_enlightened_disagreement/src/app/globals.css`
- `gpt_live_enlightened_disagreement/src/lib/env.ts`
- `gpt_live_enlightened_disagreement/eslint.config.mjs` or `.eslintrc.json` if `create-next-app` adds one

## Files forbidden to change

- `gpt_live_enlightened_disagreement/ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md`
- Root `pyproject.toml`, `uv.lock`, `.github/workflows/ci.yml`
- Any OpenAI client module (do not add the `openai` package yet)

## Work

1. From the repo root, create the app with Node 22. Do not use Tailwind. Use the App Router and `src/`.

```bash
node -v
```

Expected: a version string that is 22.6.0 or higher, for example `v22.14.0`.

```bash
npx --yes create-next-app@latest gpt_live_enlightened_disagreement --typescript --eslint --app --src-dir --no-tailwind --no-turbopack --use-npm --import-alias "@/*" --yes
```

Expected: the command exits 0. `gpt_live_enlightened_disagreement/src/app/page.tsx` exists. The principles markdown is still at `gpt_live_enlightened_disagreement/ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md`.

If `create-next-app` refuses a non-empty folder because the principles file is already there, run the same command with `.` from inside that folder after moving the principles file to `/tmp/ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md`, then move it back to `gpt_live_enlightened_disagreement/ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md`.

2. Set `"engines": { "node": ">=22.6.0" }` in `gpt_live_enlightened_disagreement/package.json`.
3. Write `gpt_live_enlightened_disagreement/.env.example` with exactly the names below, no values that look like live keys:

```
OPENAI_API_KEY=
APP_ORIGIN=http://localhost:3000
```

4. Write `gpt_live_enlightened_disagreement/src/lib/env.ts` that reads `OPENAI_API_KEY` and `APP_ORIGIN`. `getOpenAIKey()` throws if the key is missing or whitespace. `getAppOrigin()` returns `APP_ORIGIN` if set, otherwise `http://localhost:3000` in development. Do not use a `NEXT_PUBLIC_` prefix for the key.
5. Change `src/app/page.tsx` to a server component that renders the heading `GPT-Live debate` and the line `Health: up`. Do not print env values.
6. Write `gpt_live_enlightened_disagreement/README.md` covering what the page is, required Node version, `npm install`, `cp .env.example .env.local`, `npm run dev`, and that the OpenAI key stays on the server.
7. Add `outputFileTracingIncludes` in `next.config.ts` so `/api/session` (added in Step 3) will include `./ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md`. Putting the include in Step 2 avoids a later tracing miss.

## Commands (exact)

From `gpt_live_enlightened_disagreement/`:

```bash
cp .env.example .env.local
npm install
npm run build
```

Expected: `next build` exits 0.

```bash
npm run dev
```

Expected: process listens on `http://localhost:3000`.

In a second shell:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/
```

Expected output: `200`

```bash
curl -s http://localhost:3000/ | grep -E "Health: up|GPT-Live debate"
```

Expected: both strings appear. The body must not contain `sk-`.

Stop the dev server after the checks. Leave it stopped so Step 4 can start a clean one.

## Pass / fail

| Check | Pass | Fail |
| --- | --- | --- |
| App path | `src/app/page.tsx` exists under `gpt_live_enlightened_disagreement/` | App at repo root |
| Principles file | Still at `gpt_live_enlightened_disagreement/ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md` | File overwritten or deleted |
| Boot | `curl` returns `200` and `Health: up` | Non-200 or crash |
| Secrets | HTML has no API key | Key in HTML |
| Node | `package.json` engines require `>=22.6.0` | No engines field |
| Scope | No `openai` dependency | `openai` added early |

## Out of scope

- `src/app/api/session/route.ts` (Step 3)
- Client WebRTC (Step 4)
- Debate prompts (Step 5)
