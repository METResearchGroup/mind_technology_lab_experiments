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

Open `http://localhost:3000`. The page heading is `GPT-Live debate`. The role line is `You argue for socialism. The agent is a capitalist devil's advocate.` Start and Stop control the call. The cost note is `Voice is billed at $0.05 per minute. Grant the microphone only if you accept that charge. The OpenAI key stays on the server.`

## Tests and build

```bash
npm test
npm run build
```
