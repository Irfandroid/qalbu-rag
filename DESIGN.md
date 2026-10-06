# Qalbu Design System

Single source of truth for Stitch generation and frontend implementation.

## Design Read

Reading this as: a private Quran reflection companion for Indonesian Muslims, in a contemporary quiet-manuscript visual language, dial **ENERGY 1 / RHYTHM 2 / MOTION 1**.

Qalbu must feel calm, credible, and human. It is not a generic AI dashboard, a social messenger clone, a therapy product, or a religious authority. The interface makes the source material easy to inspect before asking the user to trust a generated reflection.

## 1. Product Experience Principles

1. **Source before synthesis.** Show the retrieved Quran passage before or together with the generated reflection. The reflection never visually outranks the evidence.
2. **Grounded or honest fallback.** Weak retrieval, unavailable generation, and failed citation validation each have a clear non-generated state.
3. **Safety before intelligence.** Crisis handling is visually distinct, deterministic, short, and never presented as model output.
4. **Respect the sacred text.** Arabic is exact, right-to-left, never truncated, animated, stylized as decoration, or placed under another control.
5. **Quiet transparency.** Dataset name, source version, citation, and retrieval status are accessible without turning the main chat into an engineering console.
6. **Private by default.** The active runtime profile and privacy implication are stated in plain Indonesian.
7. **No false authority.** Qalbu is a reflection companion, not a therapist, diagnostic tool, fatwa source, or substitute for qualified help.

## 1A. Relationship and ABI Contract

Qalbu is relationship-centered without simulating a human relationship. The user remains the
owner of meaning, interpretation, decisions, and next steps; Qalbu only retrieves, organizes,
explains, and opens a quiet space for reflection. The product should strengthen the user's
relationship with the Qur'an, trusted people, and their own lived context—not maximize messages
or make Qalbu feel indispensable.

Every response follows this order when sources are available:

1. **Acknowledge:** recognize the user's stated experience without diagnosis or judgment.
2. **Qur'an:** show the exact Arabic, Indonesian translation, citation, and provenance.
3. **Meaning:** explain the connection as a tentative reflection, never as divine certainty.
4. **Tafsir:** disclose the tafsir source and keep it distinct from AI wording.
5. **Reflect:** offer one open, optional question or small step; leave the decision to the user.

The ABI trust contract is visible in the interface:

- **Ability:** only retrieved Quran, translation, tafsir, and themes may support a claim.
- **Benevolence:** use calm, non-preachy language; suffering is not evidence of weak faith.
- **Integrity:** label AI reflection, source, and tafsir separately; prefer an honest fallback to a
  forced verse, invented citation, or overconfident interpretation.

Progressive disclosure keeps the first view readable: acknowledgement and one to three sources
come first; tafsir detail, retrieval explanation, and related exploration remain expandable. A
crisis state bypasses normal reflection and uses the reviewed deterministic support response.

## 2. Atmosphere and Identity

### Direction

Use a warm paper canvas, deep forest ink, one muted moss accent, precise hairlines, and generous reading space. The visual character should sit between a carefully typeset study note and a familiar private conversation.

### Identity motif: evidence thread

A thin vertical or horizontal rule connects retrieval evidence to its parent passage. Small child markers may sit on the rule, while the expanded parent passage receives the largest reading area. This is the only recurring decorative gesture.

Reason: the motif makes the parent-child RAG relationship understandable without exposing database terminology in the default user view.

### What changes from the old "Nur Aurora" direction

- Remove violet, cyan, and coral gradients.
- Remove glowing orbs, blurred blobs, glass panels, and decorative sparkles.
- Replace Inter and Fraunces with type chosen for quiet screen reading.
- Replace multi-color action chips with one accent and clear text hierarchy.
- Keep warmth, generous space, careful Arabic rendering, and visible source provenance.

Reason: Qalbu earns trust through evidence and restraint, not through familiar AI decoration.

## 3. Color System

### Light theme

