# Runbook: auth-service — Certificate Expiry

## Symptom
SSL/TLS handshake failures, browsers showing "connection not secure".

## Cause
SSL certificate expiring or revoked.

## Steps
1. Check certificate expiry: `openssl s_client -connect auth.company.internal:443 -servername auth.company.internal | openssl x509 -noout -dates`
2. Check certificate chain: `openssl s_client -connect auth.company.internal:443 | grep -A5 "Certificate chain"`
3. Check revocation status: `openssl x509v3 -checkend 0 < cert.pem`
4. Generate new cert and restart service (if auto-renewal enabled).

## Escalation
Page #security-oncall immediately. Certificate renewal may take 30-60 min to propagate.