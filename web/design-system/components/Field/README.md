# Field

A label, an optional hint, an optional error and one control, in a single column.

- Label on top, tight to the field (`space-1`). Hint under the label, above the field, in `ink-muted`. Mark optional fields "(optional)" in `ink-muted`; mark required fields only when a form mixes both.
- Field width matches the expected input; cap at 480px. Inputs are `surface-raised` with a 1px `line-strong` border, height `size-target`.
- Placeholders show an example and end with "…"; they are never the only label, except in a search field that also has an accessible name.
- Validate on submit. The error goes under the label and above the control: `blocked` text in 600 weight with the alert icon, a 2px `blocked` border and a `blocked-soft` fill. Set `aria-invalid` and `aria-describedby`. Move focus to the first error. Keep what was typed.
- Error copy names the problem and the fix, without blame.
- Consumer provides: label, id, value, hint, error message, and whether it is optional.
