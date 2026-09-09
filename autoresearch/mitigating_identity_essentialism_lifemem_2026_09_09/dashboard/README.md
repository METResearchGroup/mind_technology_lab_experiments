# LifeMem dashboard

Next.js app that reads `public/data/results.json`.

Live Vercel preview: https://temporary-prompt-birch-7xdekgc.vercel.app

Claim that anonymous deploy to keep it: https://vercel.com/claim-deployment?code=81a2f69e-26b4-4b8c-9839-e6ce949a0df1

Durable static mirror: https://huggingface.co/spaces/mtorres98/lifemem-identity-dashboard

```bash
npm install
npm run dev
```

Regenerate the JSON from the replication folder:

```bash
uv run python ../scripts/export_dashboard_data.py
```

Static export for Hugging Face Spaces:

```bash
NEXT_OUTPUT=export npm run build
```
