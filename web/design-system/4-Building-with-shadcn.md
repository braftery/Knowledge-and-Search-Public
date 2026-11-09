# Building with shadcn

Build on shadcn/ui (Radix primitives, Tailwind). Its components carry the accessibility. This system supplies the theme, the variants and the components shadcn does not have.

## Theme variables

Map shadcn's CSS variables to these tokens, once per theme. Wrap internal tools in `data-theme="tools"` and the member site in `data-theme="member"`.

| shadcn variable | Token |
| --- | --- |
| `--background` | `surface` |
| `--foreground` | `ink` |
| `--card`, `--popover` | `surface-raised` |
| `--card-foreground`, `--popover-foreground` | `ink` |
| `--primary` | `action` |
| `--primary-foreground` | `on-action` |
| `--secondary` | `surface-raised` (used only as the secondary button background) |
| `--secondary-foreground` | `action` |
| `--muted` | `surface-sunken` |
| `--muted-foreground` | `ink-muted` |
| `--accent` | `action-soft` |
| `--accent-foreground` | `ink` |
| `--destructive` | `blocked` |
| `--border` | `line` |
| `--input` | `line-strong` |
| `--ring` | `focus-ring` |
| `--radius` | `radius-md` (tools), `radius-member` (member) |

## Variant rules

- **Button**: use `default` for primary, `outline` restyled with an `action` border and `action` text for secondary, and `link` for tertiary. Do not use the stock `secondary` (grey fill reads as disabled) or `ghost` for labelled actions. `destructive` is unused: nothing in the prototype is irreversible.
- **Badge**: replace the stock variants with the five status variants (approved, review, blocked, stale, neutral), each with its icon and word.
- **Tabs**: underline style (3px `action` bar under the selected tab), not the stock pill segment. Counts sit in a neutral count chip.
- **Toast**: use Sonner through shadcn. Success toasts carry an Undo action and the check icon in `approved`.
- **Dialog**: rarely needed. Never for confirmations or form errors.
- **Sidebar, Table, Input, Textarea, Popover, Tooltip, Skeleton, Command**: use as shipped, themed by the variables above. Keep tooltips for supplementary hints only.

## Components to build from shadcn parts

Diff view, verbatim block, citation line, answer card, no-answer state, empty state, metric tile, ranked bars, presenter bar, chat launcher, chat panel and bubbles, call strip, email client window. Each has a card in Components with its preview and rules. Match the preview's spacing, type and colour exactly.

## Do not

- Do not ship the stock neutral theme. It is the most recognisable "AI-built app" look.
- Do not add colours outside `tokens.json`. If something seems to need one, it needs a status or a hierarchy fix instead.
- Do not restyle a shadcn component beyond these variables and variant rules without noting why in the build log.
