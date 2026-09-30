# Runbook: auth-service — Token Expiry Spike

## Symptom
401 Unauthorized errors spiking, users logged out unexpectedly.

## Cause
JWT tokens expiring faster than expected, or token refresh endpoint failing.

## Steps
1. Check token TTL: `grep "iat.*exp" /var/log/auth.tokens | tail -n 100`
2. Verify token refresh endpoint: `curl -X POST /auth/refresh -H "Authorization: Bearer <token>"`
3. Check for clock skew between services (`date` on all servers).
4. Review token rotation policy and refresh window configuration.

## Escalation
If clock skew found, sync NTP. If config issue, update token settings and redeploy.