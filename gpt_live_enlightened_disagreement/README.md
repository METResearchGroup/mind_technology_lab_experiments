# GPT-Live enlightened disagreement debate

A one-page Next.js experiment. You argue for socialism out loud. A GPT-Live-1 agent replies as a capitalist devil's advocate using Kellogg enlightened disagreement moves.

Requires Node.js 22.6 or later.

## Local run

```bash
npm install
cp .env.example .env.local
```

Put the OpenAI project key in `.env.local` as `OPENAI_API_KEY`. Do not prefix it with `NEXT_PUBLIC_`. The key stays on the server.

```bash
npm run dev
```

Open `http://localhost:3000`. The health page should show `GPT-Live debate` and `Health: up`.

## Tests and build

```bash
npm test
npm run build
```
