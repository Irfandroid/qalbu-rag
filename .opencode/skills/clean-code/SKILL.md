---
name: clean-code
description: SOLID principles, separation of concerns, DRY, and maintainable refactoring. Use when designing modules, reviewing code quality, removing duplication, untangling large functions or god objects, or refactoring safely without changing behavior.
---

# Clean Code — Maintainable by Default

Optimize for the next reader and the next change, not for cleverness. A module
should hide complexity behind a small interface, not leak it to callers.

## SOLID, applied

**S — Single Responsibility.** One reason to change. Split by axis of change,
not by line count. A FastAPI route parses HTTP; a service decides; a repository
persists. Do not put SQL in the route.

**O — Open/Closed.** Add behavior by adding a new implementation, not by editing
a growing `if/elif` chain. Use strategy functions, registries, or protocols.

```python
# Instead of: if provider == "jina": ... elif provider == "openai": ...
PROVIDERS: dict[str, EmbeddingProvider] = {"jina": JinaProvider(), ...}
provider = PROVIDERS[name]
```

**L — Liskov Substitution.** A subtype must honor the parent's contract:
same accepted inputs, same guarantees, no new exceptions. Prefer composition
over inheritance when the contract cannot be preserved.

**I — Interface Segregation.** Small, role-specific interfaces. Do not force
callers to depend on methods they never use.

**D — Dependency Inversion.** Business logic depends on abstractions; adapters
depend on details. Inject clients, clocks, and repositories at the boundary.

## DRY without premature abstraction

- Rule of three: duplicate twice, abstract the third time.
- Duplicate code is cheaper than the wrong abstraction.
- Abstract by **concept**, not by similar-looking lines.
- If the shared function needs flags to serve each caller, it is two functions.
- Keep test setup duplication; it makes tests readable.

## Functions

- Do one thing at one level of abstraction.
- Target ≤ 30 lines and ≤ 3 parameters. Use a typed object for more.
- No boolean flag parameters that switch behavior; split the function.
- Prefer early returns and guard clauses over nesting deeper than two levels.
- Return values; avoid mutating arguments unless the API says so.
- Name by intent: `charge_customer`, not `process_data_2`.

## Naming

- Intention-revealing, pronounceable, searchable.
- No abbreviations except domain-standard ones (`url`, `id`, `http`).
- Use the project's domain vocabulary; read `GLOSSARY.md` if present.
- Booleans read as predicates: `is_active`, `has_access`, `can_retry`.
- Collections plural; maps `by_id`; units in the name when relevant (`timeout_ms`).

## Boundaries

- Validate and normalize at the edge (HTTP, CLI, queue, env).
- Keep the core pure: domain rules should not import FastAPI, requests, or ORM models.
- Translate between DTO, domain, and persistence models. Do not let one leak everywhere.
- Wrap third-party SDKs behind a small adapter you own.
- Side effects (I/O, time, randomness) belong at the edges and are injected.

## Errors

- Fail fast on programmer errors; handle expected failures explicitly.
- Never `except Exception: pass` or `.catch(() => {})`.
- Raise/throw typed, meaningful errors with context; preserve the cause.
- Do not use exceptions for normal control flow.
- Clean up resources with context managers / `try-finally`.

## Comments and docs

- Comment **why**, not **what**. The code says what.
- Delete commented-out code; version control remembers it.
- Document public contracts, invariants, and non-obvious trade-offs.
- Keep docstrings about behavior and constraints, not a line-by-line translation.

## Refactoring loop

1. Tests green (or write characterization tests first).
2. One small, behavior-preserving change.
3. Run tests and type checks.
4. Commit separately from feature work.
5. Repeat. Never mix a refactor with a behavior change in one commit.

## Smells → moves

| Smell | Move |
| --- | --- |
| Long function | Extract by steps; name each step |
| Deep nesting | Guard clauses, extract predicate |
| God class | Split by responsibility |
| Primitive obsession | Value object / branded type |
| Feature envy | Move method to the data owner |
| Shotgun surgery | Consolidate the concept |
| Divergent change | Split the module |
| Temporal coupling | Make the order explicit in one function |
| Magic number/string | Named constant or config |
| Flag argument | Two functions |

## Review checklist

- [ ] Each module has one clear responsibility.
- [ ] Public interface is smaller than the implementation.
- [ ] No duplicated business rule.
- [ ] Functions fit on a screen and take few parameters.
- [ ] No hidden global state or ambient I/O in the core.
- [ ] Errors are explicit and typed.
- [ ] Names use domain language.
- [ ] Refactor commits contain no behavior change.
