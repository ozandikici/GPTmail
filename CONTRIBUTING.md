# Contributing to GPTmail

Contributions are welcome, particularly security hardening, broader IMAP interoperability, additional OAuth providers, accessibility and tests.

1. Fork the repository and create a feature branch.
2. Set up Python 3.11+; install `requirements.txt`, `pytest` and `httpx`.
3. Run `python -m pytest -q` and add tests for fixes.
4. Never include real email, credentials, copied proprietary messages or API tokens in test fixtures or PR descriptions.
5. Open a concise pull request describing changed capabilities and their permission/security impact.

Please discuss backward-incompatible MCP protocol or authorization changes in an issue before implementing them.
