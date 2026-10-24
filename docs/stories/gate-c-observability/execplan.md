# Exec Plan

## Goal

Provide production-safe correlation, structured runtime logs, and a protected
Prometheus scrape surface for Gate C without changing product audit semantics.

## Scope

In scope:

- Request ID validation and propagation.
- JSON stdout logging for API and worker.
- Bounded HTTP, provider, rate-limit, and worker-job metrics.
- Secure-by-default metrics configuration and operator documentation.
- Unit, integration, regression, container-build, and runtime scrape proof.

Out of scope:

- Hosted telemetry services and dashboard provisioning.
- Distributed tracing backend integration.
- Cross-process Prometheus aggregation.
- Audit-event retention changes.

## Risk Classification

Risk flags:

- Audit/security.
- External systems.
- Public contracts.
- Existing behavior.
- Weak proof.
- Cross-platform deployment.

Hard gates:

- Audit/security.

## Work Phases

1. Confirm the accepted telemetry and redaction contract.
2. Record the story and architecture decision.
3. Implement correlation, structured logging, and bounded metrics.
4. Add focused security and contract tests.
5. Run backend, frontend, build, and live scrape verification.
6. Update operator docs, story proof, AI logs, and Harness trace.

## Stop Conditions

Pause for human confirmation if:

- The implementation would need to record document or chat content.
- The metrics endpoint cannot be protected at the application boundary.
- Audit persistence semantics would need to change.
- Validation requirements need to be weakened.

