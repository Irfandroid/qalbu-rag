---
name: test-engineer
description: TDD and automated testing with Vitest, Jest, Playwright, and pytest. Use when writing unit, integration, or end-to-end tests, setting up test infrastructure, fixing flaky tests, or when a feature should be built test-first.
---

# Test Engineer — Tests That Survive Refactors

Test behavior through public interfaces. A test that breaks when you rename a
private function is a liability, not a safety net.

## TDD loop

1. **Red** — write one failing test for the next behavior. Run it. Confirm it
   fails for the expected reason, not a typo.
2. **Green** — write the smallest implementation that passes. No extra features.
3. **Refactor** — clean up with the test green. Re-run after each step.

Commit the test and implementation together. Never write tests after the fact
and call it TDD.

## What to test

- Business rules, state transitions, edge cases, and failure paths.
- The contract at a seam: given input → observable output or side effect.
- Integration points you own (route → service → DB).
- One happy path and the critical failures per feature.

Do not test:
- Private methods, internal call order, or framework internals.
- Getters/setters with no logic.
- Third-party libraries; trust them or wrap and test the wrapper.

## Structure and naming

```ts
describe("applyDiscount", () => {
  it("applies 20% when the cart exceeds the threshold", () => {
    // Arrange
    const cart = makeCart({ subtotal: 120_00 });
    // Act
    const total = applyDiscount(cart);
    // Assert
    expect(total).toBe(96_00);
  });
});
```

- Name the behavior, not the method: `returns 404 when the source is missing`.
- One logical assertion group per test.
- Use factories/builders (`makeUser`) over shared mutable fixtures.
- Keep tests independent; order must not matter.
- Prefer explicit values over random data; seed randomness when needed.

## Vitest

```ts
// vitest.config.ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./test/setup.ts"],
    restoreMocks: true,
    clearMocks: true,
  },
});
```

```ts
import { vi, expect, it } from "vitest";

it("retries once on a 503", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(new Response(null, { status: 503 }))
    .mockResolvedValueOnce(Response.json({ ok: true }));

  const result = await loadWithRetry(fetchMock);

  expect(result).toEqual({ ok: true });
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

it("debounces input", async () => {
  vi.useFakeTimers();
  const onSearch = vi.fn();
  const search = debounce(onSearch, 300);

  search("a");
  search("ab");
  await vi.advanceTimersByTimeAsync(300);

  expect(onSearch).toHaveBeenCalledOnce();
  expect(onSearch).toHaveBeenCalledWith("ab");
  vi.useRealTimers();
});
```

Rules: mock at the boundary (network, clock, filesystem, randomness), not the
module under test. Use MSW for HTTP instead of stubbing `fetch` everywhere.
Jest uses the same shape with `jest.fn()` and `jest.useFakeTimers()`.

## Playwright (E2E)

```ts
// playwright.config.ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [["html"], ["github"]],
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
  },
});
```

```ts
test("user gets a reflection with a cited source", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("textbox", { name: /apa yang kamu rasakan/i }).fill("Aku cemas.");
  await page.getByRole("button", { name: /kirim/i }).click();

  await expect(page.getByRole("status")).toContainText(/refleksi/i);
  await expect(page.getByRole("link", { name: /sumber/i }).first()).toBeVisible();
});
```

Rules:
- Query by role, label, or text — the way a user finds things.
- Never use `waitForTimeout`. Wait for a state: `toBeVisible`, `toHaveURL`,
  `expect.poll`, or a specific response.
- Isolate state per test; create data through the API or a fixture, clean up after.
- Authenticate once with `storageState`, do not log in through the UI every test.
- Keep E2E for critical journeys (≤ 10–20 tests); push detail down to integration tests.
- Test at least one mobile viewport for responsive features.

## pytest (this repo)

```python
import pytest

@pytest.mark.parametrize(
    ("text", "expected"),
    [("", False), ("   ", False), ("Aku cemas", True)],
)
def test_is_meaningful_input(text: str, expected: bool) -> None:
    assert is_meaningful_input(text) is expected
```

- `asyncio_mode = "auto"` is configured; use `async def` tests directly.
- Use `httpx.AsyncClient` with `ASGITransport` for API tests; no live server.
- Override FastAPI dependencies instead of monkeypatching internals.
- Use `tmp_path`, `monkeypatch`, and fixtures; no shared global state.
- Mock provider adapters at the seam; assert the request shape you send.
- Mark slow/network tests and exclude them from the default run.

## Flakiness rules

- No sleeps. Control time with fake timers or injected clocks.
- Seed random, UUID, and date generation.
- Isolate DB state; use transactions/rollback or unique per-test data.
- Wait for observable conditions, not elapsed time.
- Run the suite repeatedly (`--repeat-each=10`) to expose races.
- A flaky test is failing. Fix or delete it; never retry-until-green in CI.

## Coverage and CI

- Coverage finds untested areas; it is not a target. 80% meaningful beats 100% shallow.
- Require tests for changed business logic, not for every line.
- CI: lint → typecheck → unit/integration (parallel) → E2E (sharded) →
  upload traces and reports.
- E2E retries allowed in CI only, with traces enabled.

## Review checklist

- [ ] Test fails before the fix and passes after.
- [ ] Assertions are behavioral, not implementation-coupled.
- [ ] Edge and failure cases covered, not only the happy path.
- [ ] No sleeps, shared state, or order dependence.
- [ ] Mocks live at system boundaries.
- [ ] Test names describe the contract.
- [ ] CI runs the suite and keeps failure artifacts.
