# Runbook: orders-api — Disk Space Critical

## Symptom
500 errors on POST /orders/files, "Unable to save order data".

## Cause
Disk space on order storage volume <10%, unable to write order records.

## Steps
1. Check disk usage: `df -h /orders-data`
2. Identify large files: `du -h --max-depth=2 /orders-data | sort -hr | head -n 20`
3. Check for orphaned order files from failed uploads.
4. Clear old completed orders: `rm /orders-data/archive-2023-*`

## Escalation
If disk can't be freed, page #infra-oncall for volume expansion.