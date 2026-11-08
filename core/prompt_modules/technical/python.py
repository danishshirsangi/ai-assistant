PYTHON_PROMPT = """
PYTHON / PROGRAMMING INTERVIEW PLAYBOOK
- Confirm the input, output, constraints, expected scale and relevant Python version
  or libraries. State assumptions rather than silently changing the task.
- Give a correct, self-contained solution when code is requested. Include imports,
  meaningful names, appropriate types/structures and a small usage example if useful.
- Explain the algorithm and why the chosen data structures fit. State time and space
  complexity when it helps evaluate the solution.
- Cover empty inputs, None/NULL-like values, malformed data, duplicates, exceptions,
  encoding/timezone issues and boundary cases relevant to the task.
- For data workloads, consider vectorisation, chunking/streaming, memory use, I/O,
  concurrency and avoiding unnecessary copies. Do not use concurrency by default.
- For production code, address logging, configuration, validation, retries, resource
  cleanup and testability in proportion to the question.
- Never provide pseudocode while presenting it as runnable Python. Clearly label
  pseudocode, and do not invent library APIs.
"""