| Token | Value | Role |
|---|---:|---|
| `canvas` | `#F4F1E8` | App background, warm enough to reduce clinical sterility |
| `paper` | `#FFFDF7` | Reading surfaces, composer, assistant messages |
| `paper-muted` | `#ECEDE4` | Selected row, skeleton, quiet grouping |
| `ink` | `#173A31` | Primary text, navigation, high-emphasis controls |
| `ink-muted` | `#66736D` | Metadata and secondary explanation |
| `line` | `#D3D6CB` | Dividers and control borders |
| `accent` | `#55724E` | Active state, user message, grounded status, focus ring |
| `accent-soft` | `#E3EBDD` | Selected suggestion and evidence highlight |

### Dark theme

| Token | Value | Role |
|---|---:|---|
| `canvas` | `#111A17` | App background |
| `paper` | `#19241F` | Reading surfaces and assistant messages |
| `paper-muted` | `#23302A` | Selected row and quiet grouping |
| `ink` | `#EFF2E9` | Primary text |
| `ink-muted` | `#AEB8B1` | Metadata |
| `line` | `#36473F` | Dividers and borders |
| `accent` | `#9BB890` | Active state and focus ring |
| `accent-soft` | `#2B4034` | Selected suggestion and evidence highlight |

### Semantic states

Semantic colors do not act as decoration and never compete with the moss accent.

| State | Foreground | Background | Use |
|---|---:|---:|---|
| Error | `#7E3F3A` | `#F5E7E3` | Request failure and validation failure |
| Crisis | `#6F3333` | `#F4E2DE` | Deterministic crisis response only |
| Warning | `#765822` | `#F4ECD8` | Stale corpus or incomplete source metadata |

Use no gradient, glow, colored shadow, pure black, or saturated AI blue. Text and interactive boundaries must meet WCAG AA in both themes.

Reason: a limited earth palette supports long reading, gives Arabic and citations visual dignity, and keeps safety colors meaningful.

## 4. Typography

### Families

- **Interface and Indonesian text:** `Satoshi`, fallback `Arial`, `sans-serif`.
- **Arabic Quran text:** `Noto Naskh Arabic`, fallback `Amiri`, `serif`.
- **Technical metadata only:** `IBM Plex Mono`, fallback `ui-monospace`, `monospace`.

Self-host subsetted WOFF2 files. Do not make external font requests at runtime.

Reason: Satoshi feels contemporary without resembling a default developer dashboard, Noto Naskh preserves Arabic readability and harakat, and IBM Plex Mono separates provenance data from spiritual content.

### Scale

| Role | Size / line height | Weight | Use |
|---|---|---:|---|
| Page title | `28px / 36px` | 600 | Screen title only |
| Section title | `20px / 28px` | 600 | Evidence and settings sections |
| Message | `16px / 26px` | 400 | User and reflection text |
| UI label | `14px / 20px` | 600 | Buttons and field labels |
| Metadata | `12px / 18px` | 500 | Time, source, score, model status |
| Arabic | `30px / 56px` | 400 | Exact ayah text, right aligned |

Keep chat copy between 45 and 68 characters per line. Avoid all-caps labels and excessive tracking. Arabic may grow to `34px` on large screens and must never drop below `26px` on mobile.

## 5. Spacing, Shape, and Elevation

- Spacing scale: `4, 8, 12, 16, 24, 32, 48, 64px`.
- Control radius: `10px`.
- Message radius: `16px`, with one reduced corner at `6px` to clarify speaker direction.
- Evidence surface radius: `12px`.
- Pill radius is reserved for status and suggestion chips only.
- Control height: minimum `44px`.
- Standard border: `1px solid line`.
- Shadow: only the sticky composer uses `0 -8px 24px rgba(23, 58, 49, 0.06)` when content scrolls behind it.

Reason: moderate corners keep the interface warm without turning every element into a capsule; elevation marks overlap rather than decorating every surface.

## 6. Responsive App Shell

### Desktop, 1024px and wider

Use a three-zone asymmetric shell:

1. **Navigation rail:** `248px`, fixed left. Product name, New Reflection, Conversation, Knowledge, Evaluation, Settings, privacy status.
2. **Conversation:** flexible, maximum reading width `760px`. It owns the visual focus.
3. **Evidence drawer:** `320px`, optional and collapsible. It shows source detail, retrieval trace, and tafsir without narrowing the conversation below `600px`.

