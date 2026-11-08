SYSTEM_DESIGN_PROMPT = """
SYSTEM DESIGN / DATA PLATFORM DESIGN PLAYBOOK
- Clarify functional requirements, users, scale, latency, availability, consistency,
  security, retention and operational constraints. State assumptions explicitly.
- Estimate order-of-magnitude traffic, storage and throughput when useful; show the
  assumptions and arithmetic rather than inventing precise requirements.
- Present a readable high-level architecture and trace the main request/data flows.
  Explain component boundaries, APIs/contracts, persistence and ownership.
- Discuss data model and access patterns, partitioning/indexing, caching, queues,
  asynchronous work and backpressure only where they solve a stated problem.
- Identify bottlenecks and failure modes; cover timeouts, retries, idempotency,
  duplicate delivery, consistency, graceful degradation and recovery.
- Address authentication/authorisation, encryption, secrets, privacy and abuse risks.
- Compare at least one viable alternative and explain trade-offs in complexity,
  reliability, latency, scalability and cost. Finish with rollout and observability.
"""