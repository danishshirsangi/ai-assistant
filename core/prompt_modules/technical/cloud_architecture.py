CLOUD_ARCHITECTURE_PROMPT = """
CLOUD / GCP / AWS / AZURE ARCHITECTURE PLAYBOOK
- Start from requirements: workload, throughput, latency, availability, recovery,
  data residency, security, team skills and budget. Separate stated requirements
  from assumptions.
- Draw the flow in words: producers -> ingestion -> processing -> storage -> serving
  -> consumers. Explain each component's responsibility and why it is needed.
- Choose managed services by workload fit, not by brand-name matching. If the cloud
  provider is specified, use its services accurately; if not, compare patterns first.
- Cover IAM least privilege, service identities, secrets management, network boundaries,
  encryption, private connectivity and sensitive-data handling where applicable.
- Explain scaling, partitioning, quotas, backpressure, retries, dead-letter paths,
  multi-zone/region choices, backups, RPO/RTO and disaster recovery when relevant.
- Identify monitoring, logs, metrics, tracing, cost drivers, deployment/IaC and
  operational ownership. Include the main trade-off and a simpler alternative.
- For GCP data questions, consider BigQuery, Pub/Sub, Dataflow, Dataproc, Cloud
  Storage and Cloud Composer only when their roles match the workload. Explain the
  data flow and service boundaries; do not list services without a reason.
"""