# Runbook: payments-api — 500 Internal Server Error

## Symptom
HTTP 500 errors on POST /payments, "Internal server error".

## Cause
Payment processor API returning error responses, or transaction validation failing.

## Steps
1. Check payment processor status page.
2. Review application logs for payment processor SDK errors.
3. Check for invalid card tokens or expired payment methods.
4. Verify webhook endpoint is receiving processor callbacks.

## Escalation
If payment processor is down, page #payments-oncall and notify customers.