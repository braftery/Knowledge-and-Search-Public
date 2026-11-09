# ChatPanel

The member chat on the Harbor Health website and app. Answers with approved member wording only.

- `size-chat` wide (full screen under 640px), up to 640px tall, `surface-raised`, `radius-member`, `shadow-3`, no scrim. The site stays usable behind it.
- Header: "Ask Harbor" in `member-h3` and a labelled close button. Footer: the input and Send, the panel's one primary. Enter sends.
- Bot bubbles on `surface-sunken`, the member's own on `action-soft`, both `ink` text at 18px. The bot's answer ends with a member Citation.
- Clarify: when the question is close to several topics, ask one short question and show two to four topic chips.
- Feedback: "Did that answer help?" with Yes and No. No leads to an offer to talk to a member advocate.
- Hand-off: "Talk to a member advocate" becomes the primary button, replacing Send's emphasis.
- Privacy line under the input, always visible on the public site: "Please don't include personal details like your member ID or date of birth. For questions about your own claims, sign in." In `member-meta`, `ink-muted`. The public chat answers general plan questions only (HIPAA_REVIEW.md).
- Never show unit IDs, versions or internal names. Never generate wording.
- Consumer provides: the messages, topic chips, and the send, feedback and hand-off handlers.
