# Contributor instructions

This repository contains a small Python command-line package. Keep the code
modular, typed, and easy to extend as additional commands are introduced.

## Engineering rules

- Use Python 3.11+ and keep runtime dependencies narrowly scoped.
- Never embed credentials, API keys, or machine-specific secrets in source,
  tests, fixtures, generated documentation, or examples.
- Preserve caller-supplied values and surface protocol errors; do not silently
  substitute models, transports, or configuration.
- Keep transport/protocol code separate from command parsing and presentation.
- Add focused tests for new behavior and avoid unrelated refactors.
- Keep generated CLI documentation synchronized with typed signatures and
  docstrings.

## Task workflow

- Every task must use a unique task branch and dedicated Git worktree under the
  repository's sibling `.worktrees` directory, regardless of how the task was
  started. Create it before editing; never modify the shared checkout or
  another task's worktree.
- Stay within the issue's acceptance criteria and leave the committed branch
  ready for review. Do not merge, close the ticket, change workflow state, or
  start follow-on work.

## Validation

Reuse compilation caches safely, prefer focused development checks and run
lightweight checks independently of heavy validation where possible. Incorporate
review fixes before final validation, then run all required acceptance checks
against the exact frozen revision. Avoid redundant full-suite runs unless changes
or failures justify them. Never share writable build targets between concurrent
builds or treat cached artifacts as acceptance evidence.

Final acceptance includes the test suite, package compilation, `--help` and
generated CLI documentation checks. Keep commits focused and explain any
version-sensitive protocol assumptions in the code or documentation.
