# Runbook: payments-api — Webhook Failures

## Symptom
Payment processor webhooks not being processed, orders not updated after payment.

## Cause
Webhook endpoint returning 5xx, or webhook signature verification failing.

## Steps
1. Check webhook endpoint logs: `grep "webhook" /var/log/payments-api.log | tail -n 100`
2. Verify webhook signature: compare HMAC signature in header with computed signature.
3. Check endpoint health: `curl -X POST -H "Content-Type: application/json" -d '{"event": "test"}' https://api.company.internal/payments/webhook`
4. Check for webhook retry limits being exhausted.

## Escalation
If signature mismatch, review token rotation policy. If endpoint down, restart payments-api service.