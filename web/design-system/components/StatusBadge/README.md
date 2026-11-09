# StatusBadge

The state of a unit or an item, always as an icon plus a word on a tint.

- Five variants: `approved` (check-circle), `review` (clock), `blocked` (triangle-alert), `stale` (refresh-cw) and `neutral` (no icon, for draft or retired). Text in the status colour on its `-soft` tint, `radius-sm`, 16px 600.
- The word carries the meaning; the colour and icon reinforce it. Never show a coloured dot alone.
- Use the glossary's words: Approved, Waiting for Legal, Waiting for your approval, Sent back, Conflict, Source changed, Past review date, Draft, Retired.
- A badge is not a button and never looks like one: no border, no hover, no pointer.
- Consumer provides: variant and the word.
