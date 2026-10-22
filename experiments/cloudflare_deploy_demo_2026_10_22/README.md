# Cloudflare deploy demo

This folder is a small app you can deploy to Cloudflare. It is here so we can see the current path for a FastAPI backend and a Next.js frontend on Workers, including storage bindings and secrets, before moving larger services off Railway.

This copy is deployed. The Live URLs section has the workers.dev addresses. Cloudflare credentials for this lab live in AWS Secrets Manager in `us-east-2`, under the secret names `cloudflare-api-token` and `cloudflare-r2-credentials`. Those names are not the token values. Do not print or commit the values.

## How it fits together

```
Browser
  |  GET /health and GET /api/notes
  |  (the browser calls the API directly, so the API allows this page's origin)
  v
Next.js Worker (vinext)          name: cloudflare-deploy-demo-web
  |  POST /api/notes
  |  Authorization: Bearer NOTE_TOKEN
  |  (a server action adds the token and calls the API through a service binding)
  v
FastAPI Worker (Python)          name: cloudflare-deploy-demo-api
  |
  v
D1 database                      name: cloudflare-deploy-demo
                                 table: notes
```

A Worker is a small program Cloudflare runs on its network when a request arrives. A binding is a named connection from that program to another Cloudflare resource, such as a database or a secret. D1 is Cloudflare's SQLite database.

The API has three routes.

- `GET /health` returns JSON with `status`, `storage` (`d1`), and `secret_configured`. The last field is true or false. The response does not include the token.
- `GET /api/notes` returns the latest 20 notes. Reading is public.
- `POST /api/notes` stores one note. The JSON body is `{ "body": "..." }` and the text can be 1 to 200 characters. The request must send `Authorization: Bearer <NOTE_TOKEN>`. A missing or wrong token gets 401. A missing token configuration or a database error gets 503.

The page at `/` loads health and notes in the browser, so you can see the cross-origin headers. The save form posts to the Next.js Worker. That Worker reads `NOTE_TOKEN` from its own secret and calls the API through a service binding named `API`.

A service binding is a direct Worker-to-Worker call. Both of these Workers are on `workers.dev`, which is one Cloudflare zone. A global `fetch()` from one Worker to another Worker on that same zone fails. The browser calls are not affected, because they come from the public internet.

## Why this stack

The API is a Python Worker running FastAPI, not a Cloudflare Container.

Cloudflare's current Python Workers docs show FastAPI running in a Worker through the built-in ASGI adapter. ASGI is the Python web server interface FastAPI already uses. The Worker entry is `Default = asgi.entrypoint(app)`, and the Wrangler config sets the `python_workers` flag. For a compatibility date of 2026-09-08 or later, that runtime is Python 3.14. This demo's API uses compatibility date 2026-10-22. Local `pywrangler dev` on Wrangler 4.152 accepts that date.

A Container would also run FastAPI, because a Container is a normal Linux image. It is the wrong default for this demo. You pay for a running container, cold starts are often a few seconds, and you still put a Worker in front of it. Use a Container when the program does not fit a Worker. The comparison section below lists those cases.

The page is Next.js on Workers through vinext, not OpenNext.

The Next.js on Workers guide, updated August 25, 2026, says to use vinext for new apps. The OpenNext guide, updated October 12, 2026, says the same thing, and it keeps OpenNext for an existing OpenNext app that cannot move yet. vinext is a Vite plugin that runs the Next.js App Router, including server actions, and deploys the result as a Worker. This app was created with `create-vinext-app`.

Current vinext setup for a new Cloudflare app writes `cloudflare.config.ts` and deploys with the `cf` command. This demo passes `--legacy-wrangler-cloudflare-init`, so the page has a `wrangler.jsonc` and deploys with Wrangler. That matches the request for Wrangler config files and `wrangler secret`. The `cf` path is the one vinext documents as the default for a brand new app. Either path still runs on Workers.

