# Runbook: notifications-service — Queue Backlog

## Symptom
Email/SMS notification delays >5min, queue depth >10000 messages.

## Cause
下游 provider (SendGrid/AWS SES) slow or failing, worker processes down.

## Steps
1. Check queue depth: `rabbitmqadmin get -q /notifications/queue -d 0`
2. Check worker health: `curl http://localhost:5672/health`
3. Check provider API status (SendGrid status page, AWS SES health).
4. Review failed message logs for provider error patterns.

## Escalation
If provider down, enable fallback queue. If workers down, restart worker pods.