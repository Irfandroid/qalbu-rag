---
name: emil-design
description: Motion and micro-interaction design in the style of Emil Kowalski. Use when adding animations, transitions, hover/press states, modals, drawers, toasts, page transitions, or when UI motion feels sluggish, bouncy, or distracting.
---

# Emil Design — Motion That Earns Its Place

Motion is feedback, continuity, and causality. It is never decoration. Every
animation must answer: what changed, where did it come from, and what can I do
next? If it does not answer one of those, delete it.

## Non-negotiables

1. **Respond in under 100 ms.** Press, hover, and toggle feedback must feel
   instant. Delay reads as a broken control.
2. **Animate `transform` and `opacity`.** Never animate `width`, `height`,
   `top`, `left`, `margin`, or `box-shadow`. For disclosure, animate
   `grid-template-rows: 0fr → 1fr`.
3. **Exit faster than enter.** Leaving should feel decisive: enter 200 ms,
   exit 150 ms.
4. **Interruptible.** A new input animates from the current visual value, never
   from the start. Springs and CSS transitions do this; keyframe replays do not.
5. **No motion without meaning.** No floating blobs, parallax, or ambient
   loops behind content.
6. **Respect `prefers-reduced-motion`.** Remove translation and scale; keep a
   short opacity change.

## Tokens

| Token | Value | Use |
| --- | --- | --- |
| `--dur-instant` | 80 ms | Color/opacity on press |
| `--dur-fast` | 120 ms | Hover, focus, small toggles |
| `--dur-base` | 200 ms | Popovers, dropdowns, tooltips |
| `--dur-slow` | 300 ms | Modals, drawers, sheets |
| `--ease-out` | `cubic-bezier(0.16, 1, 0.3, 1)` | Enter, expand, appear |
| `--ease-in` | `cubic-bezier(0.7, 0, 0.84, 0)` | Exit, collapse, dismiss |
| `--ease-in-out` | `cubic-bezier(0.65, 0, 0.35, 1)` | On-screen movement |

```css
:root {
  --dur-fast: 120ms;
  --dur-base: 200ms;
  --dur-slow: 300ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-in: cubic-bezier(0.7, 0, 0.84, 0);
}

.button {
  transition:
    background-color var(--dur-fast) ease,
    transform var(--dur-fast) var(--ease-out);
}
.button:active { transform: scale(0.97); }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

## Springs (physics-based)

For anything the user drags, swipes, or directly manipulates, use a spring.
For anything that appears on its own, use a duration curve.

| Feel | stiffness | damping | mass |
| --- | --- | --- | --- |
| Snappy UI | 320 | 32 | 0.9 |
| Gentle sheet | 260 | 30 | 1 |
| Drag / carousel | 240 | 28 | 1 |

Rules:
- Never bounce on text, forms, or destructive confirmations.
- Bounce is allowed only for playful, low-stakes drag release.
- Critically damped or slightly under-damped (`damping ≈ 2 * sqrt(stiffness * mass)`) is the default.

```tsx
import { motion, useReducedMotion } from "motion/react";

export function Sheet({ open }: { open: boolean }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      initial={{ opacity: 0, y: reduce ? 0 : 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: reduce ? 0 : 8 }}
      transition={{ type: "spring", stiffness: 320, damping: 32, mass: 0.9 }}
    />
  );
}
```

## Interaction recipes

- **Press:** `scale(0.97)`, 120 ms, release back with `--ease-out`.
- **Hover lift:** `translateY(-1px)` max. Do not combine lift + scale + shadow.
- **Modal:** backdrop fades 150 ms; panel `opacity 0→1`, `scale 0.96→1`,
  `y 8→0` over 200 ms. Origin near the trigger when the trigger is visible.
- **Toast:** slide 8–12 px + fade, 200 ms in, 150 ms out. Never bounce.
- **Accordion:** `grid-template-rows` 200 ms `--ease-out`; rotate chevron 180°.
- **List add/remove:** FLIP/layout animation 200 ms; stagger 20–30 ms, cap the
  total stagger at ~200 ms regardless of item count.
- **Skeleton:** opacity pulse 1.2–1.6 s, `ease-in-out`; no shimmer sweep.
- **Page transition:** opacity + 4 px rise, 200 ms. Do not slide entire pages.
- **Number change:** cross-fade or 120 ms slide, never a slot-machine spin.

## What good motion feels like

- Fast enough to feel causal, slow enough to be seen.
- The end state is stable; nothing overshoots its final position accidentally.
- Simultaneous properties share one duration and one easing.
- The interface stays usable during the animation; inputs are never blocked.
- Motion reads the same at 60 Hz and on a throttled laptop.

## Anti-patterns

- `transition: all` — animates properties you did not intend.
- Durations above 400 ms for UI chrome.
- Bounce/elastic easing on menus, modals, or errors.
- Animating `box-shadow`, `filter: blur()` on large surfaces, or layout props.
- Hover effects that are the only affordance (touch users never see them).
- Entrance animations on every section; one hero moment per page is enough.
- Infinite ambient motion in the content area.
- Blocking clicks or focus until an animation finishes.

## Review checklist

- [ ] Every animation has a stated purpose.
- [ ] Press/hover feedback under 100 ms.
- [ ] Only compositor-friendly properties animate.
- [ ] Exit is shorter than enter.
- [ ] Animation interrupts cleanly mid-flight.
- [ ] Reduced-motion path is implemented and tested.
- [ ] No layout shift caused by the animation.
- [ ] Timing tokens are reused, not hardcoded per component.
