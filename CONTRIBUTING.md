# Contributing

- **A command, limit or status code changed:** open a pull request with the CLI version you checked (`eos --version`).
- **A field name in the logs or key list differs from what the tools assume:** fix the default in `usage_report.py` or `watch_budget.py` and update the sample and the tests.
- **New code:** keep it dependency-free, add tests that run offline against a fake server, and never use a real key.
- Describe behavior, not outcomes. No pricing, no compliance claims, no statistics you cannot source.
- Never include real keys, tokens or customer data. Use obviously fake values.
