# Runbook: orders-api — High Latency

## Symptom
Response times >2s for GET /orders, users reporting slow page loads.

## Cause
Database index on `orders.user_id` missing or fragmented, causing full table scans.

## Steps
1. Check index health: `EXPLAIN (ANALYZE, FORMAT JSON) SELECT * FROM orders WHERE user_id = ?;`
2. Look for Sequential Scan instead of Index Scan.
3. If missing index, create: `CREATE INDEX idx_orders_user_id ON orders(user_id);`
4. If fragmented, rebuild: `REINDEX TABLE orders;`

## Escalation
If unresolved in 15 min, page #backend-oncall.