# Results

The full study finished on 21 October 2026. Run `01a160bd-2ce7-77e9-80e1-1990174d7213` completed five discussion rounds and the seven voter ranking, which is 72 model calls, and the process exited 0. This run started from the brief again. It does not reuse the earlier smoke round.

The model was `gpt-6-sol` with reasoning effort `medium`. The calls used 87,112 input tokens and 38,676 output tokens. At $2.00 per million input tokens and $10.00 per million output tokens, the cost is $0.560984. The one round smoke run had projected $0.586178 for these 72 calls. Actual spend stayed under that projection, and it stayed under the $2.00 stop.

`study.json` is a `StudyResult`. The stored token totals equal the sum of every round turn and every ballot. Reasoning tokens stay inside the output total, and they are not added again.

## Ranking

Each voter scored three criteria from 1 to 5. The criteria are whether a specialist would already expect the study, whether a small team can run it, and whether the design answers the question. A ballot total is the sum of those three scores, so it runs from 3 to 15. The rank is the mean of the seven ballot totals. A tie would go to the higher mean feasibility score, and then to the lower round number. No tie needed a tie break.

| Rank | Round | Mean total | Sum of seven totals |
| --- | --- | --- | --- |
| 1 | 3 | 14.429 | 101 |
| 2 | 5 | 14.143 | 99 |
| 3 | 1 | 12.714 | 89 |
| 4 | 4 | 12.000 | 84 |
| 5 | 2 | 9.857 | 69 |

## Top three proposals

### Round 3, first place

**Title.** Does the Identity of a Prior Replier Change the Effect of Direct Address?

**Question.** In a four-person online-group thread, does direct address from a dissenter change a reader’s stated opinion differently when that dissenter, rather than a supporter, is identified as the person who previously replied to the reader?

**Proposed design.** Run a preregistered 2×2 online experiment. After a private initial opinion rating, show participants a four-member thread with two supporters of their initial position and one dissenter. Randomize whether the dissenter’s otherwise identical comment opens by addressing the participant or the group. Independently randomize a single history note stating that one earlier reply to the participant came from either the dissenter or a designated supporter. Show no reply map, other links, or earlier reply text. Collect the private opinion rating again before manipulation checks.

**Votes.** Every voter gave 5 for feasibility and 5 for whether the design answers the question. The communications researcher, the sociologist, and the political scientist gave 5 for surprise, and the other four voters gave 4. Totals were 15, 15, 15, 14, 14, 14, and 14.

| Voter | Surprise | Feasible | Method fits | Total |
| --- | --- | --- | --- | --- |
| Social psychologist | 4 | 5 | 5 | 14 |
| Computer scientist | 4 | 5 | 5 | 14 |
| Communications researcher | 5 | 5 | 5 | 15 |
| Sociologist | 5 | 5 | 5 | 15 |
| Political scientist | 5 | 5 | 5 | 15 |
| Methodologist | 4 | 5 | 5 | 14 |
| Critic | 4 | 5 | 5 | 14 |

### Round 5, second place

**Title.** Do Reply Links Between Commenters Change Stated Civic Opinions?

**Question.** When people read the same five comments in a small online group, does changing who appears to reply to whom affect their stated opinion?

**Proposed design.** Run a preregistered online experiment with approximately 240 adults. Measure initial opinion, then randomly assign participants to one of two displays of five comments in the same order: favorable, dissenting, favorable, dissenting, favorable. Keep text and author labels fixed. In one display, the favorable comments at positions three and five reply to earlier favorable comments; in the other, they reply to the dissenters at positions two and four. Measure opinion immediately afterward, before asking any other questions about the discussion. Briefly pretest whether both displays are understandable.

**Votes.** The computer scientist gave 5, 5, and 5, for a total of 15. Each of the other six voters gave 4, 5, and 5, for a total of 14. The only split is the surprise score.

