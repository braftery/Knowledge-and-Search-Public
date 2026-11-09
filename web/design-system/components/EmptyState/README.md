# EmptyState

Every list, queue and search result has one. It answers why it is empty, what the person can do, and gives a direct action.

- `surface-raised` with a 1px dashed `line-strong` border, `space-6` padding, 520px wide at most.
- Heading in `tools-title-sm` states the fact. One line in `ink-muted` says why or what happened. Optional numbered next steps. One action, secondary or tertiary.
- "No approved answer" is an empty state, never an error, and never a guess.
- Do not show a blank area, a lone spinner, or "No results".
- Consumer provides: heading, reason, optional steps, and one action.
