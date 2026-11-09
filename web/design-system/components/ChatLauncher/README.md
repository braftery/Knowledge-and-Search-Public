# ChatLauncher

Opens the member chat panel from any page of the Harbor Health site.

- Pill, `action` fill, `on-action` text, `shadow-3`, at least 56px tall, fixed 24px from the bottom and right edges, clear of the safe area.
- Always the chat icon plus the words "Ask Harbor". Never an icon alone.
- Opening grows the panel from the launcher's corner in 240ms. Focus moves to the chat input. Closing returns focus to the launcher.
- Consumer provides: the open state and the toggle handler.
