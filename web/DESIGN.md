# Design system for the web front end

The Harbor Health design system lives in `web/design-system/`. It is binding for everything under `web/`. Implement it; do not invent values.

Read in this order:

1. `design-system/README.md`: principles, colour, type, space, radius, depth, icons, brand mark.
2. `design-system/1-Interaction.md`: states, undo, forms, focus, modals, motion, touch.
3. `design-system/2-Writing.md`: house rules, button and message copy, member voice, glossary.
4. `design-system/3-Surfaces.md`: the layout, regions and widths of every surface.
5. `design-system/4-Building-with-shadcn.md`: how shadcn/ui maps onto these tokens, and the variant rules.
6. `design-system/components/<Name>/README.md`: rules for each component.

Use these files directly:

- `design-system/tokens.json` is the source of every value. `design-system/tokens.css` is generated from it: import it once at the app root, and map shadcn's variables to it as `4-Building-with-shadcn.md` shows.
- `design-system/components.css` and each `components/<Name>/preview.html` show the exact intended rendering of the components shadcn does not provide. Rebuild them as React components and match them.
- `design-system/reference/<Name>.png` is a screenshot of each preview. Compare your screenshots against these during the visual QA loop.
- `design-system/index.html` shows every preview on one page. Serve the folder locally to view it (for example, `python3 -m http.server` inside `web/design-system`).

The two themes are `tools` (internal tools) and `member` (the Harbor Health public site, app and phone line). Set `data-theme` on the root element of each surface.

If a screen seems to need something the system does not define, use the closest existing token or component and record the gap in `WEB_BUILD_LOG.md`. Do not add new colours, sizes or fonts.

A browsable copy of the same system is published as a private claude.ai artifact for the owner to review. The files in this folder are the source of truth for the build.