State is D1, not Workers KV. KV is a key-value store with a daily write limit that is tight on the free plan (1,000 writes a day). D1 is closer to the database a FastAPI service already expects, and the migration file shows how a binding is created and applied. The Python Worker reads it from the request environment as `env.DB`.

The two apps are separate Workers on purpose. The browser uses the public API URL, so the CORS headers are visible. CORS is the rule that lets a page on one origin call an API on another. The save path uses a service binding, because that call starts inside the page Worker.

## API token permissions

Create the token in the Cloudflare dashboard with the custom token builder. These names match the user token builder, which labels write access as Edit. An account-owned token uses Write for the same groups, so D1 Edit there is D1 Write, and Workers Scripts Edit is Workers Scripts Write.

Set `CLOUDFLARE_ACCOUNT_ID` in the environment as well. Wrangler uses it so the token does not need permission to list every account.

### Minimum to deploy and manage this demo

This is enough to create both Workers, deploy them to `*.workers.dev`, create the D1 database, apply the remote migration, and set `NOTE_TOKEN`.

- Account > Workers Scripts > Edit
- Account > D1 > Edit

You do not need a zone permission for a `workers.dev` hostname. Add Zone > Workers Routes > Edit only if you attach the Worker to a route or a custom domain on a zone. After that route exists, a later deploy that does not change the route does not need the zone permission.

You do not need Account > Workers KV Storage > Edit, Account > Containers > Edit, Account > Workers AI > Read, or Account > AI Gateway > Edit. This demo does not use those products.

Binding an existing D1 database into a Worker does not, by itself, require a D1 permission. Creating the database and running `d1 migrations apply --remote` does.

### If the token screen shows Workers roles instead of Workers Scripts

On September 15, 2026 Cloudflare added Workers roles for account API tokens. In that screen the permission is a role, not Read or Edit.

- To create these Workers the first time, grant Admin at the Workers product scope. Editor cannot create a Worker, and you cannot grant a per-Worker role before the Worker exists.
- Also grant Account > D1 > Edit, or D1 Write on an account-owned token.
- After both Workers exist, Editor on those two Workers is enough to deploy again and to run `wrangler secret put`.

The older Workers Scripts Edit permission still works. The roles page says there is no deprecation date yet.

The vinext docs mention an "Edit Cloudflare Workers" token template. That template is broader than this list. Use the two permissions above if you want the smallest token that can still deploy this demo.

### Logs and observability

These are not required to deploy.

- Account > Workers Tail > Read lets you run `wrangler tail` for live logs. A token that already has Workers Scripts Edit can also tail, because that permission includes the tail API.
- On the new roles screen, Metadata Read-Only is the minimum role for `wrangler tail` and for metrics, logs, and traces in the dashboard. It does not reveal secret values.
- The roles page still names the older groups Workers Observability Read and Workers Observability Edit. The permissions catalog updated October 12, 2026 does not list a Workers Observability group. If your builder shows it, Read matches viewing observability data, and Edit matches the stored log query API, which is a write call. Metadata Read-Only is the replacement for Workers Observability Read and for Workers Tail Read.
- Account > Logs > Read is a different product. It covers Logpull and Instant Logs, not Workers Logs.

Workers Logs pricing is in the cost section.

### Cloudflare MCP servers

An MCP server is a remote tool endpoint an agent can call. Cloudflare's docs, updated October 22, 2026, say the API server is the one that covers the whole API. You connect it at `https://mcp.cloudflare.com/mcp`. With OAuth, you pick permissions in the browser. With a bearer token, the token needs the same permissions as the API calls you want the agent to make.

To deploy and manage this demo through that server, use the same minimum list as above. The server does not add a separate scope on top of those permissions.

For an account-owned token, the MCP server README also asks for Account Resources Read so the server can discover the account id. In the permissions catalog, that access is Account > Account Settings > Read. You can skip it when `CLOUDFLARE_ACCOUNT_ID` is already set, which is what the deploy steps below do.

These servers do not need an account token.

