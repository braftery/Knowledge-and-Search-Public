# AnswerCard

One approved answer in the agent desktop knowledge panel.

- Order: the question in `ink-muted`, the wording (a VerbatimBlock if required, else body text), the Citation, then actions.
- Actions: Copy wording (secondary, compact) and Flag this answer (tertiary). No primary button in the panel; the call is the advocate's primary task.
- Copy confirms with a toast "Copied the approved wording". Flag opens a small popover with four reasons as radio buttons and an optional note.
- 400px wide in the panel. `surface-raised`, 1px `line` border, `space-4` padding, `space-3` between parts.
- Consumer provides: question, unit wording, verbatim flag, citation, and the flag handler.
