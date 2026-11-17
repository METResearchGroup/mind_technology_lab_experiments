# AWS cost tracker automation

Runs every 3 hours. It watches the lab AWS account for cost anomalies, trips a circuit breaker on runaway Athena jobs, and reports only when something needs attention.

## Schedule

`0 */3 * * *` in America/Chicago (every 3 hours).

## Prompt

Check the lab AWS account (account 517478598677, mostly us-east-2) for cost anomalies. Everything here is read-only except the circuit-breaker actions in step 6, which are the only changes this automation may ever make.

Access: use Python boto3 with the `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_SECRET_ACCESS_KEY` environment variables (IAM user `mark`). Cost Explorer is in us-east-1. Do not use any other account's keys.

1. Pull month-to-date unblended cost from Cost Explorer.
   - Get it by day and by service, plus usage types for any service that jumped.
   - Also pull the previous month's total and the Cost Explorer forecast for the current month.
   - Cost Explorer lags by several hours and its daily buckets are in UTC. Treat the current UTC day as incomplete, and say so when it matters.
   - For Athena, also sum today's data scanned from the query history in the us-east-2 workgroups, since that has no lag.
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
   - Never start or retry any job or Step Functions execution.
6. Circuit breaker. Trip it when either of these is true:
   - Athena data scanned in one complete or partial day exceeds 1 TB.
   - A day's cost tied to the backfill merge or maintenance jobs exceeds $25.

   When it trips, do the following in this order, and only on these resources in us-east-2:
   1. Stop any RUNNING executions of the `bluesky_backfill_merge` and `bluesky_backfill_maintenance` state machines.
   2. Cancel any RUNNING or QUEUED Athena queries in the `bluesky_backfill` and `bluesky_raw_maintenance` workgroups.
   3. Set the EventBridge Scheduler schedules `bluesky_backfill_merge` and `bluesky_backfill_optimize` (group `default`) to DISABLED. Leave everything else in each schedule unchanged.
   4. Record the trip in state.json, including the time, the trigger, and exactly what was stopped or disabled.

   Never touch anything else. That includes:
   - the Jetstream `bluesky_raw_*` schedules and the `bluesky_raw_maintenance` state machine;
   - Cloudflare Workers;
   - S3, DynamoDB, Secrets Manager, GuardDuty, Config, and CloudWatch;
   - IAM users, roles, or keys.

   Never delete anything. Never re-enable a schedule yourself. While state.json shows the breaker as tripped, do not trip it again or repeat the report.

   The breaker resets when Mark re-enables the schedules himself, or runs `terraform apply` in `terraform/bluesky_backfill_app`, which turns them back on. When you see the schedules enabled again after a trip, mark the breaker as reset in state.json and stay quiet.

   If a stop or disable call is denied, still send the alert. Say which action was denied, and say that the IAM policy `CostCircuitBreaker` on user `mark` may be missing.
7. Report only when there is something new.
   - A message covers a breaker trip, a new anomaly, a threshold crossing, or an anomaly that got materially worse since the last report.
   - A breaker-trip message lists exactly what was stopped or disabled, and how to undo it: re-enable the two schedules in the console, or run `terraform apply` in `terraform/bluesky_backfill_app`.
   - It should say what happened, how much it cost, the likely cause, and a suggested next step.
   - Keep it to a few sentences, with times in CT.
   - Never print credentials or secrets.

Send the result to Mark in this Grok Bot chat. When nothing is anomalous, the breaker didn't trip, and no threshold has newly been crossed, send nothing.

## IAM permissions for the breaker

The breaker needs this inline policy, `CostCircuitBreaker`, attached to IAM user `mark`. `iam:PassRole` on `bluesky_backfill_scheduler`, which `UpdateSchedule` requires, is already granted by `TerraformManageBlueskyBackfillRoles`.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "StopBackfillExecutions",
      "Effect": "Allow",
      "Action": ["states:StopExecution", "states:DescribeExecution"],
      "Resource": [
        "arn:aws:states:us-east-2:517478598677:execution:bluesky_backfill_merge:*",
        "arn:aws:states:us-east-2:517478598677:execution:bluesky_backfill_maintenance:*"
      ]
    },
    {
      "Sid": "ListBackfillExecutions",
      "Effect": "Allow",
      "Action": "states:ListExecutions",
      "Resource": [
        "arn:aws:states:us-east-2:517478598677:stateMachine:bluesky_backfill_merge",
        "arn:aws:states:us-east-2:517478598677:stateMachine:bluesky_backfill_maintenance"
      ]
    },
    {
      "Sid": "StopAthenaQueries",
      "Effect": "Allow",
      "Action": ["athena:StopQueryExecution", "athena:ListQueryExecutions", "athena:GetQueryExecution", "athena:BatchGetQueryExecution"],
      "Resource": [
        "arn:aws:athena:us-east-2:517478598677:workgroup/bluesky_backfill",
        "arn:aws:athena:us-east-2:517478598677:workgroup/bluesky_raw_maintenance"
      ]
    },
    {
      "Sid": "PauseBackfillSchedules",
      "Effect": "Allow",
      "Action": ["scheduler:GetSchedule", "scheduler:UpdateSchedule"],
      "Resource": [
        "arn:aws:scheduler:us-east-2:517478598677:schedule/default/bluesky_backfill_merge",
        "arn:aws:scheduler:us-east-2:517478598677:schedule/default/bluesky_backfill_optimize"
      ]
    }
  ]
}
```

## Terraform drift

Disabling the two schedules drifts from `terraform/bluesky_backfill_app`, which leaves `state` unset (the default is ENABLED). This is intentional: the next apply resets the breaker. Stopping executions and queries does not drift.
