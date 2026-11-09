Harbor Health is a fictional health plan. This system covers two looks under one brand. **Internal tools** are dense, calm and enterprise: Single Source Studio, the Legal review page, the agent desktop, insights, the developer docs and the presenter bar. The **member site** is warm and consumer-facing: the public website, the chat widget, the mobile app and the phone line transcript. Each look is a colour theme (`tools`, `member`). Set `data-theme` on the root of a surface and every token follows.

Every figure shown with this system is illustrative. No surface may imitate a real company's logo, product UI or brand.

The rules come from two sources, applied here with tokens: the ux-ui-design skill (Refactoring UI and Practical UI) and the interaction-design skill (Vercel guidelines, Rauno Freiberg, Apple's fluid interfaces talk, NN/g). The sections **Interaction**, **Writing** and **Surfaces** carry the rules that tokens cannot hold. **Building with shadcn** maps this system onto shadcn/ui.

## Principles

1. **The approved wording is the product.** The one thing every surface must make obvious is which words are approved, by whom, and what version. Verbatim text, citations and status get the strongest treatment. Chrome stays quiet.
2. **One primary action per view.** It is the only `action` fill on the screen. Everything else is secondary (outlined) or tertiary (underlined link).
3. **Hierarchy from weight and colour, then size.** Two weights only: 400 and 600. Secondary text is `ink-muted` at the same size, not smaller.
4. **Meaning never rides on colour alone.** Every status has a word and an icon. Every diff mark has a strikethrough or an underline.
5. **Undo, not confirm.** Every action in the prototype can be reversed, so none asks "Are you sure?". Each shows a toast with Undo.
6. **Look like where people actually are.** A member sees a health plan website. An advocate sees an agent desktop. Legal starts in an email. The design system serves those contexts; it never turns them into one generic app.

## Colour

One interactive colour per look, `action`: a calm blue in tools, a deep teal on the member site. It marks what is clickable: primary fills, secondary borders and text, links, the selected tab, and the focus ring. Never use `action` on a heading, an icon that does nothing, a chart bar or decoration.

- Text: `ink` for headings and primary text, `ink-muted` for secondary text and metadata. Both pass 4.5:1 on `surface`, `surface-raised` and `surface-sunken` in both themes. `ink` also passes on every `-soft` tint, so a badge or banner can hold body text.
- Surfaces: `surface` is the page, `surface-raised` holds cards, panels and inputs, `surface-sunken` holds wells, code and neutral badges. `surface-inverse` is for the presenter bar and the member footer only, with `ink-inverse` and `ink-inverse-muted` text.
- Borders: `line` for decorative dividers. `line-strong` for anything that defines a control (input, checkbox, table frame); it holds 3:1 on every surface. Prefer spacing or a background change over a border.
- Status: four states, each a text colour plus a `-soft` background. `approved` (green, check icon), `review` (amber, clock icon: waiting for a person), `blocked` (red, alert icon: conflict, send back, error), `stale` (violet, refresh icon: source changed or past review date). Each status text colour passes 4.5:1 on its tint and on both surfaces. Approved and blocked are close in lightness, so the word and icon are mandatory: a state shown by colour alone is a defect.
- Diff: `diff-del-ink` on `diff-del-bg` with strikethrough for removed words, `diff-add-ink` on `diff-add-bg` with underline for added words. Every diff carries a legend.
- `highlight-bg` marks the source span a unit came from. `overlay` is the scrim behind a dialog.

## Type

Source Sans 3 for all UI text in both looks. Source Serif 4 for member headings only (`member-display`, `member-h2`, `member-h3`), which gives the public site warmth without changing the body face. Source Code Pro for code and unit IDs. Self-host all three with `@fontsource` packages; no font CDN at runtime.

- Floor: no sentence below 16px. The one exception is `tools-overline`, 13px uppercase, bold and tracked, for two-to-five-word group labels.
- Tools use `tools-body` (16/24) for running text and `tools-meta` (16/22, `ink-muted`) for metadata. Page title `tools-title-lg`, item title `tools-title`, section heading `tools-title-sm`.
- The member site uses `member-body` (18/28) for running text and chat, `member-body-lg` for the hero lead only. Long help text stays at 18px or larger.
- Line length: cap running text at `size-measure` (72ch). Left-align all running text. Right-align numbers in tables and use tabular figures.
- Sentence case everywhere, including buttons, tabs and headings.

## Space, size and layout

- Spacing steps: `space-1` 4, `space-2` 8, `space-3` 12, `space-4` 16, `space-6` 24, `space-8` 32, `space-12` 48, `space-16` 64, `space-24` 96. Pick from the scale only. More space around a group than inside it. When unsure, take the next step up.
- Tools pad cards and panels with `space-4` and separate page sections with `space-8`. The member site pads cards with `space-6` and separates sections with `space-12`.
- Targets: `size-target` (48px) by default. `size-target-compact` (40px) only for dense tool toolbars and the panel header search. Floors: 24px desktop, 44px on touch.
- Fixed regions: `size-topbar` 56, `size-presenter` 48, `size-rail` 240, `size-queue` 360, `size-panel` 400, `size-chat` 400, `size-content` 1200. A fixed sidebar with a fluid main area; a 12-column grid only for main containers.
- Nothing important below the fold at 1280 by 800. Long text and long numbers reflow; they never clip.

## Radius and depth

- Tools: `radius-sm` (4) for badges, inputs and diff marks, `radius-md` (6) for buttons, cards, panels and toasts, `radius-lg` (10) for dialogs and the email client window.
- Member: `radius-member` (12) for cards, inputs, buttons and the chat panel, `radius-pill` for the chat launcher, topic chips and bubble ends. Never use pills in tools.
- Elevation: `shadow-1` raised cards, `shadow-2` popovers and toasts, `shadow-3` dialogs and the chat panel, `shadow-4` device frames and the email window in the guided demo. Shadows are tinted with `ink`. Prefer elevation or a background change to a border.
- Avoid cards with a coloured left border, gradients, glass effects and emoji. These are common AI-made tropes and weaken hierarchy.

## Iconography

Lucide icons (the shadcn/ui default), 18px in text and 16px in badges, stroke 2, in `currentColor`. Fixed meanings, used the same way on every surface: check-circle (approved), clock (review), triangle-alert (blocked), refresh-cw (stale), lock (verbatim, word for word), file-text (citation), copy (copy wording), flag (flag this answer), undo-2 (undo), message-circle (chat), sparkles (AI proposed, internal tools only), user (human decision). An icon that carries meaning has a visible label or an accessible name. Icons never look like buttons unless they are buttons.

## Brand mark

There is no logo. Set "Harbor Health" as a wordmark in Source Serif 4 at 600, in `ink` on light surfaces and `ink-inverse` on `surface-inverse`. Internal tools follow it with the product name in Source Sans 3 at 400 in `ink-muted` ("Harbor Health  Single Source"). Do not draw a symbol.
