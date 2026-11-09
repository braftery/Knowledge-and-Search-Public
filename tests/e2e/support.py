"""Shared waits for the Streamlit demo. Each click reruns the script."""

from __future__ import annotations

import re

FORBIDDEN = ("No cached result", "Not cached", "No saved answer")

HEADINGS = {
    0: "Today: one disclaimer, three wordings",
    1: "AI turns a script into knowledge units",
    2: "AI finds copies and conflicts",
    3: "Legal approves units, not documents",
    4: "One question, two roles, scoped answers",
    5: "Author once, every channel updates",
    6: "Unanswered questions become the next units",
    7: "When the source changes, the unit is flagged",
    8: "We measure retrieval before we trust it",
}

EXPLORE_PAGES = {
    "Knowledge Ops author": ["My work", "Library", "Source documents", "Copies and conflicts"],
    "Legal approver": ["Review inbox", "Revise wording", "Version history"],
    "Pharmacy advocate": ["Agent desktop", "What I can read"],
    "Insurance advocate": ["Agent desktop", "What I can read"],
    "Member": ["App chat", "Website", "Phone line"],
    "Knowledge owner": ["Insights", "Gaps", "Drift", "Quality"],
    "Channel and AI team": ["Quick start", "API reference", "Change events"],
}


def open_demo(page, url: str) -> None:
    page.goto(url, wait_until="domcontentloaded")
    page.locator("h1.screen-title", has_text=HEADINGS[0]).wait_for()
    assert_no_exception(page)


def assert_no_exception(page) -> None:
    exceptions = page.locator('[data-testid="stException"]')
    if exceptions.count():
        raise AssertionError(exceptions.first.inner_text()[:2500])
    body = page.locator("body").inner_text()
    if "Traceback (most recent call last)" in body:
        raise AssertionError(body[:2500])


def assert_saved_answers(page) -> None:
    html = page.content()
    for phrase in FORBIDDEN:
        if phrase in html:
            raise AssertionError(f"Page contains {phrase!r}")


def activity_text(page) -> str:
    return page.locator(".activity-line").text_content() or ""


def wait_for_activity_change(page, previous: str) -> None:
    page.wait_for_function(
        """(prev) => {
            const line = document.querySelector('.activity-line');
            return line && line.textContent && line.textContent !== prev;
        }""",
        arg=previous,
    )
    assert_no_exception(page)


def heading(page) -> str:
    return page.locator("h1.screen-title").inner_text().strip()


def click_button(page, name: str) -> None:
    page.get_by_role("button", name=name, exact=True).click()


def click_pattern(page, pattern: str) -> None:
    page.get_by_role("button", name=re.compile(pattern)).click()


def wait_heading(page, number: int) -> None:
    page.locator("h1.screen-title", has_text=HEADINGS[number]).wait_for()
    assert_no_exception(page)


def wait_text(page, text: str) -> None:
    page.get_by_text(text).first.wait_for()
    assert_no_exception(page)


def wait_content(page, text: str) -> None:
    """Wait until the text is in the page, including a tab panel that is not selected yet."""
    page.wait_for_function(
        """(needle) => (document.body.textContent || '').includes(needle)""",
        arg=text,
    )
    assert_no_exception(page)


def go_to_step(page, number: int, name: str) -> None:
    page.get_by_role("button", name=re.compile(rf"^{number}\s+{re.escape(name)}$")).click()
    wait_heading(page, number)


def choose_view(page, label: str) -> None:
    sidebar = page.locator('[data-testid="stSidebar"]')
    sidebar.locator('[data-testid="stSelectbox"]').first.click()
    option = page.get_by_role("option", name=label, exact=True)
    option.wait_for()
    option.click()
    if label == "Guided demo":
        page.locator(".chip", has_text="Step ").first.wait_for()
        return
    role = label
    page.locator(".persona", has_text=f"You are: {role}").wait_for()
    page.locator(".chip", has_text="Explore mode").wait_for()
    assert_no_exception(page)


def open_tab(page, pattern: str) -> None:
    tab = page.get_by_role("tab", name=re.compile(pattern))
    tab.click()
    page.get_by_role("tab", name=re.compile(pattern), selected=True).wait_for()
    assert_no_exception(page)


def sidebar_button(page, name: str):
    return page.locator('[data-testid="stSidebar"]').get_by_role("button", name=name, exact=True)
