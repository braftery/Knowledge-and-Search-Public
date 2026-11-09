# Surfaces

Each person sees the product where they actually work. These are the layouts, regions and widths for every surface. Build each one as a credible, original product in its context. Never copy a real vendor's UI.

## Member: Harbor Health website (theme `member`)

- **Header**, 72px, `surface-raised` with a `line` bottom border: wordmark at left; visible navigation (Find care, Drug costs, Plans, Member help); "Sign in" as a secondary button at right. Navigation is never hidden behind a menu at desktop width. The current page is marked with a 3px `action` underline and `ink` text.
- **Page**: the help article "Estimate a drug price". Breadcrumb, `member-display` heading, `member-body-lg` lead, then two columns inside `size-content`: article (max 72ch) and a 320px "Get help" card with the phone number and chat entry.
- **Footer**: `surface-inverse`, four link columns in `ink-inverse-muted`, "Illustrative site. Harbor Health is fictional." on the last line.
- **Chat launcher**: fixed 24px from the bottom and right edges, pill, `action` fill, chat icon plus "Ask Harbor". It is a labelled button, never an icon alone.
- **Chat panel**: opens from the launcher (grows from bottom right), `size-chat` wide, up to 640px tall, `shadow-3`, no scrim. Header with "Ask Harbor" and a close button. Body: greeting, topic chips, messages. Footer: input and Send. Under 640px wide it becomes a full-screen sheet with a close button at top left.
- **Answer bubble**: approved member wording in `member-body`, then the citation in `member-meta`. Then "Did that answer help?" with Yes and No as secondary buttons. A clarifying question shows two to four topic chips. A hand-off shows "Talk to a member advocate" as a primary button, the only one in the panel.

## Member: mobile app (theme `member`)

- A device frame 390 by 844 on `surface-sunken`, `shadow-4`. Status bar, app header with the wordmark, bottom navigation of four labelled items (Home, Care, Costs, Help) with the current one marked.
- The Help tab is the same chat, full height, input pinned above the navigation with safe-area padding.

## Member: phone line (theme `member`)

- A call transcript card: caller and "Harbor Health automated line" turns, with times. The line reads the same approved wording, then "Press 0 to talk to a member advocate". Labelled "Transcript of an automated call. Illustrative."

## Advocates: agent desktop (theme `tools`)

- **Top bar** (`size-topbar`): product name "Harbor Health Contact Center", queue status, the advocate's name.
- **Call strip**, 64px: caller name, member ID (fictional), plan, verification status as a badge (approved "Verified" or review "Not verified"), call timer in tabular figures, Hold and End call as secondary buttons.
- **Center**: caller profile and interaction notes, fluid width.
- **Knowledge panel** (`size-panel`, docked right, full height, `surface-raised`, left `line` border): header with the search field (`size-target-compact`, Enter submits). Below it, "Suggested for this call" with two or three answer cards for the call reason. A search replaces the suggestions with results and a tertiary "Back to suggestions" link.
- **Answer card**: question in `ink-muted`, then a verbatim block if the unit requires word-for-word reading, else the advocate wording. Then the citation, then Copy wording (secondary) and Flag this answer (tertiary). No primary action in the panel: the advocate's primary task is the call.
- In the guided demo, step 4 shows two desktops side by side (Pharmacy and Insurance), each at 640px with the panel collapsed to 360px.

## Legal approver: email, then the review page (theme `tools`)

- **Email client**: an original, generic client in a `radius-lg` window with `shadow-4`: folder list (160px), message list (320px), reading pane. The message from "Single Source" says how many items wait and has one primary button, "Start review".
- **Review page**: top bar with "Legal review" and "Item 2 of 5". Below it, a sticky decision bar: Approve and publish (primary), Send back to author (secondary). Directly under it: the verbatim check and "If you approve this unit" (who sees it, which channels, effective date). Then the wording and the highlighted source passage side by side.
- **Send back** reveals a required reason field in place, never a modal.
- **Conflicts** show two columns, the kept wording and the retired wording, with the AI's reason above both and a diff legend.
- After each decision the next item loads and focus moves to its title. The last decision ends at an empty state: "All caught up. New items arrive by email."

## Knowledge Ops author: Single Source Studio (theme `tools`)

- **Left rail** (`size-rail`): wordmark plus "Single Source", navigation with counts: My work, Library, Copies and conflicts, Gaps, Source changes. Labels always visible; the current item uses `action-soft` with `ink` text.
- **My work** is master and detail: queue (`size-queue`) grouped under `tools-overline` headings (Sent back by Legal, Waiting for your approval, Flagged by advocates and channels, Source changed, Drafts assigned), the item in the center, the source document on the right (360px, collapsible).
- **Library**: filterable table (type, knowledge base, status, audience, review date), version history in the detail pane with diffs between versions.

## Knowledge owner: insights (theme `tools`)

- Weekly digest sentence at the top. A row of metric tiles, each with its denominator ("18 of 20 right answer first"). Top unanswered questions as ranked, sorted bars in `ink-muted` with counts. A "Needs attention" column for source changes and review dates. Every item links to where it is acted on.
- No gauges and no pie charts. Bars are sorted.

## Channel and AI team: developer docs (theme `tools`)

- A documentation site: left navigation (Quick start, API reference, Change events, Product backlog), content at 72ch, code blocks in `code` on `surface-sunken` with a Copy button. "Try it" sends a real request to the prototype API and shows the real response. Marked "Mock portal" in the header.

## Guided demo mode

- **Presenter bar** (`size-presenter`, `surface-inverse`) at the very top, outside the product: step number and title, Back, Next (the only primary), Jump to short demo, Reset, and Undo when available. It is visibly not part of any product.
- Below it, the real surface for the step's persona at full size. Steps that compare two views (4 and 5) show them side by side inside `shadow-4` frames labelled with the persona.
- Talking points live in a collapsible presenter notes drawer, closed by default, never on the product surface itself.

## Launcher

- One page: "Harbor Health knowledge prototype", a short line on what it shows, then "Start the guided demo" (primary) and "Explore as" with seven role cards, each naming the role, where they work, and their first task. Switching roles keeps the guided demo's place.