- `https://docs.mcp.cloudflare.com/mcp` searches the public docs.
- `https://agents.cloudflare.com/mcp` searches the Agents SDK docs.

These product servers are optional. The API server already covers their APIs. This demo does not need them. The matching catalog permissions, if you connect the product server with a token, are below. The docs page does not publish a separate permission table for each server.

- Containers, `https://containers.mcp.cloudflare.com/mcp`. Changing containers uses Account > Containers > Edit.
- Browser Run, `https://browser.mcp.cloudflare.com/mcp`. The docs do not name a token permission for this server.
- Digital Experience Monitoring, `https://dex.mcp.cloudflare.com/mcp`. Account > Cloudflare DEX > Read.
- CASB, `https://casb.mcp.cloudflare.com/mcp`. Account > Cloudflare CASB > Read.

### Workers AI, AI Gateway, and deploying from an agent

This demo does not call a model. The permissions below are only here because a later service might.

- Running a model on Workers AI uses Account > Workers AI > Read. Changing Workers AI settings uses Account > Workers AI > Edit. The free allocation is 10,000 Neurons a day. Neurons are Cloudflare's unit for model compute. Usage above that requires the Workers Paid plan at $0.011 per 1,000 Neurons. Some larger models require the Paid plan or prepaid AI Gateway credits even for the first request.
- AI Gateway is the proxy in front of model providers. Its logging, caching, and rate limits do not add a separate Workers subscription. Reading a gateway uses Account > AI Gateway > Read. Creating or changing one uses Account > AI Gateway > Edit. Those two permissions are account-wide. You cannot limit them to one gateway. Running a model through the gateway still needs the model provider permission, which for Workers AI is Account > Workers AI > Read.
- An agent that deploys a Worker uses the same Workers permission as a person running `wrangler deploy`. The versions and deployments API is the HTTP form of that deploy. It does not add another permission group. Workers for Platforms is a different product, and you only need it if you are publishing Workers into other people's accounts.

## Set up and run it locally

You need Node.js 22, npm, and `uv`. The API project asks for Python 3.13 or newer. `uv sync` downloads Python 3.14, which matches the Worker runtime.

From the repository root:

```bash
cd experiments/cloudflare_deploy_demo_2026_10_22/backend
uv sync
cp .dev.vars.example .dev.vars
uv run pywrangler d1 migrations apply cloudflare-deploy-demo --local
uv run pywrangler dev --port 8787 --ip 127.0.0.1
```

`.dev.vars` is gitignored. The example value `NOTE_TOKEN=local-dev-only` is only for your machine. `pywrangler dev` also installs Python packages into `python_modules/` for the Worker runtime. That directory is gitignored.

In another shell:

```bash
cd experiments/cloudflare_deploy_demo_2026_10_22/frontend
npm ci
cp .dev.vars.example .dev.vars
npm run dev
```

Use the same `NOTE_TOKEN` value in both `.dev.vars` files. The page listens on `http://127.0.0.1:3001`. The API listens on `http://127.0.0.1:8787`.

The frontend compatibility date is 2026-10-19. The Workers runtime bundled with this vinext install rejects 2026-10-22 during local dev. 2026-10-19 is the newest date that runtime accepts.

Check the API without printing the token:

```bash
python3 experiments/cloudflare_deploy_demo_2026_10_22/scripts/smoke.py \
  http://127.0.0.1:8787 http://127.0.0.1:3001
```

The script checks health, the notes list, a write without a token (that must be 401), and the CORS headers. It does not read `.dev.vars`. It sends a User-Agent, because `workers.dev` answers `1010` when that header is missing.

`npm run build` in `frontend/` produces the Worker bundle under `dist/`. `npm run start` serves that bundle locally with Wrangler on port 8788. The API allows that origin too.

`npm run build` is the production build for this app. It is a Vite build through vinext. Do not use `next build` or the OpenNext build for this project. Those commands belong to the OpenNext path, which this app does not use.

