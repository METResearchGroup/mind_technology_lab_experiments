# Step 1: Write the Kellogg principles file

## Goal

Write `gpt_live_enlightened_disagreement/ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md` so Step 5 can load it into prompts. The file is the only source of debate rules. Later steps must not invent extra rules in prompt strings.

## Scope

- Caller: `gpt_live_enlightened_disagreement/src/lib/prompts.ts` in Step 5 reads this file from process working directory.
- Task: create the markdown file with the required headings below, cited rules, named non-goals, quotes, and inference labels.
- Out of scope: Next.js app, OpenAI calls, UI, Vercel.

## Files to inspect

- `docs/plans/2026-09-11_gpt-live-enlightened-disagreement_9dbac1/plan.md`
- Fetch each URL below, and quote only what is on the page:
  - https://www.kellogg.northwestern.edu/academics-research/litowitz-center-enlightened-disagreement/
  - https://www.kellogg.northwestern.edu/academics-research/litowitz-center-enlightened-disagreement/curriculum/
  - https://www.kellogg.northwestern.edu/academics-research/litowitz-center-enlightened-disagreement/curriculum/residential-program/
  - https://www.kellogg.northwestern.edu/news/blog/2024/02/14/center-for-enlightened-disagreement/
  - https://www.kellogg.northwestern.edu/news/blog/2025/09/03/litowitz-center-enlightened-disagreement-naming-gift/
  - https://magazine.northwestern.edu/features/center-for-enlightened-disagreement-eli-finkel-nour-kteily-politics-republicans-democrats-kellogg-democracy
  - https://www.kellogg.northwestern.edu/magazine/features/spring-summer-2024/how-to-disagree/
  - https://insight.kellogg.northwestern.edu/article/take-5-how-to-talk-politics-constructively
  - https://insight.kellogg.northwestern.edu/article/reducing-partisan-animosity
  - https://insight.kellogg.northwestern.edu/article/bucking-the-party-line-may-not-be-as-perilous-as-people-think

## Files allowed to change

- `gpt_live_enlightened_disagreement/ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md` (create)
- `gpt_live_enlightened_disagreement/` directory if it does not exist yet (create the folder only; do not add Next.js files)

## Files forbidden to change

- Any file under `gpt_live_enlightened_disagreement/` other than the principles markdown
- `docs/plans/2026-09-11_gpt-live-enlightened-disagreement_9dbac1/plan.md`
- Root `pyproject.toml`, `SETUP.md`, `AGENTS.md`

## Required file shape

The markdown file must use the headings below, in the listed order, with no extra top-level headings:

1. `# Enlightened disagreement principles`
2. `## Source note`
3. `## Mission`
4. `## Non-goals`
5. `## Operating rules`
6. `## Devil's advocate procedure`
7. `## Quotes`

### Source note

State that https://www.kellogg.northwestern.edu/academics-research/litowitz-center-enlightened-disagreement/news-research/ has no papers listed. State that rules come from the URLs in Files to inspect. Any mapping onto a spoken devil's advocate must be labeled `Inference`.

### Mission

Three to five sentences. Name Eli Finkel and Nour Kteily. State that disagreement is kept and made more accurate, not shut down.

### Non-goals

Each bullet must be a Center or faculty statement, with a source URL. Include all of the claims below, in the file's own words plus a quote:

- They are not trying to get people to merely get along.
- Agreement is not the required result.
- The goal is not to make people milder and more acquiescent.
- They are not trying to eliminate disagreement.
- Not every moral view is treated as equal.
- Hard topics stay on the table.

### Operating rules

Include every rule below. Each rule is a `###` heading with a name. After the heading, write the rule in one or two sentences, a `Source:` URL, and either `Direct` or `Inference` on its own line.

1. Keep the disagreement
2. Hard on the issues, soft on the person
3. Make the gap accurate before you make it dramatic
4. Stop caricature and dehumanization
5. Repeat the other person's claim before you rebut it
6. Listen to understand, not only to reply
7. Self-distance when moral heat rises
8. Demand the strongest case against each speaker's own view
9. Move from positions to interests
10. Set engagement rules before the heat, and keep hate speech out of bounds
11. Fight the real disagreement, not a cartoon of the other side
12. Invite dissent inside each camp, not only across camps

Do not add a thirteenth rule. If a source does not support a rule, drop that rule and say so in `## Source note` rather than inventing a citation.

### Devil's advocate procedure

The Devil's advocate procedure section is labeled `Inference` as a whole. It tells the later prompt how to order moves for one voice that both argues for capitalism and uses the operating rules:

1. Restate the user's socialist claim.
2. State the strongest version of that claim.
3. Ask one clarifying question only when the claim is too vague to answer.
4. Argue the capitalist counter to that claim.
5. If you used a stereotype of socialists, correct it.
6. Do not offer a compromise middle as the goal of the turn.

### Quotes

At least six quotes, each with speaker, year or page date if the source has one, and URL. Use only quotes that appear in the sources listed above.

## Work

1. Fetch every URL in Files to inspect. If a URL fails, try the next source and record the failure in `## Source note`. Do not invent a quote for a failed URL.
2. Write the markdown file with the required headings.
3. Commit the principles markdown alone.

## Commands (exact)

```bash
test -f gpt_live_enlightened_disagreement/ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md && echo present
```

Expected output: `present`

```bash
python3 - <<'PY'
from pathlib import Path
p = Path("gpt_live_enlightened_disagreement/ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md")
text = p.read_text()
needed = [
    "# Enlightened disagreement principles",
    "## Source note",
    "## Mission",
    "## Non-goals",
    "## Operating rules",
    "## Devil's advocate procedure",
    "## Quotes",
    "Inference",
    "https://",
]
missing = [n for n in needed if n not in text]
print("missing:" + (",".join(missing) if missing else "none"))
print("bytes", p.stat().st_size)
PY
```

Expected output includes `missing:none` and `bytes` greater than `4000`.

## Pass / fail

| Check | Pass | Fail |
| --- | --- | --- |
| Path | File exists at `gpt_live_enlightened_disagreement/ENLIGHTENED_DISAGREEMENT_PRINCIPLES.md` | File in docs/ or another name |
| Headings | All seven required headings present in order | Extra top-level heading, or a required heading missing |
| Citations | Every operating rule has a `Source:` URL from Files to inspect | Unsourced rule, or a URL not in the inspect list |
| Inference | Devil's advocate procedure and any audio mapping marked `Inference` | Procedure presented as a Center handbook |
| Quotes | At least six quotes with speaker and URL | Invented quote |
| Scope | No Next.js or API files added | `package.json` or `app/` created in this step |

## Out of scope

- Prompt strings in TypeScript (Step 5)
- Tests (Step 3)
- UI copy beyond what this markdown already contains
