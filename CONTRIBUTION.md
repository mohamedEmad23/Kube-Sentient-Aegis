# Contribution Guide

## Contribution Policy
All changes must be submitted through Pull Requests (PRs).

- Direct pushes to protected branches should be blocked in repository settings.
- CODEOWNERS review is required before merge.
- Keep PRs focused and small enough for clear review.

## Workflow
1. Fork or create a feature branch from `main`.
2. Implement the change with tests/docs updates when relevant.
3. Run required checks locally.
4. Open a PR with clear scope, rationale, and testing notes.
5. Wait for owner review and approval.
6. Merge only after all checks pass.

## Local Setup
```bash
make setup
cp .env.example .env
```

## Required Checks Before PR
```bash
make lint
make type-check
make test
make security
```

If you changed CLI/operator behavior, also run:
```bash
uv run aegis --help
uv run aegis operator status
```

## Coding Standards
- Python `3.12+`.
- Use type hints for new/modified public interfaces.
- Keep error handling explicit and structured.
- Prefer deterministic behavior over hidden magic.
- Update docs for any user-facing change.

## Commit Message Guidance
Use clear, imperative messages.

Examples:
- `Add shadow verification retry backoff`
- `Fix incident status filtering in CLI`
- `Improve Trivy scan error reporting`

## PR Checklist
- [ ] Scope is focused and clearly described.
- [ ] Tests added/updated for behavior changes.
- [ ] Linting and type checks pass locally.
- [ ] Security checks pass.
- [ ] Docs updated (`README.md`, `CONTRIBUTION.md`, or relevant docs files).
- [ ] No secrets or credentials committed.

## Security Reporting
Do not open public issues for sensitive vulnerabilities.
Use responsible disclosure via repository security channels.

## License
By contributing, you agree that your contributions are licensed under GPL-3.0.
