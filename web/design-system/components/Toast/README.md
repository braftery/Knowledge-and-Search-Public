# Toast

Confirms an action and offers Undo. Every action in the prototype ends with one.

- `surface-raised`, `shadow-2`, `radius-md`, bottom right, 8 seconds, paused while hovered or focused.
- Text is what happened, in the past tense, naming the item. Then a tertiary "Undo".
- Announced politely (`role="status"`). One toast at a time; a new one replaces the old.
- Errors do not use toasts. They appear next to what failed.
- Consumer provides: the message and the undo handler.
