# Runbook: api-gateway — Certificate Renewal

## Symptom
Certificate expiration warning in 30 days, monitoring alert "cert-expiry-soon".

## Cause
Automated certificate rotation not completing, or ACME challenge failures.

## Steps
1. Check certbot status: `certbot certificates`
2. Check renewal logs: `cat /var/log/letsencrypt/letsencrypt.log | grep -i "renewal"`
3. Test certificate rotation: `openssl s_client -connect api.company.internal:443 -servername api.company.internal`
4. Verify CDN (CloudFront/Cloudflare) cache TTL for SSL cert.

## Escalation
If auto-renewal failing, enable manual renewal and monitor certificate propagation for 24h.