The conversation aligns slightly left of the remaining viewport center when the evidence drawer is closed. Do not center the entire product like a marketing hero.

### Tablet, 720px to 1023px

- Collapse navigation to a `72px` icon rail with text tooltips.
- Open evidence and settings in a right sheet.
- Preserve at least `560px` for reading where possible.

### Mobile, below 720px

- Use one column with `16px` side padding.
- Navigation opens as a modal sheet.
- Evidence expands inline below the relevant reflection, not as a horizontal card carousel.
- Composer respects safe-area insets and stays above the software keyboard.
- Message width: user maximum `86%`; assistant and evidence may use `100%`.
- No horizontal scrolling except deliberate code or metric tables on the Evaluation screen.

Reason: the asymmetry preserves conversation priority on desktop, while inline evidence avoids hidden horizontal content on mobile.

## 7. Core Components

### 7.1 App header

- Show the current conversation title and a plain-text runtime status such as `Lokal, data tetap di perangkat` or `Cloud, permintaan diproses layanan eksternal`.
- A compact `Safety: Strict` status is always visible. It is a status, not an editable toggle.
- Header actions are text plus relevant icon when space permits: `Hapus percakapan`, `Ekspor teks`, `Buka sumber`.
- Every action must execute a real behavior or not be rendered.

### 7.2 User message

- Right aligned with `accent` background and high-contrast text.
- Show message content and optional timestamp only.
- Do not show fake delivery checks, online presence, or a fabricated avatar.

### 7.3 Assistant response

One response is a semantic sequence, not a generic bubble containing everything:

1. retrieval state,
2. grounded reflection,
3. evidence thread,
4. source actions,
5. one relevant follow-up suggestion group.

Use `paper` with a `line` border. The reflection begins with `Ruang refleksi`, not `AI answer` or `bot`.

### 7.4 Quran evidence block

This is the signature component and the focal point of a completed answer.

- Header: surah name, surah and ayah number, and grounded status.
- Arabic: exact source text with `lang="ar"`, `dir="rtl"`, generous line height, and no truncation.
- Translation: show the named translation and its source version. Use `Terjemahan Kemenag` only when the stored record is actually sourced from Kemenag.
- Tafsir: collapsed by default after the first concise excerpt. `Baca tafsir lengkap` opens an accessible disclosure.
- Provenance: dataset, snapshot date, document ID, and source link where available.
- Developer mode: score, matched child IDs, parent ID, embedding model, and retrieval rank.
- Actions: `Salin ayat`, `Salin sitasi`, and `Buka sumber`. Do not include a save action until persistence exists.

The Arabic text and translation are one reading unit. Never place an action row between them.

### 7.5 Composer

- Label: `Ceritakan secukupnya`.
- Multiline field, maximum 500 characters.
- Placeholder: `Contoh: Aku cemas menghadapi ujian besok`.
- Primary action: `Kirim refleksi`.
- Enter sends; Shift+Enter inserts a line break.
- A visible character counter appears from 400 characters.
- Helper: `Qalbu adalah pendamping refleksi, bukan pengganti tenaga profesional atau fatwa.`
- Suggestion chips use actual example queries and fill the composer. They do not submit until the user confirms.

### 7.6 Status and feedback

- Loading: show sequential labels `Mencari ayat`, `Membuka konteks`, then `Menyusun refleksi`.
- Streaming: render evidence first when available, then the reflection text.
- Verifying: show `Memeriksa sitasi` until the citation validator completes.
- Success: use the small grounded status, not a celebratory animation.
- Error: state what failed and preserve the user input. Offer `Coba lagi` only when retry is possible.
- Offline model: keep evidence visible and say `Refleksi belum tersedia. Ayat dan tafsir tetap bisa dibaca.`

### 7.7 Crisis response

- Replace the normal answer region with the reviewed fixed response.
- No Quran retrieval, model copy, animation, recommendation chips, or decorative status.
- Use `role="alert"`; move focus to the response heading, not automatically to a phone call.
- Show the configured and release-verified help contact as a clear action.
- Include a second action encouraging contact with a trusted nearby person only when backed by approved copy.

Reason: calm hierarchy reduces cognitive load while keeping urgent help reachable and avoiding false automation.

