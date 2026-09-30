# Runbook: orders-api — Memory Leak

## Symptom
Node.js process memory growing unbounded, OOM kills after hours of operation.

## Cause
Event listeners not removed on component unmount, or unclosed file handles.

## Steps
1. Check heap dump: `node --heap --heap-check` and analyze with Chrome DevTools heap snapshot.
2. Look for growing object graphs (closures holding references).
3. Check for file descriptors: `lsof -p <pid> | grep -i open`
4. Restart service and monitor for recurrence.

## Escalation
If leak persists after restart and memory persists, page #backend-oncall with heap dump.