# Payments

## Stripe Integration

We use Stripe Checkout for one-off purchases. Webhooks land at `/api/stripe/webhook`.
Test cards work in sandbox mode. Live keys live in `Security/project.json` under `stripe.live`.

## Refund Policy

Customer refunds processed within 14 days, no questions asked. Use Stripe dashboard.

## PCI Compliance

Stripe Checkout keeps us in scope SAQ-A. We never touch raw card data.