## 8. Parent-Child RAG Explainer

Use the supplied five-stage diagram as an information model, not as a literal visual style.

### Desktop composition

Build one horizontal evidence thread with unequal stage widths:

1. **Sumber utuh:** a wide parent document sample.
2. **Potongan pencarian:** several compact child rows, not tiny document icons.
3. **Embedding dan tautan:** one mapping table that connects child IDs to a parent ID.
4. **Pencarian:** emphasize the matched child with the moss accent.
5. **Konteks lengkap:** expand the selected parent passage and lead into the final reflection.

Use one continuous connector rule and numbered text labels. The expanded parent stage is largest. Avoid rainbow stage colors, cartoon clip art, fake handwritten fonts, and five equal cards.

### Mobile composition

Stack stages vertically along a left evidence rail. Each stage title remains visible; supporting detail can use disclosure controls. The reading order must match the technical execution order.

### User-facing wording

- `Dokumen sumber` instead of `big text`.
- `Potongan untuk pencarian` instead of `small chunk`.
- `Tautan ke konteks` instead of `mapping`.
- `Ayat yang paling relevan` instead of `vector result`.
- `Konteks lengkap untuk refleksi` instead of `big output`.

Reason: the visual teaches why small passages improve search while complete passages protect meaning.

## 9. Screens for Stitch

### 9.1 Conversation, primary screen

Focal point: the latest Quran evidence block. Include a compact navigation rail, a real conversation thread, sequential retrieval status, sticky composer, and optional evidence drawer. Use realistic Indonesian copy, but mark changing response content as sample data.

### 9.2 Empty conversation

Focal point: the composer. Use a short welcome and three vertically varied example prompts, not an oversized hero, orb, or grid of identical cards.

### 9.3 Low-confidence result

Focal point: honest fallback copy. Say that no sufficiently relevant passage was found. Offer query reformulation examples. Do not invent a verse or display a weak match as grounded.

### 9.4 Reflection unavailable

Focal point: retrieved evidence. Keep Arabic, translation, tafsir, and provenance. Place the generator error below the evidence as a secondary operational note.

### 9.5 Crisis state

Focal point: reviewed help copy and configured contact action. Remove normal evidence and generation states.

### 9.6 Knowledge sources

Focal point: current corpus manifest. Show each real source, version, snapshot date, verse count, translation ownership, and curation status in rows. Never label Quran.com, Kaggle, or community data as Kemenag.

### 9.7 Evaluation

Focal point: the latest measured retrieval result. Use one large primary metric followed by a comparison table for hit@k, MRR, faithfulness, citation validity, crisis recall, latency, and memory. Render values only from a real evaluation artifact. Missing measurements display `Belum diukur`.

### 9.8 Settings

Focal point: privacy and runtime profile. Only show controls implemented by the application. Safety is read-only and always strict. Destructive local-data clearing requires confirmation.

## 10. Content Voice

- Indonesian first, natural and concise.
- Acknowledge emotion without claiming a diagnosis.
- Distinguish Quran text, translation, tafsir, and generated reflection through labels and typography.
- Never imply that a retrieved verse proves the user's faith, worth, diagnosis, or divine judgment.
- Never produce a fatwa or medical instruction.
- Use specific actions: `Kirim refleksi`, `Baca tafsir`, `Lihat sumber`, `Ulangi pencarian`.
- Avoid AI marketing language, urgency tricks, exclamation marks in sensitive states, and anthropomorphic claims such as `Aku selalu memahami kamu`.

## 11. Motion and Interaction

MOTION 1 means state clarity, not spectacle.

- New messages: opacity from 0 to 1 and translate Y from `4px` to `0`, `160ms` ease-out.
- Disclosure: height and opacity, maximum `180ms`.
- Press state: scale to `0.98` for `90ms` on pointer-capable devices.
- Focus: persistent `2px` accent outline with `2px` offset.
- No looping, breathing, floating, parallax, bounce, typewriter, or staggered ornament.
- With `prefers-reduced-motion: reduce`, remove transforms and transition durations.

Reason: motion confirms state changes without competing with reflective reading or increasing load on modest hardware.

