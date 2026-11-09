# End-to-end tests

Playwright drives the Streamlit demo in Chromium at 1280 by 800. The tests start the app themselves, with no API key, so every answer comes from the saved fixtures.

From the repository root, with the same Python that has the app dependencies:

```bash
pip install -r requirements.txt
pip install playwright==1.58.0 pytest==8.4.2
playwright install chromium
HARBOR_E2E=1 pytest tests/e2e
```

What the tests cover:

- Short demo. Jump to short demo, approve the three units on step 3, then step 4 search answers both roles.
- Full path. Steps 0 through 8, with no exception and none of the text "No cached result", "Not cached", or "No saved answer".
- Explore. Every entry in the View dropdown opens every page in that workspace, with no exception.
- Round trip. Switching to Explore and back keeps the guided demo's step and the approvals already made.

The plain `pytest` command skips these tests unless `HARBOR_E2E=1` is set. If Playwright cannot find its browser, set `HARBOR_CHROMIUM` to a Chromium executable path.

The server log from a failed run is written to `/tmp/harbor-e2e-streamlit.log`.
