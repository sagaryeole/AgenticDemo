# Runbook: api-gateway — 429 Too Many Requests

## Symptom
HTTP 429 errors, "Rate limit exceeded".

## Cause
Client hitting rate limit thresholds, or internal rate limiter misconfigured.

## Steps
1. Check rate limit headers: `curl -i https://api.company.internal/ | grep "X-RateLimit"`
2. Verify rate limit config: `cat /etc/rate-limits.yml`
3. Check for legitimate traffic patterns (bot traffic, scraping).
4. Review rate limit per endpoint and user tier.

## Escalation
If legitimate users affected, temporarily increase limits. If bot traffic, update WAF rules.