# Runbook: auth-service — High Authentication Latency

## Symptom
Login taking >3s, MFA verification delays.

## Cause
MFA provider (TOTP validation, SMS gateway) slow, or auth token validation expensive.

## Steps
1. Profile auth service: `perf record -g ./app; perf report`
2. Check MFA provider latency: `curl -X POST /auth/mfa/verify -d '{"code": "123456"}'`
3. Check token validation cache: `grep "token:cache-hit" /var/log/auth-service.log`
4. Review database query for user lookup in auth flow.

## Escalation
If MFA provider issue, enable backup MFA method. If DB slow, check auth-service DB connection pool.