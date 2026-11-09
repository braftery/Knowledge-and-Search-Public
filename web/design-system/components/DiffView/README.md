# DiffView

Shows what changed between two wordings: inline for a revision, two columns for a conflict.

- Removed words: `diff-del-ink` on `diff-del-bg`, struck through. Added words: `diff-add-ink` on `diff-add-bg`, underlined. The marks never rely on colour alone.
- Always show the legend above the diff.
- Diff by word, not by character. Keep the text at body size, 28px line height, capped at 72ch.
- Conflict mode: two columns of equal width, "Kept" and "Retired" headings with status badges, and the AI's reason above both.
- On the member site, highlight only the added words of a new version, with no strikethrough text.
- Consumer provides: the old text, the new text, and the mode (inline, columns, added-only).
