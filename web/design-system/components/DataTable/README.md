# DataTable

Rows of units or items in internal tools (Library, backlog).

- `surface-raised` with `shadow-1`. Headers in `tools-label` over a `line-strong` rule; rows divided by `line`. Cell padding `space-3`.
- Left-align text, right-align numbers and dates with tabular figures. Unit IDs in `code` style, `ink-muted`, under the title.
- The selected row uses `action-soft`. The whole row is a link to the detail.
- Long text wraps; it never clips. Over 50 rows, virtualize.
- Consumer provides: columns, rows, the selected id, and a sort.
