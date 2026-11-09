# DecisionMarker

Shows who made a call: the AI or a person. It makes the human-in-the-loop design visible on screen without narration.

- **AI proposed**: a dashed `line-strong` outline, `ink-muted` text and the sparkles icon. Put it on anything the model produced that no person has confirmed yet: extracted units, suggested tags and audience, duplicate labels, gap drafts, drift fixes, proposed retirements.
- **Needs a person**: `review` text with the clock icon, naming the role that must act. Use it where the flow is waiting on a human gate.
- **Human decision**: `ink` text with a person icon in `approved`, followed by the role, the person's name when known, and the date and time in `ink-muted`. Then the decision and its reason. Use it on every approval, send back, conflict decision, gap decision, drift approval and resolution.
- Once a person confirms an AI proposal, replace "AI proposed" with "Human decision". Never show both on the same field.
- The dashed outline keeps "AI proposed" from reading as a button or a status. It has no hover and no pointer.
- Never use it on member surfaces. Members see only approved wording and its citation.
- Consumer provides: the kind (ai, pending, human), the role, the name, the timestamp, and the decision text.
