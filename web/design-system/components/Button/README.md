# Button

Three weights, one primary per view. **Primary** is the `action` fill with `on-action` text, used once for the thing the screen is for. **Secondary** is a `surface-raised` button with a 2px `action` border and `action` text, for equal or lesser actions. **Tertiary** is underlined `action` text, for the least important actions and navigation-like actions.

- Labels are a verb plus a noun in sentence case and make sense alone: "Approve and publish", not "OK".
- Height `size-target` (48px). `size-target-compact` (40px) only in dense tool toolbars. At least `space-2` between buttons, `space-4` by default.
- Order most to least important, left to right, placed next to the content they act on.
- While a request is in flight: keep the label, add the spinner, end the label with "…", set `aria-busy`. Do not disable the button before submission to signal missing input; validate on submit instead.
- The member site uses the same variants with `radius-member`.
- Do not use a grey filled button, a second solid fill, or a red trigger. Nothing in the prototype is irreversible, so there is no destructive button.
- Consumer provides: label, variant, an onClick or href (use a link for navigation), and the busy state.
