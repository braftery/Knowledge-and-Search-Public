# Interaction

How every surface behaves over time. These rules come from the interaction-design skill, with the forms, buttons and layout rules of the ux-ui-design skill where they meet behaviour.

## Responsiveness

- Every press responds at once. A button shows its pressed state on pointer down and acts on pointer up.
- Saved answers come back instantly. Do not add a fake delay to make the AI look like it is thinking.
- Live AI calls show progress inside the control that started them: the button keeps its label, adds a spinner, and reads "Searching…" with the single ellipsis character.
- Spinners and skeletons wait 200ms before they appear and then stay at least 400ms, so fast responses never flicker.
- Skeletons match the final layout exactly, so nothing jumps when content arrives.

## States: design all of them

Every list, panel and page has a designed loading, empty, error and success state. Never render a blank area.

- **Empty** answers three questions: why it is empty, what the person can do, and a direct action. Example: "Nothing waiting for Legal. New items appear here when an author sends them. Open the library".
- **No approved answer** is a first-class state, not an error. Say there is no approved answer, give the next steps, and say the question was logged for the knowledge team.
- **Error** says what happened and how to fix it, in plain words, with no blame and no "oops". Keep everything the person typed.
- **Success** is a toast in the corner and the changed item visibly updated in place.

## Undo, never "Are you sure?"

- Every action in the prototype is reversible, so none asks for confirmation. Approve, send back, resolve, publish, reset and apply all act immediately and show a toast: what happened, then **Undo**.
- The toast stays 8 seconds, pauses while hovered or focused, and is announced with `aria-live="polite"`.
- Undo restores the exact prior state, including which item was selected.
- A confirm dialog is reserved for an action that cannot be undone. The prototype has none.

## Forms

- Labels on top, tight to the field. Hints sit under the label and above the field. Mark optional fields "(optional)".
- Validate on submit, not while typing. Put the error under the label and above the field, red with an icon and a 2px border, and move focus to the first error. The message names the problem and the fix: "Add a reason. Legal's reason is sent to the author with the unit."
- Do not disable a submit button to signal missing input. Leave it enabled and validate.
- Enter submits a single-field form (search, chat). In a multi-line note, Cmd or Ctrl plus Enter submits.
- Never block paste. Trim values. Search fields use `autocomplete="off"` and a placeholder that ends with an ellipsis, such as "Search approved answers…".

## Focus and keyboard

- Everything works by keyboard, following WAI-ARIA patterns: tabs with arrow keys, dialogs and popovers trap focus and return it on close, Escape closes.
- One focus style everywhere: a 2px solid `focus-ring` with a 2px gap. Use `:focus-visible`. A sticky bar never covers the focused element.
- After an action moves to the next item (Legal inbox, My work), focus moves to the new item's title so a keyboard user keeps their place.
- Autofocus the single primary input on desktop (agent panel search, chat input once the panel opens). Never autofocus on mobile.

## Modals

- Use a modal only to stop work that would otherwise be lost. Errors on a form appear on the page, next to the field.
- The member chat is a non-modal panel: the site stays usable behind it, there is no scrim, and Escape or the close button dismisses it and returns focus to the launcher.
- One overlay at a time. Never stack a popover on a dialog.

## URL holds the state

Deep-link every view: the selected role, the guided demo step, the selected tab, the selected item in a queue and any filters. Refresh, share and Back must land in the same place. Navigation uses real links.

## Motion

- Animate only to show cause and effect: the chat panel growing from its launcher, a new item sliding into a queue, the changed words in a revision fading in.
- Never animate keyboard-initiated or high-frequency actions: moving through a queue, switching tabs, typing.
- Durations 120 to 200ms with ease-out for small changes, 240ms for the chat panel. Springs, if used, start at full damping (no overshoot).
- Animate `transform` and `opacity` only. Never `transition: all`.
- Honour `prefers-reduced-motion`: replace movement with a fade or nothing.

## Touch and mobile

- Targets 48px, never under 44px on touch. At least 8px between adjacent targets.
- Put the chat input and send button where thumbs reach, and pad sticky bars with `env(safe-area-inset-bottom)`.
- Mobile inputs use 16px text or larger so iOS does not zoom. Never disable zoom.
