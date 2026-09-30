# Runbook: api-gateway — High CPU Usage

## Symptom
API response times degraded, gateway pods at 90%+ CPU.

## Cause
Malicious traffic (DDoS), inefficient routing logic, or resource exhaustion.

## Steps
1. Identify hot routes: analyze access logs for highest request counts per endpoint.
2. Check for bot traffic: `grep -i "user-agent.*bot" access.log | wc -l`
3. Review rate limiting rules and enforcement logs.
4. Check for routing loops or infinite redirect chains.

## Escalation
If DDoS, enable WAF/DDoS protection. If legitimate traffic, scale gateway horizontally.