## Deploy

Load `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` from the Secrets Manager secret `cloudflare-api-token`. The R2 keys are in `cloudflare-r2-credentials`. This demo does not use R2. Do not put either secret in a file in git, and do not print the values.

The token used for this deploy is account-scoped. `GET /user/tokens/verify` returns 401. `GET /accounts/{account_id}/tokens/verify` returns active.

`backend/wrangler.jsonc` already has the live D1 id for database `cloudflare-deploy-demo`: `89b1d314-af1f-45e1-bbe7-6268042b3703`. The migration `0001_notes.sql` is applied on that database. On an account that does not have the database yet, create it and put the new id in the config:

```bash
cd experiments/cloudflare_deploy_demo_2026_10_22/backend
uv run pywrangler d1 create cloudflare-deploy-demo
```

The account also needs a `workers.dev` subdomain before the first deploy. This account uses `mind-technology-lab`, so the Workers are at `https://<name>.mind-technology-lab.workers.dev`.

Set `NOTE_TOKEN` with `secret put`. That command asks you to paste the token. Do not pass the token as an argument. That command also uploads the Worker.

```bash
uv run pywrangler d1 migrations apply cloudflare-deploy-demo --remote
uv run pywrangler secret put NOTE_TOKEN
uv run pywrangler deploy
```

Wrangler prints an API URL like `https://cloudflare-deploy-demo-api.mind-technology-lab.workers.dev`.

Put that URL in `frontend/wrangler.jsonc` as `vars.API_BASE_URL`. The `services` entry named `API` must point at the API Worker name. Then build and set the same token on the page Worker.

```bash
cd experiments/cloudflare_deploy_demo_2026_10_22/frontend
npm run build
npx wrangler secret put NOTE_TOKEN --config dist/server/wrangler.json
```

Paste the token at the prompt. Wrangler deploys the page and prints a URL like `https://cloudflare-deploy-demo-web.<account>.workers.dev`.

Add that origin, with no path, to `CORS_ORIGINS` in `backend/wrangler.jsonc`. The value is a comma-separated list. Then deploy the API again.

```bash
cd experiments/cloudflare_deploy_demo_2026_10_22/backend
uv run pywrangler deploy
```

Later updates:

```bash
cd experiments/cloudflare_deploy_demo_2026_10_22/backend
uv run pywrangler deploy

cd experiments/cloudflare_deploy_demo_2026_10_22/frontend
npm run deploy
```

`npm run deploy` runs `vinext-cloudflare deploy`, which builds the app and deploys it with Wrangler.

## Secrets

`NOTE_TOKEN` is a Worker secret on both Workers. It is not in `wrangler.jsonc` under `vars`, and it is not in git.

- Local API and page reads come from `.dev.vars`.
- `.dev.vars.example` only shows the local placeholder.
- Production values are set with `pywrangler secret put` and `wrangler secret put`.
- `secrets.required` in both Wrangler configs makes a deploy fail when `NOTE_TOKEN` is missing.
- The health check reports whether the secret is present. It does not return the value.
- The page's server action reads the secret on the Worker and sends it through the `API` service binding. The browser script does not.

`CORS_ORIGINS` and `API_BASE_URL` are plain variables. They are public URLs, not secrets.

## Cost

Prices below are from the Workers pricing page, updated October 2, 2026, and the limits page, updated October 12, 2026. They are account prices, not a quote for a larger migration.

On the Workers Free plan this demo should cost $0 if it stays inside the daily caps.

- Workers requests: 100,000 a day for the whole account, resetting at midnight UTC. Requests to static assets are free and unlimited. If you turn on Workers Caching, the pricing page says those cached requests are billed like normal Worker requests.
- CPU time: 10 milliseconds per invocation. Waiting on D1 or `fetch` does not count as CPU time. A request that goes over the limit returns error 1102.
- D1: 5 million rows read a day, 100,000 rows written a day, and 5 GB stored. Free D1 limits are enforced.
- Workers Logs: 200,000 events a day, kept for 3 days. Both Wrangler configs enable logs and traces at a sampling rate of 1, so every request can write a log. Turn the sampling rate down if a busier app gets close to the cap.

