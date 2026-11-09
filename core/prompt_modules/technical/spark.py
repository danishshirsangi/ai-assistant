SPARK_PROMPT = """
APACHE SPARK / DISTRIBUTED PROCESSING PLAYBOOK
- Explain the data shape, scale and desired output before choosing an implementation.
  Distinguish driver work from executor/partition work.
- Reason about transformations/actions, lazy evaluation, DAG/stages, partitions,
  shuffles and wide versus narrow transformations when relevant.
- Diagnose performance using the physical plan, input sizes, skew, shuffle volume,
  spill, task duration and executor memory/CPU. Avoid arbitrary repartitioning.
- Discuss partition sizing, predicate and column pruning, broadcast joins, caching,
  file format and small-file handling only when justified by the workload.
- Address schema handling, nulls, duplicates, late data and correctness of aggregations.
  For streaming, include event time, watermarks, state, checkpoints and delivery
  semantics supported by the chosen sink/source.
- Provide PySpark or Spark SQL code when requested, and distinguish API behaviour
  across Spark versions if version-specific details matter.
"""