| Voter | Surprise | Feasible | Method fits | Total |
| --- | --- | --- | --- | --- |
| Social psychologist | 4 | 5 | 5 | 14 |
| Computer scientist | 5 | 5 | 5 | 15 |
| Communications researcher | 4 | 5 | 5 | 14 |
| Sociologist | 4 | 5 | 5 | 14 |
| Political scientist | 4 | 5 | 5 | 14 |
| Methodologist | 4 | 5 | 5 | 14 |
| Critic | 4 | 5 | 5 | 14 |

### Round 1, third place

**Title.** Does the Last Comment Change a Stated Opinion?

**Question.** Among readers whose initial opinion differs clearly from a group member’s stated position, does placing that member’s comment last rather than first change the reader’s next stated opinion? Does it matter whether that member will see the response?

**Proposed design.** Run a small preregistered experiment with one reader and three commenters per group. The reader records an initial opinion on a 0–100 scale. Each commenter independently records a position on that scale and writes a self-contained comment that explicitly states and supports that position. Before assigning order, check that each comment clearly expresses its recorded position. A group is eligible for the primary analysis only if at least one commenter’s position is at least 20 points from the reader’s initial opinion. Select the eligible commenter with the largest difference as the focal commenter, breaking ties by a prespecified rule. Then randomize the six orders of the three named comments. After reading, reveal an independently randomized assignment: the reader’s next opinion will remain private or be shown to the focal commenter. Collect that opinion immediately.

**Votes.** Five voters gave 4, 4, and 5, for a total of 13. The sociologist gave 3 for surprise, 4 for feasibility, and 5 for fit, for a total of 12. The critic gave 4 for surprise, 3 for feasibility, and 5 for fit, for a total of 12. Every voter gave 5 for whether the design answers the question.

| Voter | Surprise | Feasible | Method fits | Total |
| --- | --- | --- | --- | --- |
| Social psychologist | 4 | 4 | 5 | 13 |
| Computer scientist | 4 | 4 | 5 | 13 |
| Communications researcher | 4 | 4 | 5 | 13 |
| Sociologist | 3 | 4 | 5 | 12 |
| Political scientist | 4 | 4 | 5 | 13 |
| Methodologist | 4 | 4 | 5 | 13 |
| Critic | 4 | 3 | 5 | 12 |

## How the five ideas changed

The first two rounds kept the question on the order of comments. Later rounds held the comment text fixed and changed one social cue. Round 3 changed who had replied to the reader before. Round 4 changed whether a scripted peer addressed the reader after a short introduction. Round 5 changed which comments appeared to reply to which other comments.

Round 2, "Does a last-placed dissent change opinion immediately or a week later?", finished last. Every voter scored it 9 or 10. Round 4, "Introductory Contact and the Effect of Being Addressed", finished fourth with a mean total of 12.000.

## LangSmith threads

The project is `social-science-idea-generation`. Each round has its own thread, and the vote has a sixth thread.

- Round 1, `01a160bd-2f28-7605-abd5-8e259920f1d1`
- Round 2, `01a160be-e480-739b-9183-492abc644712`
- Round 3, `01a160c1-124f-75c7-bd94-cdda69e322be`
- Round 4, `01a160c2-ec23-7627-bada-01bba3f06de6`
- Round 5, `01a160c4-9e10-701d-b1cf-a9e8d617ea34`
- Vote, `01a160c6-67df-7710-bd3d-0f9feb426ee7`

## Stored files

The runner wrote `study.json` and a shorter `RESULTS.md` under `outputs/runs/01a160bd-2ce7-77e9-80e1-1990174d7213/`. Those local files are not committed. The same two objects are on S3, and the uploaded bytes match the local files.

- `s3://mind-technology-lab-experiments/experiments/social_science_idea_generation_2026_10_21/runs/01a160bd-2ce7-77e9-80e1-1990174d7213/study.json`
- `s3://mind-technology-lab-experiments/experiments/social_science_idea_generation_2026_10_21/runs/01a160bd-2ce7-77e9-80e1-1990174d7213/RESULTS.md`
