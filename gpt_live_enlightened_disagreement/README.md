# GPT-Live enlightened disagreement debate

The experiment is a one-page Next.js app. You argue for socialism out loud, and a GPT-Live-1 agent replies as a capitalist devil's advocate using Kellogg enlightened disagreement rules.

You need Node.js 22.6 or later.

## Local run

```bash
npm install
cp .env.example .env.local
```

Put the OpenAI project key in `.env.local` as `OPENAI_API_KEY`. Do not prefix it with `NEXT_PUBLIC_`. The key is on the server.

```bash
npm run dev
```

Open `http://localhost:3000`. The page heading is `GPT-Live debate`, and the role line is `You argue for socialism. The agent is a capitalist devil's advocate.` You start and stop the call with Start and Stop, and the cost note is `Voice is billed at $0.05 per minute. Grant the microphone only if you accept that charge. The OpenAI key stays on the server.`

## Tests and build

```bash
npm test
npm run build
```
