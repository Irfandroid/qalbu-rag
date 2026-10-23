# Qalbu — Agent Rules

Project: FastAPI + Pydantic backend (`app/`), static frontend (`frontend/`),
Postgres/Supabase (`supabase/`), pytest/ruff/mypy. Python 3.11.

## Response style

- Default compact: answer first, no preamble, no filler, no closing offers.
- Code before prose when code is the answer.
- Report changes as `path:line — what changed`.
- Load `caveman` for the full protocol when the user asks for terse mode.
- Never compress security, data-loss, or irreversible-action warnings.

## Skill routing

Load the matching skill with the `skill` tool **before** editing. Multiple may apply.

| Work | Skill |
| --- | --- |
| Animation, transitions, micro-interactions | `emil-design` |
| Layout, hierarchy, type, color, Tailwind/shadcn | `taste-ui-ux` |
| Keyboard, focus, contrast, WCAG, mobile a11y | `accessibility-a11y` |
| Terse output / no filler | `caveman` |
| SOLID, DRY, refactor, module boundaries | `clean-code` |
| TypeScript types, Zod, mypy/Pydantic | `typescript-strict` |
| API design, DB queries, cache, auth | `backend-architect` |
| Unit/E2E tests, TDD, flaky tests | `test-engineer` |
| Debugging, edge cases, leaks, security | `bug-hunter` |
| CWV, bundle, lazy loading, memoization | `performance-optimizer` |
| Commits, PR body, history | `git-master` |

## Hard rules

- Read the relevant files before editing. Do not guess APIs or file contents.
- Preserve existing behavior unless the task changes it.
- Validate at boundaries: Pydantic at HTTP/config, Zod in TS.
- Never commit or print secrets from `.env`.
- No `git reset --hard`, `git clean -fd`, or force-push to shared branches
  without explicit confirmation.
- Add or update a test for behavior changes; run the narrowest relevant check.
- State what was verified and what was not. Do not claim a passing command you
  did not run.
- UI work must pass the a11y checklist: keyboard, focus, contrast, 320 px, reduced motion.
- Refactors stay separate from behavior changes in commits.

## Verification

```bash
pytest -q
ruff check .
mypy app
```

Frontend is static HTML; check the served page in a browser and test keyboard
navigation plus 320 px width.
