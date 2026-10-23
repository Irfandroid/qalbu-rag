---
name: accessibility-a11y
description: Accessibility and responsive-design standards (WCAG 2.2 AA). Use when building UI, forms, navigation, modals, tables, or when checking keyboard support, focus management, contrast, screen-reader semantics, touch targets, zoom, or mobile reflow.
---

# Accessibility — WCAG 2.2 AA Baseline

Accessibility is a correctness requirement, not a polish task. Build it into
markup and state from the start; retrofitting ARIA is expensive and fragile.

## Semantic HTML first

- Use the native element: `button` for actions, `a href` for navigation.
- Never attach click handlers to `div` or `span` without role, tabindex, and key handling.
- One `h1` per page; headings in order, no levels skipped for styling.
- Use `header`, `nav`, `main`, `aside`, `footer`, `section` with accessible names.
- Lists are `ul`/`ol`; tabular data is `table` with `th` and `scope`.
- `label` for every form control. Placeholder is not a label.
- Language set on `html` (`lang="id"`), and `lang` on foreign passages.

## Keyboard

- Every interactive element reachable in a logical order with `Tab`.
- Visible focus at all times: 2 px ring, 2 px offset, 3:1 against adjacent colors.
  Never `outline: none` without an equivalent visible replacement.
- `Enter`/`Space` activate buttons; `Enter` follows links; `Esc` closes overlays.
- No keyboard traps. Modals trap focus intentionally and release it on close.
- Composite widgets (tabs, menus, listbox, grid) use roving tabindex and arrow keys.
- Provide a "skip to content" link as the first focusable element.
- Custom drag interactions need a keyboard alternative.

## Focus management

- Opening a modal: move focus to the dialog or its first meaningful control.
- Closing: return focus to the trigger.
- Client-side route change: move focus to the new `h1` or `main` and announce the page.
- Do not steal focus on load or on every re-render.
- Use `inert` or `aria-hidden` on background content while a modal is open.

## Contrast and color

| Element | Minimum |
| --- | --- |
| Body text | 4.5:1 |
| Large text (≥24 px, or ≥18.66 px bold) | 3:1 |
| UI components and focus indicators | 3:1 |
| Disabled text | Exempt, but keep it readable |

- Never encode meaning with color alone; add text, icon, or pattern.
- Check hover, focus, active, disabled, and dark mode separately.
- Placeholder text still needs 4.5:1 if it conveys information.
- Charts need labels or a table alternative.

## Forms

- Visible label, programmatic association (`for`/`id` or wrapping label).
- Required state conveyed in text, not only `*` or color.
- Errors: inline, next to the field, announced, and linked with `aria-describedby`.
- Error summary at the top for long forms, linking to each field.
- `autocomplete` tokens for name, email, tel, address, and passwords.
- Do not block paste on password fields.
- Give users enough time; no aggressive session timeout without warning.

## ARIA rules

1. Do not use ARIA if native HTML works.
2. Do not change native semantics (`role="button"` on a `button`).
3. Every ARIA role needs its required states and properties.
4. Interactive ARIA controls must be keyboard operable.
5. Accessible names are mandatory for controls, dialogs, and landmarks.

Useful patterns:
- `aria-expanded` + `aria-controls` for disclosure.
- `aria-current="page"` for navigation.
- `aria-live="polite"` for async status; `assertive` only for errors.
- `aria-busy="true"` while loading a region.
- `aria-describedby` for help and error text.
- `role="status"` for non-critical confirmations.

## Responsive and zoom

- Support 320 CSS px width without horizontal scrolling.
- Content reflows at 400% zoom (equivalent to 320 px) without loss.
- Text scales to 200% without clipping or overlap.
- No fixed heights on text containers.
- Touch targets ≥44×44 px (WCAG 2.2 minimum 24×24 with spacing).
- Do not disable pinch zoom: never `user-scalable=no` or `maximum-scale=1`.
- Respect safe areas on notched devices (`env(safe-area-inset-*)`).
- Orientation is not locked unless essential.

## Motion and media

- Honor `prefers-reduced-motion`; remove translation, scale, parallax, and autoplay.
- No content that flashes more than three times per second.
- Autoplaying media over 5 s needs pause/stop and mute.
- Images: meaningful `alt`, decorative `alt=""`. No "image of".
- Video: captions; audio: transcript.
- Do not autofocus fields on mobile (it opens the keyboard unexpectedly).

## Testing protocol

1. **Keyboard-only:** unplug the mouse; complete the primary task.
2. **Screen reader:** NVDA on Windows or VoiceOver on macOS for one full flow.
3. **Zoom:** 200% and 400%; check reflow and clipping.
4. **Automated:** axe DevTools or `@axe-core/playwright`; fix all serious/critical.
5. **Contrast:** check tokens, not individual screenshots.
6. **Mobile:** 320 px viewport, landscape, and touch-only.

Automated tools catch roughly a third of issues. Keyboard and screen-reader
checks are not optional.

## Definition of done

- [ ] Primary flow works with keyboard only.
- [ ] Focus is visible and managed across overlays and route changes.
- [ ] Every control has an accessible name.
- [ ] Contrast passes for text, UI, and focus rings.
- [ ] Errors are announced and linked to fields.
- [ ] Layout works at 320 px and 400% zoom.
- [ ] Reduced-motion path verified.
- [ ] No axe serious or critical violations.
