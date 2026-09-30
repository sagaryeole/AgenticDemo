# Runbook: orders-api — Order Status Synchronization Lag

## Symptom
Customers seeing "processing" for hours after payment confirmation, inventory not reserved.

## Cause
Event-driven order status updates failing or delayed, or message broker backlog.

## Steps
1. Check Kafka/RabbitMQ order-events queue depth: `kafka-topics.sh --describe --topic order-events`
2. Check consumer lag: `kafka-consumer-groups.sh --describe --group order-consumer`
3. Review order state machine logs for stuck transitions.
4. Check for duplicate order creation (race condition).

## Escalation
If consumer down, restart consumer. If duplicate orders, check idempotency key implementation.