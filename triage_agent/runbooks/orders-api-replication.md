# Runbook: orders-api — Replication Lag

## Symptom
Users seeing stale order data, checkout failures on order confirmation.

## Cause
Database replication lag >5s between primary and replica, or replica down.

## Steps
1. Check replication status: `SELECT * FROM pg_stat_replication;`
2. Check replication lag: `SELECT pg_last_xact_replay_timestamp(), EXTRACT(EPOCH FROM NOW() - pg_last_xact_replay_timestamp()) AS lag_seconds FROM pg_stat_replication;`
3. Check replica connectivity: `pg_isready -h replica-host -p 5432`
4. If lag critical (>10s), read-only mode on replicas.

## Escalation
If replica down, failover to replica. Page #dba-oncall.