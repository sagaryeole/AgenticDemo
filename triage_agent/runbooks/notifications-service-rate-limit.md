# Runbook: notifications-service — Provider Rate Limits

## Symptom
Email/SMS sending failures, "Rate limit exceeded" from provider.

## Cause
Exceeding SendGrid/Twilio rate limits, or burst traffic overwhelming provider.

## Steps
1. Check provider usage: SendGrid API `GET /v3/counts/requests`, Twilio `GET /2010-04-01/Accounts/~/Usage/Email`
2. Review sending throttling config: `cat /etc/notification-providers.yml`
3. Implement exponential backoff for failed sends.
4. Enable provider's burst allowance if available.

## Escalation
If hitting hard limits, page #prodman-oncall to adjust provider throttling settings.