The Workers Paid plan has a $5 monthly minimum. This demo's traffic fits inside the included amounts, so the bill for the demo itself stays at that $5 if the account is already on Paid.

- 10 million requests included, then $0.30 per extra million. There is no duration charge and no Workers egress charge.
- 30 million CPU milliseconds included, then $0.02 per extra million. The default cap is 30 seconds per HTTP request, and you can raise it to 5 minutes.
- D1 included usage starts at 25 billion rows read, 50 million rows written, and 5 GB stored. Extra reads are $0.001 per million rows, extra writes are $1.00 per million rows, and extra storage is $0.75 per GB-month.
- Workers Logs: 20 million events a month included, then $0.60 per extra million, kept for 7 days. On December 1, 2026, Workers Logs move to Cloudflare Observability pricing.

KV, if you used it instead of D1, is 100,000 reads and 1,000 writes a day on Free. Paid includes 10 million reads and 1 million writes a month.

Containers are not on the Free plan. On Paid, the included monthly amounts are 25 GiB-hours of memory, 375 vCPU-minutes, and 200 GB-hours of disk. Extra use is $0.0000025 per GiB-second, $0.000020 per vCPU-second, and $0.00000007 per GB-second. Disk is ephemeral. See the Containers pricing page for network egress.

Workers AI is separate from this demo. The first 10,000 Neurons each day are free. Above that, Paid accounts pay $0.011 per 1,000 Neurons.

## How this compares with Railway

Railway runs a long-lived container. A Worker runs when a request, a cron trigger, or another event arrives, and then it stops. That difference decides what can move as-is.

FastAPI request and response APIs can move to Python Workers. FastAPI itself is a supported framework. The practical limits are below.

- The runtime is Pyodide, a Python build for Workers, not CPython. A package with a C extension works only when a Pyodide wheel exists. Check that before you assume a current `requirements.txt` will install.
- Free CPU time is 10 milliseconds per request. The Workers docs say a typical Worker uses about 2.2 milliseconds, and a heavier request often uses 10 to 20 milliseconds. A real FastAPI service with a large dependency set can miss the free cap even when it spends most of its time waiting on a database. The Paid plan, with a 30 second default CPU cap, is the realistic plan for those services. Waiting on the network does not consume CPU time.
- Startup of the top-level script must finish within 1 second, and each isolate has 128 MB of memory. A large import at import time is the usual way to miss the startup cap. A dry-run package of this API is about 9.4 MiB uncompressed, which is under the 64 MiB Worker size limit, but it is large enough that startup time is the thing to watch.
- D1 is SQLite. It is not a stand-in for Postgres. You can keep Postgres and connect from a Worker through Hyperdrive, which is Cloudflare's connection pooler for an external database. You can also keep the database where it is and call it from a Container.

A long-running Jetstream ingester does not fit a Worker. Jetstream is a continuous stream of events. A Worker can hold a WebSocket while the caller stays connected, but it is not a process you leave running, and a runtime update can close that connection after a grace period of up to 20 minutes. Each invocation can also have only 6 connections waiting for response headers at the same time. Put the ingester in a Container. A Container has no fixed maximum runtime, but it is not an always-on machine either. The default is to stop it after 10 minutes without activity, disk is wiped when it sleeps, and a host restart sends SIGTERM and then SIGKILL after 15 minutes. The process has to catch SIGTERM, reconnect, and store its cursor outside the container disk. Containers require the Workers Paid plan. There is no built-in autoscaler for a stateless container fleet yet.

