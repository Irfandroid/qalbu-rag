---
name: performance-optimizer
description: Core Web Vitals, bundle size, lazy loading, memoization, and backend query performance. Use when a page or endpoint is slow, before shipping a UI, when optimizing LCP/INP/CLS, reducing JavaScript, or fixing unnecessary re-renders and expensive queries.
---

# Performance Optimizer — Measure, Change One Thing, Measure Again

No optimization without a baseline. A change that is not measured is a guess,
and most performance guesses are wrong.

## Targets (p75, mobile)

| Metric | Good | Needs work |
| --- | --- | --- |
| LCP | ≤ 2.5 s | ≤ 4.0 s |
| INP | ≤ 200 ms | ≤ 500 ms |
| CLS | ≤ 0.1 | ≤ 0.25 |
| TTFB | ≤ 800 ms | ≤ 1.8 s |

Define budgets for JS (≤ 170 KB gzip initial), CSS, images, and fonts. Enforce
them in CI with Lighthouse CI or bundlesize.

## Measure

- Field: RUM/CrUX, Sentry, or a small `web-vitals` reporter. Segment by device and route.
- Lab: Lighthouse (throttled), WebPageTest, DevTools Performance and Network.
- React: Profiler "record why each component rendered".
- Node/Python: p50/p95/p99 latency, query count per request, flame graph.
- Record the baseline before touching code. Keep the before/after numbers in the PR.

## Loading path

- **LCP:** identify the element, then preload the hero image/font, serve it at
  the right size, avoid lazy-loading it, and keep it out of client-rendered JS.
- Images: AVIF/WebP, `srcset`/`sizes`, explicit `width`/`height`, `loading="lazy"`
  below the fold, `fetchpriority="high"` on the LCP image.
- Fonts: `font-display: swap`, subset, preload one weight, self-host, avoid FOIT.
- CSS: critical CSS inline, defer the rest, avoid huge utility purge misses.
- JS: `defer`/`type="module"`, no render-blocking third parties.
- Third parties: load after interaction, self-host where possible, audit tags quarterly.
- SSR/streaming: send meaningful HTML before data; do not block the shell on personalization.
- CLS: reserve space for media, ads, and async content; never inject banners above content.

## Bundle

- Analyze first: `vite-bundle-visualizer`, `source-map-explorer`, `next build --analyze`.
- Route-level code splitting; dynamic-import heavy widgets (editors, charts, maps, chat).
- Import directly (`import { x } from "lib/x"`), not from a barrel that pulls the world.
- Tree-shake: ESM, `sideEffects: false`, no top-level side effects.
- Replace moment/lodash-full/axios with smaller equivalents when it pays.
- Keep one version of React and shared deps; dedupe.
- Target modern browsers; drop legacy polyfills unless analytics justify them.
- Compress with Brotli at the CDN; hash assets and cache immutably.

```tsx
const Chart = lazy(() => import("./Chart"));

<Suspense fallback={<ChartSkeleton />}>
  <Chart data={data} />
</Suspense>
```

Do not lazy-load the primary above-the-fold content. It worsens LCP.

## Runtime and rendering

- Memoize only measured hot paths. `useMemo`/`useCallback` have a cost and add noise.
- Fix the cause of re-renders first: state placement, context splitting, stable keys.
- Do not create objects/arrays inline as effect dependencies; memoize or move them out.
- Virtualize lists over ~100 rows (`@tanstack/react-virtual`).
- Debounce search input (200–300 ms); throttle scroll/resize; prefer `IntersectionObserver`.
- Move CPU-heavy parsing to a Web Worker; keep the main thread for input.
- Use `startTransition` for non-urgent updates; `useDeferredValue` for filtering.
- Batch DOM reads and writes; avoid layout thrash in loops.
- Animate only `transform`/`opacity`; see `emil-design`.
- Avoid synchronous `localStorage` reads in hot paths; cache in memory.

## Network and API

- Paginate and limit payloads; return only fields the screen uses.
- Compress JSON (gzip/brotli) and enable keep-alive/HTTP2+.
- Cache at the edge for public reads; `stale-while-revalidate` for semi-static data.
- Deduplicate in-flight requests; cancel stale ones with `AbortController`.
- Prefetch the next likely route/data on intent (hover/focus), not on load.
- Batch requests; avoid request waterfalls in SSR.

## Database and backend

- Index the filter/sort columns; verify with `EXPLAIN ANALYZE`.
- Remove N+1 queries; log query count per request.
- Select only needed columns; avoid `SELECT *`.
- Cache expensive aggregates with explicit invalidation.
- Pool connections; set timeouts; stream large exports.
- Offload slow work to a background job and return `202`.

## Process

1. Baseline (numbers, device, route).
2. Profile; find the top bottleneck, not the tenth.
3. Change one thing.
4. Re-measure under the same conditions.
5. Keep or revert based on data.
6. Add a budget/regression guard.
7. Document the result in the PR.

## Anti-patterns

- Premature `React.memo` everywhere.
- Lazy-loading everything, including the hero.
- Huge icon libraries imported wholesale.
- Unoptimized 4 MB PNGs and web fonts with five weights.
- Client-side fetching for content that could be server-rendered.
- "Optimizing" without a before/after measurement.
- Raising a budget to make CI pass.

## Review checklist

- [ ] Baseline and target recorded.
- [ ] LCP element identified and prioritized.
- [ ] Images sized, compressed, and lazy below the fold.
- [ ] Initial JS within budget; heavy widgets split.
- [ ] No unnecessary re-renders on interaction.
- [ ] Lists virtualized where needed.
- [ ] Queries indexed and free of N+1.
- [ ] Caching headers and invalidation defined.
- [ ] Before/after numbers included in the PR.
