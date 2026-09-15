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

- The dispatcher starts the session in this repository and supplies one issue;
  it does not create the worktree.
- Before editing, create a unique task branch and dedicated Git worktree under
  the repository's sibling `.worktrees` directory. Do all edits, tests, and
  commits there; never modify the shared checkout or another task's worktree.
- Stay within the issue's acceptance criteria and leave the committed branch
  ready for review. Do not merge PRs, close issues, or change Project status.

## Validation

Before committing, run the test suite, compile the package, check `--help`, and
regenerate the CLI documentation. Keep commits focused and explain any
version-sensitive protocol assumptions in the code or documentation.
