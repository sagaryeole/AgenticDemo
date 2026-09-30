# Runbook: payments-api — Database Timeout

## Symptom
Errors: "DB timeout after 30s", "Pool exhausted"

## Cause
Connection pool exhausted under load, or long-running queries holding connections.

## Steps
1. Check active connections: `SELECT count(*) FROM pg_stat_activity;`
2. Look for queries running >10s.
3. If pool is maxed but queries are fast, increase pool size in payments-api config.
4. If queries are slow, check for missing indexes on the orders table.

## Escalation
If unresolved in 15 min, page #payments-oncall.