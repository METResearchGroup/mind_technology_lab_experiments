# Step 7: Deploy to Vercel and verify the call

## Goal

Create a Vercel project whose Root Directory is `gpt_live_enlightened_disagreement/`, set `OPENAI_API_KEY` on the project, turn on Vercel Authentication for all deployments, and preview-deploy the feature branch. Confirm an unauthenticated visitor is blocked, a signed-in teammate can load the debate page, and a missing key fails with the Step 3 error string.

## Scope

- Caller: signed-in browser against the preview URL, plus `POST /api/session` on that origin.
- Task: project create with `deploy: false`, env, Authentication, preview deploy from the feature branch. Application feature code changes only if the preview build fails.
- Out of scope: production deploy from `main`, custom domain, custom in-app passwords, claiming that curl of the HTML means a microphone call works.

## Files to inspect

- `gpt_live_enlightened_disagreement/package.json`
- `gpt_live_enlightened_disagreement/next.config.ts`
- `gpt_live_enlightened_disagreement/.env.example`
- `gpt_live_enlightened_disagreement/.gitignore`

## Files allowed to change

- `gpt_live_enlightened_disagreement/vercel.json` only if a Root Directory or framework setting cannot be set on the project
- Application files only for a one-line build fix required to deploy; name the fix in the commit message

## Files forbidden to change

- Debate rules in `ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md`
- Adding `NEXT_PUBLIC_OPENAI_API_KEY`
- Custom password middleware or a second auth provider
- Deploying the production branch (`main`) as the first Live demo

## Project settings (exact)

- Team slug: `marktorres10s-projects`
- Team id: `team_EgUv9LU3C6giNlRgZU4lODvX`
- Project name: `gpt-live-enlightened-disagreement`
- Root Directory: `gpt_live_enlightened_disagreement`
- Repo: `METResearchGroup/mind_technology_lab_experiments`
- Framework: Next.js
- Node: `>=22.6.0` (already in `package.json` `engines`)

`create_git_project` with `deploy: true` would build production branch `main`, which does not contain the experiment app. Set `deploy: false`. Then preview-deploy the current branch.

## Work

1. Confirm local `npm test` and `npm run build` still exit 0 in `gpt_live_enlightened_disagreement/`.
2. Create or reuse the Vercel project with Vercel MCP `create_git_project`:

   - `repo`: `METResearchGroup/mind_technology_lab_experiments`
   - `teamId`: `team_EgUv9LU3C6giNlRgZU4lODvX`
   - `projectName`: `gpt-live-enlightened-disagreement`
   - `rootDirectory`: `gpt_live_enlightened_disagreement`
   - `deploy`: `false`

3. Set server env on Preview and Production (never `NEXT_PUBLIC_`):

   - `OPENAI_API_KEY` from the same secret already used locally (printenv, then `vercel env add`; do not pass the key as a CLI flag).
   - `APP_ORIGIN` after the first preview URL is known, or omit it and rely on `https://${VERCEL_URL}` in `isAllowedOrigin`.

4. Enable Vercel Authentication with Vercel MCP `update_project_deployment_protection`:

   - `teamId`: `team_EgUv9LU3C6giNlRgZU4lODvX`
   - `projectId`: the id returned by create (or the project slug `gpt-live-enlightened-disagreement`)
   - `ssoProtection`: `{ "enabled": true, "deploymentType": "all" }`

   Do not add password protection. Do not disable Authentication.

5. Preview-deploy the feature branch. Preferred order:

   1. `git push` of the implementation commits so Git Integration can build a preview (only after the user has approved implementation and the code exists).
   2. If Git Integration has no preview yet, from `gpt_live_enlightened_disagreement/` run `vercel deploy -y --no-wait --scope marktorres10s-projects` with `VERCEL_TOKEN` in the environment (not `--token`). Then `vercel inspect <url>`.

6. Verify:

   - Unauthenticated `GET` of the preview URL is `401` or `403` or an Authentication interstitial, not the debate HTML.
   - Signed-in teammate (Vercel Authentication) sees `GPT-Live debate` and the Step 6 role line.
   - With the key set, Start on HTTPS can reach `POST /api/session` and return 201 or a visible error body. A cloud agent without a microphone still must run local tests and the unauthenticated protection check.
   - Do not treat an unauthenticated curl `200` of a login page as proof that the debate works.

7. Record the preview URL in the PR body. Do not commit `.env`, `.env.local`, or `.vercel` secrets.

## Commands (exact)

From `gpt_live_enlightened_disagreement/`:

```bash
npm test
npm run build
```

Expected: both exit 0.

From repo root, after the project exists (replace nothing in the create call; MCP already has team id):

```bash
printenv OPENAI_API_KEY | wc -c
```

Expected: a positive byte count. If `0`, stop and set the key in the environment before `vercel env add`.

```bash
printenv OPENAI_API_KEY | vercel env add OPENAI_API_KEY preview --scope marktorres10s-projects --yes
printenv OPENAI_API_KEY | vercel env add OPENAI_API_KEY production --scope marktorres10s-projects --yes
```

Expected: CLI reports the variable was added. If the variable already exists, skip rather than printing the key.

Unauthenticated check after deploy (replace `PREVIEW_HOST`):

```bash
curl -s -o /tmp/preview-body.txt -w "%{http_code}" "https://PREVIEW_HOST/"
```

Expected: `401` or `403`, or `200` with a Vercel Authentication / login page that does not contain `start-call`. If the body contains `start-call`, Authentication is off; turn `ssoProtection` on and redeploy.

Signed-in check is browser-only (Vercel Authentication cookie). Confirm the role line and Start control.

## Pass / fail

| Check | Pass | Fail |
| --- | --- | --- |
| Root Directory | Project builds `gpt_live_enlightened_disagreement/` | Root of the Python monorepo |
| Deploy target | Preview of the feature branch | First demo is a production deploy of `main` |
| Key | `OPENAI_API_KEY` set on Vercel, absent from git | Key committed or missing |
| Authentication | `ssoProtection` enabled for `all` | Public preview that anyone can Start |
| Session | Signed-in Start either connects or shows the explicit JSON error | Silent spinner forever |
| Scope | No in-app password feature | Custom auth shipped |

## Out of scope

- Production promotion of `main` until the preview call is accepted
- Hugging Face Jobs, Qwen, S3 recordings
