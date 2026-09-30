# Runbook: payments-api — PCI Compliance Alert

## Symptom
Compliance scan failing, "Card data not encrypted", or tokenization failures.

## Cause
Payment card data being stored in plaintext, or PCI-scoped services not isolated.

## Steps
1. Audit database for card numbers: `SELECT * FROM order_details WHERE card_number IS NOT NULL;` (should only show tokens)
2. Verify encryption at rest: check KMS keys for payment table.
3. Check tokenization service logs for failed tokenization.
4. Review network segmentation (PCI scope).

## Escalation
Page #security-oncall immediately. Full PCI remediation may require re-architecture.