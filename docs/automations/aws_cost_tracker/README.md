# AWS cost tracker automation

Runs every 3 hours. It watches the lab AWS account for cost anomalies and reports only when something needs attention.

## Schedule

`0 */3 * * *` in America/Chicago (every 3 hours).

## Prompt

Check the lab AWS account (account 517478598677, mostly us-east-2) for cost anomalies. Use read-only access only, and never change any AWS resource.

1. Pull month-to-date unblended cost from Cost Explorer.
   - Get it by day and by service, plus usage types for any service that jumped.
   - Also pull the previous month's total and the Cost Explorer forecast for the current month.
   - Cost Explorer lags by several hours and its daily buckets are in UTC. Treat the current UTC day as incomplete, and say so when it matters.
2. Compare against the baseline.
   - On quiet days the account has historically run about $3/day, mostly S3, Secrets Manager, CloudWatch, GuardDuty, and ECR.
   - Athena is billed at $5 per TB scanned. The `bluesky_backfill` workgroup has a per-query cap of 300 GiB. The weekly Bluesky backfill merge runs Sunday at about 3 AM CT and should now cost cents, not tens of dollars.
3. Flag an anomaly if any of the following is true:
   - A complete day costs more than 2x the trailing 7-day median of complete days and more than $5 above it.
   - Any one service's daily cost is more than 3x its trailing 7-day median and more than $3 above it.
   - A service appears that wasn't billed in the previous 30 days and costs more than $1.
   - Athena data scanned in one day exceeds 1 TB.
   - Bedrock or other model-inference charges appear unexpectedly.
4. Budget threshold. The initial limit is $200 per calendar month.
   - Alert when month-to-date spend crosses 80% ($160).
   - Alert again when it crosses 100% ($200).
   - Alert when the month's forecast exceeds $200 and month-to-date spend has not crossed it yet.
   - Send each of these alerts once per month. Keep track of what has already been sent in `/workspace/aws_cost_tracker/state.json`, so the same crossing isn't reported every 3 hours.
5. Find the cause of each anomaly.
   - Name the service, usage type, day, and dollar amount.
   - For Athena, look at that day's query executions in the relevant workgroups and summarize which queries or state machine produced the scan.
   - Do not start, stop, or retry any job or Step Functions execution.
6. Report only when there is something new.
   - A message covers a new anomaly, a threshold crossing, or an anomaly that got materially worse since the last report.
   - It should say what happened, how much it cost, the likely cause, and a suggested next step.
   - Keep it to a few sentences, with times in CT.
   - Never print credentials or secrets.

Send the result to Mark in this Grok Bot chat. When nothing is anomalous and no threshold has newly been crossed, send nothing.
