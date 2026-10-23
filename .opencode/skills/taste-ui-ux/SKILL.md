---
name: taste-ui-ux
description: Visual hierarchy, spacing, typography, and color-system standards for modern product UI. Use when building or polishing screens, Tailwind CSS or shadcn/ui components, dashboards, marketing pages, empty states, or when a UI looks generic, cramped, or visually inconsistent.
---

# Taste UI/UX — Intentional Interfaces

Good taste is not decoration. It is consistent decisions applied under
constraint: one hierarchy, one spacing scale, one type scale, one accent.

## Hierarchy

- One primary action per view. Everything else is secondary or tertiary.
- Maximum three visual levels in a section (title, supporting, body).
- Create hierarchy with size, weight, color, and space — in that order.
- If everything is bold, nothing is. Use weight 400/500/600/700 only.
- The eye should land on the same element in under one second.

## Spacing

Use a 4 px base scale. Do not invent values.

| Token | px | Typical use |
| --- | --- | --- |
| 1 | 4 | Icon-to-label, tight pairs |
| 2 | 8 | Inside buttons, chips |
| 3 | 12 | Form field gaps |
| 4 | 16 | Card padding (compact), stack gaps |
| 6 | 24 | Card padding, group separation |
| 8 | 32 | Section inner spacing |
| 12 | 48 | Block separation |
| 16 | 64 | Section separation (mobile) |
| 24 | 96 | Section separation (desktop) |

Rules:
- Related items closer than unrelated items. Proximity beats borders.
- Use one spacing system everywhere; no `mt-[13px]` one-offs.
- Whitespace is structure, not waste. Dense UIs still need 12–16 px breathing room.
- Align to the same left edge; optical alignment beats mathematical alignment for icons.

## Typography

- Two families maximum: one UI sans, optionally one display or mono.
- Type scale (1.2–1.25 ratio): 12, 14, 16, 20, 24, 30, 38, 48, 60.
- Body 15–17 px, line-height 1.5–1.65; headings 1.1–1.25.
- Measure 60–75 characters (`max-w-prose`).
- Large headings need negative tracking (`-0.02em` to `-0.03em`).
- Weight contrast is stronger than many sizes: pair 600 heading with 400 body.
- Never use more than one italic or all-caps treatment per screen.
- Tabular numbers for tables, prices, and counters (`font-variant-numeric: tabular-nums`).

## Color

Define semantic tokens, never raw hex in components.

```css
:root {
  --background: 0 0% 100%;
  --foreground: 240 10% 12%;
  --muted: 240 5% 96%;
  --muted-foreground: 240 4% 46%;
  --border: 240 6% 90%;
  --primary: 243 75% 59%;
  --primary-foreground: 0 0% 100%;
  --destructive: 0 72% 51%;
  --ring: 243 75% 59%;
}
```

- One accent hue. Neutrals carry the rest.
- Tint neutrals slightly toward the accent hue for cohesion.
- Text contrast: 4.5:1 minimum, 7:1 for small or critical text.
- Do not use pure black on pure white; use near-black and off-white.
- Dark mode is a designed theme, not an inversion. Recheck contrast and elevation.
- Semantic color only: success, warning, destructive, info. Never use red for emphasis.

## Layout

- Content max width 1100–1280 px; prose 65–75 ch.
- 12-column grid on desktop, single column on mobile.
- Breakpoints: `sm 640`, `md 768`, `lg 1024`, `xl 1280`.
- Mobile-first: design the 375 px view first, then add.
- Prefer CSS grid for page structure; flex for one-dimensional alignment.
- Sticky headers must not cover anchored content; account for their height.
- Touch targets at least 44×44 px with 8 px separation.

## Tailwind + shadcn/ui

- Use tokens (`bg-background`, `text-muted-foreground`, `border-border`), not arbitrary colors.
- Use `cn()` for conditional classes; `cva` for variants. No string concatenation.
- Keep a consistent radius: pick one (`rounded-lg` or `rounded-xl`) and apply everywhere.
- shadcn is a starting point, not a finished design. Adjust spacing, type, and states.
- Use `gap-*` instead of margins between flex/grid children.
- Prefer `size-*` for square icons and controls.
- Do not stack `border` + strong `shadow` + gradient on the same surface.
- Use `data-[state=open]` variants for Radix state, not JS class toggles.
- One icon library, one stroke width (1.5 or 2).

## Required states

Every data surface needs all five:

1. **Loading** — skeleton matching final layout, not a spinner in the middle of nowhere.
2. **Empty** — explain what goes here and the next action.
3. **Error** — human message, retry, no stack trace.
4. **Success** — confirm the outcome without a modal.
5. **Partial/degraded** — say what is missing and what still works.

Forms: label above field, helper text below, inline error that does not shift layout.
Buttons: loading state keeps width, disables double submit, keeps the label.

## Polish pass

- Check optical alignment of icons with text.
- Normalize icon sizes: 16 inline, 20 controls, 24 navigation.
- Ensure every interactive element has hover, focus-visible, active, disabled.
- Verify long words, long emails, and unbroken strings do not overflow.
- Check 320 px width, 200% zoom, and dark mode.
- Remove one border, one shadow, or one color from busy screens.

## Avoid

- Gradient text, glassmorphism everywhere, neon glows.
- Centering all content; left-aligned reading is easier.
- More than two font families or five font sizes per screen.
- Cards inside cards inside cards.
- Icon-only buttons without labels or tooltips.
- Inconsistent radii, shadows, and vertical rhythm.
- Placeholder text used as the only label.

## Review checklist

- [ ] One clear primary action.
- [ ] Spacing uses the 4 px scale only.
- [ ] Type scale and line-height are consistent.
- [ ] Colors come from semantic tokens.
- [ ] All five states exist.
- [ ] Contrast passes in light and dark mode.
- [ ] Layout holds at 320 px and 200% zoom.
- [ ] No decorative element competes with content.