Cron backup jobs only partly fit. A Cron Trigger can run on a schedule. Free accounts get 5 cron triggers per account, and Paid accounts get 250. The wall clock limit is 15 minutes. CPU time on Free is still 10 milliseconds, which is too small for a backup. On Paid, CPU time is 30 seconds when the cron interval is under 1 hour, and 15 minutes when the interval is 1 hour or more. A job that needs a shell, `pg_dump`, local disk, or a long upload does not fit. Run that job in a Container, or split it into a Workflow. A Workflow step has no wall clock limit while it waits on I/O, but each step still has the CPU cap, and the free CPU cap is still 10 milliseconds.

## Live URLs

- API: `https://cloudflare-deploy-demo-api.mind-technology-lab.workers.dev`
- Page: `https://cloudflare-deploy-demo-web.mind-technology-lab.workers.dev`
- Health: `https://cloudflare-deploy-demo-api.mind-technology-lab.workers.dev/health`
- Notes: `https://cloudflare-deploy-demo-api.mind-technology-lab.workers.dev/api/notes`

D1 database name: `cloudflare-deploy-demo`. Database id: `89b1d314-af1f-45e1-bbe7-6268042b3703`.

## Sources

Workers and Python:

- [Cloudflare Workers](https://developers.cloudflare.com/workers/)
- [Python Workers](https://developers.cloudflare.com/workers/languages/python/)
- [FastAPI on Python Workers](https://developers.cloudflare.com/workers/languages/python/packages/fastapi/)
- [Python web framework support, September 2, 2026](https://developers.cloudflare.com/changelog/post/2026-09-02-python-workers-web-framework-support/)
- [Python 3.14 on Workers, September 8, 2026](https://developers.cloudflare.com/changelog/post/2026-09-08-python-workers-314/)
- [Workers limits, October 12, 2026](https://developers.cloudflare.com/workers/platform/limits/)
- [Workers pricing, October 2, 2026](https://developers.cloudflare.com/workers/platform/pricing/)
- [Secrets](https://developers.cloudflare.com/workers/configuration/secrets/)

Next.js:

- [Next.js on Workers, August 25, 2026](https://developers.cloudflare.com/workers/framework-guides/web-apps/nextjs/)
- [OpenNext on Workers, October 12, 2026](https://developers.cloudflare.com/workers/framework-guides/web-apps/opennext/)
- [vinext](https://github.com/cloudflare/vinext)

Storage and containers:

- [D1](https://developers.cloudflare.com/d1/)
- [Query D1 from Python Workers](https://developers.cloudflare.com/d1/examples/query-d1-from-python-workers/)
- [Workers KV](https://developers.cloudflare.com/kv/)
- [Containers](https://developers.cloudflare.com/containers/)
- [Containers pricing, October 5, 2026](https://developers.cloudflare.com/containers/platform/pricing/)
- [Containers FAQ, October 5, 2026](https://developers.cloudflare.com/containers/faq/)

Permissions, MCP, and AI:

- [API token permissions, October 12, 2026](https://developers.cloudflare.com/fundamentals/api/reference/permissions/)
- [Workers roles and permissions, September 15, 2026](https://developers.cloudflare.com/workers/authorization/workers/)
- [Granular Worker permissions, September 15, 2026](https://developers.cloudflare.com/changelog/post/2026-09-15-granular-worker-permissions/)
- [Cloudflare MCP servers, October 22, 2026](https://developers.cloudflare.com/agents/model-context-protocol/cloudflare/servers-for-cloudflare/)
- [Cloudflare MCP server README](https://github.com/cloudflare/mcp)
- [Workers AI](https://developers.cloudflare.com/workers-ai/)
- [Workers AI pricing, October 20, 2026](https://developers.cloudflare.com/workers-ai/platform/pricing/)
- [Cloudflare AI](https://developers.cloudflare.com/ai/)
- [AI Gateway pricing](https://developers.cloudflare.com/ai-gateway/reference/pricing/)
- [Workers versions API for programmatic deploys, September 3, 2025](https://developers.cloudflare.com/changelog/post/2025-09-03-new-workers-api/)
- [Observability pricing](https://developers.cloudflare.com/observability/pricing/)
