# scripts/  (primitive 4 · Action)
Your deterministic script + its JSON Schema 2020-12 contract, e.g.
  scripts/check_leave.py
  scripts/leave_schema.json
Rules: Decimal for money, errors as {"error","field","fix","retryable"} with exit code 2,
no stack traces, nothing the manifest does not declare (tools/gate.py checks).
The mock connector file is passed in as an argument (--data ../mock_connectors/…).
