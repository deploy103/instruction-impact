# Contributing

Bug reports, scoped improvements, and pointers to related tools are welcome.

For bugs, include Python/Git versions, the command, expected and actual output, and a minimal repository or test fixture. Do not include private instructions or credentials. Report security-sensitive issues using GitHub's private vulnerability reporting if available; otherwise contact the maintainer before opening a public issue with sensitive details.

Install with `python -m pip install -e .` and run `python -m unittest discover -s tests -v`. Tests must use temporary repositories, not alter the contributor's working tree. A regression test should distinguish the intended scope from a plausible wrong scope (for example, `api/` versus `apiary/`).

Keep runtime dependencies at zero. Never execute commands found in instruction files. Changes to scope semantics or JSON fields must update the README and tests; incompatible JSON changes require a schema version bump. Do not expand agent-specific behavior without documenting what is and is not modeled.
