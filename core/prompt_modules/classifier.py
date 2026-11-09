"""Fast, deterministic routing from interview questions to focused prompt modules."""

import re


_PATTERNS = {
    "data_engineering": re.compile(
        r"\b(data engineer(?:ing)?|etl|elt|data pipeline|ingestion|cdc|change data capture|"
        r"data warehouse|data lake|lakehouse|data modeling|data modelling|orchestrat(?:ion|e)|"
        r"batch processing|stream processing|data quality|incremental load|watermark|"
        r"bigquery|pub\s*sub|dataflow|cloud composer|redshift|snowflake|dbt)\b", re.I
    ),
    "sql": re.compile(
        r"\b(sql|query|cte|window function|join|group by|having|subquery|index(?:ing)?|"
        r"partition pruning|query plan|sql optimization|sql optimisation)\b", re.I
    ),
    "python": re.compile(
        r"\b(python|pandas|numpy|pyspark|function|class|decorator|generator|"
        r"list comprehension|asyncio|exception handling|time complexity|space complexity)\b", re.I
    ),
    "cloud_architecture": re.compile(
        r"\b(gcp|google cloud|aws|azure|cloud architecture|cloud services|iam|"
        r"pub\s*sub|dataflow|bigquery|cloud storage|dataproc|cloud composer|"
        r"serverless|kubernetes|terraform)\b", re.I
    ),
    "spark": re.compile(
        r"\b(apache spark|spark|pyspark|shuffle|executor|driver|spark sql|"
        r"partition(?:ing)?|broadcast join|watermark|structured streaming)\b", re.I
    ),
    "system_design": re.compile(
        r"\b(system design|design an? (?:end.to.end )?(?:system|platform|architecture|pipeline)|"
        r"high.level design|scalability|distributed system|microservices|event.driven|"
        r"availability|fault tolerance|rpo|rto)\b", re.I
    ),
}

_TECHNICAL_CUES = re.compile(
    r"\b(technical|architecture|pipeline|database|programming|code|debug|"
    r"optimi[sz]e|distributed|schema|api|cloud|spark|sql|python|etl|elt)\b", re.I
)


def classify_question(question):
    """Return relevant technical playbook names, preserving a stable order."""
    text = question or ""
    matches = [name for name, pattern in _PATTERNS.items() if pattern.search(text)]

    if not matches and _TECHNICAL_CUES.search(text):
        matches.append("data_engineering")

    # Keep the prompt focused while allowing combined questions to match multiple areas.
    return matches[:4]