## 12. Accessibility and Resilience

- Body contrast at least `4.5:1`; large text and control boundaries at least `3:1`.
- Full keyboard flow with logical tab order, Enter, Shift+Enter, Escape, and visible focus.
- Message list uses `role="log"` and `aria-live="polite"`; announce a streamed answer only after completion.
- Every disclosure exposes `aria-expanded` and references its panel.
- Arabic uses correct language and direction attributes and preserves harakat when present.
- Touch targets are at least `44 x 44px`.
- At 200% zoom, no content or controls are lost.
- Loading, empty, low-confidence, offline, error, validation-failed, and crisis states are all designed.
- Never erase a drafted message after a network error.
- Do not depend on color alone for status.

## 13. Decision Ledger

| Decision | One-line reason |
|---|---|
| Warm paper and forest ink | Creates a calm reading environment without borrowing the generic purple AI aesthetic |
| One moss accent | Gives interaction hierarchy while keeping sacred content visually dominant |
| Asymmetric app shell | Prioritizes the conversation while keeping evidence inspectable |
| Satoshi for interface | Contemporary and readable without looking like a default developer tool |
| Noto Naskh Arabic | Preserves Quran text legibility, rhythm, and harakat |
| Moderate radii | Feels humane while retaining document-like structure |
| Borders over shadows | Clarifies grouping with less visual noise and rendering cost |
| Evidence thread motif | Turns the parent-child retrieval mechanism into a product-specific visual language |
| Evidence before reflection | Lets users inspect grounding before trusting synthesis |
| Light default with working dark option | Supports the quiet manuscript identity while respecting user preference |

## 14. Anti-Patterns

- No purple-blue gradient, glow, orb, sparkle, robot, or magic icon.
- No generic centered hero with feature-card grid.
- No WhatsApp, Telegram, Notion, Vercel, or Linear imitation.
- No three equal feature cards or five equal workflow cards.
- No glassmorphism across navigation, cards, or modal surfaces.
- No oversized marketing headline inside the application.
- No decorative Arabic calligraphy, mosque silhouettes, or sacred text used as texture.
- No fake avatar, online presence, read receipt, testimonial, statistic, security claim, or source authority.
- No pills for every control.
- No dead button, placeholder link, or setting that the implementation cannot honor.
- No citations outside the retrieved evidence set.
- No labeling a translation as official unless provenance proves it.

## 15. Stitch Generation Contract

When generating screens from this file:

1. Preserve the palette, typography roles, dials, evidence hierarchy, and identity motif.
2. Generate the Conversation screen first, then all required states before secondary pages.
3. Use actual component names and Indonesian labels from this specification.
4. Keep sample content explicitly marked as sample and never fabricate performance values.
5. Represent parent-child retrieval with the evidence thread described in section 8.
6. Make every visible control map to a defined behavior.
7. Produce both desktop and mobile frames for Conversation, low-confidence, error, and crisis states.
8. Treat Arabic, translation, tafsir, and model reflection as four distinct content types.

## 16. Design Gate

- **PASS, direction:** Design Read and ENERGY 1 / RHYTHM 2 / MOTION 1 are explicit.
- **PASS, focal point:** each required screen names one dominant element.
- **PASS, palette:** two core surface families, one forest ink family, and one moss accent; semantic colors are state-only.
- **PASS, typography:** every family has a product and readability reason.
- **PASS, identity:** the evidence thread is specific to parent-child Quran retrieval.
- **PASS, hierarchy:** evidence outranks generated reflection, and the parent context outranks child markers.
- **PASS, anti-slop:** no gradient, glow, orb, glass dashboard, generic hero grid, or cloned product identity.
- **PASS, honest content:** metrics, authority, provenance, and runtime status must be data-backed.
- **PASS, resilience specification:** empty, loading, low-confidence, offline, error, validation, and crisis states are defined.
- **PASS, interaction specification:** every named action has a required behavior; unimplemented actions must not render.
- **PASS, accessibility specification:** keyboard, focus, contrast, RTL, live regions, reduced motion, zoom, and touch targets are defined.
- **NOT RUNTIME-TESTED:** this deliverable is a design specification. Browser control click-through belongs to the implementation task.
