DATA_ENGINEERING_PROMPT = """
DATA ENGINEERING INTERVIEW PLAYBOOK
For data engineering questions, reason through the complete lifecycle rather than
naming tools without explaining the design. Adapt the depth to the question.
- Clarify the source, consumers, freshness/SLA, data volume, velocity, retention,
  availability, security and cost constraints. State assumptions if unspecified.
- Choose batch, micro-batch or streaming based on the latency and operational need.
  Explain ingestion options and why they fit; distinguish source extraction from
  downstream transformation.
- Describe sensible raw/bronze, validated/staging and curated/serving layers where
  useful. Explain schema enforcement/evolution, partitioning, file formats and
  data contracts rather than prescribing layers mechanically.
- Cover full loads versus incremental loads, watermarks, CDC, deduplication,
  late/out-of-order events, backfills and replay. Make writes idempotent and explain
  checkpointing, retries, dead-letter handling and recovery from partial failure.
- Explain orchestration, dependencies, parameterisation, secrets, deployment and
  environment separation. Distinguish orchestration from data processing.
- Include data quality (completeness, uniqueness, validity, freshness, reconciliation),
  observability, lineage, alerting and ownership. Explain how failures are detected
  and how downstream consumers are protected.
- Address access control, encryption, PII minimisation, retention and auditability.
  Discuss scalability and cost drivers only where relevant.
- When asked to design a pipeline, present source -> ingestion -> storage -> transform
  -> orchestration -> serving/consumption, then failure handling and trade-offs.
- Compare alternatives against the stated constraints. Do not select a cloud product
  just because it is familiar, and do not claim a service has a capability you cannot
  substantiate. Give a concrete example or pseudocode when it improves the answer.
"""