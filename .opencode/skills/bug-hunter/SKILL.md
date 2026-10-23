---
name: bug-hunter
description: Systematic debugging, edge-case detection, async error handling, memory-leak prevention, and basic security auditing. Use when a bug is reported, code fails intermittently, something leaks or hangs, or a change needs an adversarial review for failure modes.
---

# Bug Hunter — Find the Cause, Not the Symptom

Do not patch the visible error. Reproduce it, shrink it, explain it, then fix
the invariant that allowed it.

## Loop

1. **Reproduce** — exact steps, input, environment, and version. Intermittent
   bugs need a loop count and a captured failure artifact.
2. **Observe** — logs, stack trace, network, DB state, profiler. Read the actual
   error before changing code.
3. **Isolate** — remove variables. Binary-search the input, the commit range
   (`git bisect`), or the code path. Make a failing test if possible.
4. **Hypothesize** — one sentence: "X happens because Y." Predict what changes
   if the hypothesis is true.
5. **Verify** — confirm the prediction. If wrong, discard the hypothesis; do not
   stack fixes.
6. **Fix the cause** — smallest correct change. No drive-by refactors.
7. **Regression test** — prove the bug cannot return.
8. **Blast radius** — search for the same pattern elsewhere. Fix or ticket it.

Never "fix" by adding a null check without understanding why the value is null.

## Edge-case checklist

**Input**
- null/undefined/None, empty string, whitespace, zero, negative, max int/float
- Unicode, emoji, RTL, combining characters, very long strings
- Duplicate keys, unknown fields, wrong types, nested depth
- Leading/trailing spaces, case sensitivity, locale-specific formatting

**Time and numbers**
- Timezone, DST transitions, leap day, "today" boundaries
- Clock skew, expired tokens, stale cache
- Float rounding; use integer minor units for money
- Off-by-one in ranges, pagination cursors, and retries

**State and concurrency**
- Double submit, rapid clicks, retry storms
- Race between read and write; lost updates
- Partial failure after a side effect; non-atomic multi-step writes
- Refresh during an in-flight request; unmount during a fetch
- Queue redelivery and at-least-once consumers

**Environment**
- Offline, slow 3G, high latency, DNS failure
- Permission denied, expired session, revoked role
- Storage full, quota exceeded, file too large
- Old browser, disabled JS, reduced motion, 320 px screen

## Async failures

- Missing `await`: the error escapes and the caller proceeds.
- `Promise.all` rejects on the first failure; use `allSettled` when every result matters.
- Unhandled rejections: add a global handler that logs and alerts, but still handle locally.
- No timeout: every external call gets a deadline.
- No cancellation: pass `AbortSignal` through fetch chains and stop work on unmount.
- Ordering: responses can arrive out of order; guard with a request id or sequence.
- Double submit: disable + idempotency key, not just a spinner.
- Fire-and-forget tasks: catch, log, and own the lifecycle.
- `try/catch` around an async call without `await` catches nothing.
- Cleanup in `finally`, not only on the success path.

## Memory leaks

- Event listeners and subscriptions without removal (`useEffect` cleanup,
  `removeEventListener`, `unsubscribe`).
- `setInterval`/`setTimeout` never cleared.
- Observers (`IntersectionObserver`, `ResizeObserver`, `MutationObserver`) not disconnected.
- Unbounded caches, maps, arrays, and event emitters.
- Closures retaining large objects or DOM nodes.
- WebSocket/SSE streams not closed on route change.
- Workers and audio/video contexts not terminated.
- Detached DOM held by JS references.

Protocol: DevTools Memory → heap snapshot → perform action 10× → snapshot again →
compare retained size and object counts. In Node, `--inspect` + heap snapshots,
or `process.memoryUsage()` over a soak test.

## Security basics

- **Injection:** parameterized SQL only; never string interpolation. Validate
  shell args; avoid `exec` with user input.
- **XSS:** escape by context; avoid `innerHTML`/`dangerouslySetInnerHTML` with
  untrusted data; sanitize Markdown with a maintained sanitizer; add CSP.
- **CSRF:** SameSite cookies + token for state-changing requests.
- **SSRF:** allowlist outbound hosts; block link-local/metadata IPs; no arbitrary URLs.
- **Path traversal:** resolve and verify the path stays inside the allowed root.
- **IDOR:** authorize the object, not just the route. Test with another user's id.
- **Secrets:** never log tokens, passwords, cookies, or full request bodies.
- **Errors:** generic message to the client, detail to the server log.
- **Dependencies:** run `pip-audit` / `npm audit`; pin and update.
- **Rate limits:** auth, search, and expensive generation endpoints.
- **Deserialization:** validate schema; never unpickle or eval untrusted input.

## Reporting

```
Symptom:    what the user sees
Repro:      minimal steps / input
Cause:      the invariant that was violated
Fix:        files and behavior changed
Test:       regression test added
Risk:       other paths affected
```

## Review checklist

- [ ] Reproduction captured before the fix.
- [ ] Root cause stated, not just the symptom.
- [ ] Failure path has a regression test.
- [ ] Async errors are awaited, handled, and cancelled.
- [ ] Listeners, timers, and streams are cleaned up.
- [ ] Authorization checked per object.
- [ ] No secrets or stack traces in client output.
- [ ] Same bug class searched elsewhere.
