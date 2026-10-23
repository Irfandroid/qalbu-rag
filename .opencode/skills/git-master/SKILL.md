---
name: git-master
description: Conventional Commits, atomic commits, and clear pull request descriptions. Use when committing, splitting work into commits, writing commit messages or PR bodies, preparing a branch for review, or cleaning up history before merge.
---

# Git Master — History That Explains Itself

A commit is a message to the future: why this changed, what it affects, and how
to verify it. Optimize for the reviewer and for `git bisect`, not for speed.

## Atomic commits

- One logical change per commit. A feature and its formatting cleanup are two commits.
- Every commit should build and pass tests on its own when practical.
- Refactors separate from behavior changes. Rename/move separate from edits.
- Stage with intent: `git add -p`, review `git diff --staged` before committing.
- Never commit secrets, `.env`, credentials, dumps, or build output.
- Do not mix generated files with source unless the generator changed.

## Conventional Commits

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

Rules:
- Subject imperative, lowercase after the colon, no trailing period.
- ≤ 72 characters; scope is a stable area (`api`, `auth`, `chat`, `rag`, `ui`).
- Body explains **why** and the user-visible impact; wrap at 72.
- `BREAKING CHANGE:` footer or `!` after type/scope for incompatible changes.
- Reference issues in the footer (`Refs: #123`, `Closes: #123`).
- One topic per commit; if the subject needs "and", split it.

Examples:

```
feat(chat): stream reflection tokens over SSE

Keeps the UI responsive on slow provider responses and lets the client
render partial text. Falls back to a single JSON response when streaming
is unavailable.

Refs: #142
```

```
fix(rag): reject citations that are not in the retrieved context

The validator previously accepted any verse id returned by the model,
which allowed unsupported citations to reach the UI.

Closes: #151
```

```
refactor(providers)!: inject HTTP client into embedding adapters

BREAKING CHANGE: adapters now require an AsyncClient in the constructor.
```

Bad:

```
update stuff
fix bug
WIP
feat: added the new thing and fixed the other thing and updated deps
```

## Branching

- `feat/chat-streaming`, `fix/citation-validator`, `chore/deps`.
- Rebase on the target branch before review; keep the branch current.
- Do not force-push a shared branch. Force-push your own only with `--force-with-lease`.
- Delete merged branches.

## Pull requests

Keep PRs reviewable: under ~400 changed lines where possible. Split large work
into stacked PRs.

```markdown
## Summary
Streams reflection text over SSE so users see progress instead of a blank wait.

## Changes
- `app/api/routes/chat.py`: SSE endpoint with heartbeat and timeout
- `app/rag/pipeline.py`: yield tokens, keep final validation
- `frontend/index.html`: incremental render + abort on navigation

## Why
Provider latency is 3–6 s; a blocking response feels broken.

## Test plan
- [ ] `pytest tests/test_chat_stream.py`
- [ ] Manual: slow network, navigate away mid-stream
- [ ] `ruff check . && mypy app`

## Screenshots
Before / after (mobile + desktop).

## Risks and rollback
Falls back to JSON when streaming fails. Revert this commit to restore the
previous path; no migration involved.

Closes: #142
```

Rules:
- Title follows Conventional Commits.
- Summary is the user-facing outcome, not a file list.
- List the test plan with real commands and checkboxes.
- Call out migrations, config changes, and rollback steps.
- Link the issue and design doc.
- Self-review the diff before requesting review; remove debug code and TODOs.

## Review hygiene

- Comment on substance: correctness, edge cases, security, performance, naming.
- Distinguish blocking issues from nits (`nit:`).
- Do not rewrite the author's code in comments; suggest and explain.
- Approve only when tests and the contract are clear.

## Conflict resolution

1. Rebase or merge the target branch; never resolve by deleting the other side blindly.
2. Understand both changes before editing.
3. Re-run tests and type checks after resolution.
4. Verify no conflict markers remain: `git grep -n '<<<<<<<'`.

## Safety

- No `git reset --hard`, `git clean -fd`, or branch deletion without explicit confirmation.
- No `push --force` to `main`/shared branches.
- Inspect `git status` and `git diff` before destructive commands.
- Use `git stash push -m` with a message when parking work.
- Recover with `git reflog` before assuming work is lost.

## Checklist

- [ ] Each commit is one logical change and builds.
- [ ] Subject follows Conventional Commits and is ≤ 72 chars.
- [ ] Body explains why and notes breaking changes.
- [ ] No secrets, debug code, or unrelated formatting.
- [ ] PR has summary, test plan, risks, and issue link.
- [ ] Diff self-reviewed; tests and linters pass.
