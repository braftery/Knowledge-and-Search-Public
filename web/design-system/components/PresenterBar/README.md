# PresenterBar

The guided demo's controls, at the very top of the window and visibly outside every product surface.

- `surface-inverse`, `size-presenter` tall, `ink-inverse` text. On this bar the primary button is an `ink-inverse` fill with `surface-inverse` text, so it stays the one primary.
- Order: step counter, step title, Back (tertiary), Jump to short demo and Reset (secondary), Undo when available, Next (primary).
- Reset acts immediately and offers Undo in a toast.
- Keyboard: Left and Right arrows go Back and Next only when focus is not in a field.
- Consumer provides: step number, total, title, and the handlers.
