# Runbook: auth-service — 503 Service Unavailable

## Symptom
HTTP 503 errors on POST /auth/login, "Service temporarily unavailable".

## Cause
Authentication service dependency (Keycloak/Okta) unreachable or overloaded.

## Steps
1. Check dependency health: `curl -v https://auth.company.internal/health`
2. Check auth service logs for upstream connection errors.
3. If dependency down, check network connectivity and firewall rules.
4. If dependency overloaded, check their status page or contact vendor.

## Escalation
If dependency issue confirmed, page SRE team. If vendor issue, create incident with auth-provider support.