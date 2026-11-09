"""Walk steps 0 to 8. Saved answers cover every click on this path."""

import re

from tests.e2e.support import (
    assert_no_exception,
    assert_saved_answers,
    click_button,
    click_pattern,
    open_demo,
    open_tab,
    wait_content,
    wait_heading,
    wait_text,
)


def _check(page) -> None:
    assert_no_exception(page)
    assert_saved_answers(page)


def _next(page, number: int) -> None:
    click_pattern(page, r"^Next:")
    wait_heading(page, number)
    _check(page)


def test_full_path_steps_zero_through_eight(page, app_url):
    open_demo(page, app_url)
    _check(page)

    click_button(page, "Run today's search")
    wait_text(page, "Which wording is current")
    _check(page)
    _next(page, 1)

    click_button(page, "Extract units with AI")
    wait_text(page, "Confirm tags and audience")
    _check(page)
    click_button(page, "Confirm tags and audience")
    page.get_by_role("button", name=re.compile(r"^Next:")).wait_for()
    _check(page)
    _next(page, 2)

    click_button(page, "Keep the Legal-signed v1 wording")
    page.get_by_role("button", name=re.compile(r"^Escalate \d+ conflicts to Legal$")).wait_for()
    _check(page)
    click_pattern(page, r"^Escalate \d+ conflicts to Legal$")
    page.get_by_role("button", name=re.compile(r"^Next:")).wait_for()
    _check(page)
    _next(page, 3)

    click_button(page, "Approve and publish")
    wait_text(page, "Published")
    _check(page)
    click_button(page, "Approve all remaining (demo shortcut)")
    wait_text(page, "Queue is empty")
    _check(page)
    open_tab(page, r"Knowledge Ops approvals")
    page.get_by_role("button", name=re.compile(r"^Approve all \d+ \(demo shortcut\)$")).click()
    wait_content(page, "every one is approved")
    open_tab(page, r"Knowledge Ops approvals")
    wait_text(page, "every one is approved")
    _check(page)
    open_tab(page, r"Conflicts for Legal")
    page.locator('[data-testid="stBaseButton-primary"]').filter(has_text="Keep the").click()
    wait_content(page, "Legal kept")
    open_tab(page, r"Conflicts for Legal")
    wait_text(page, "Legal kept")
    _check(page)
    open_tab(page, r"Legal queue")
    _next(page, 4)

    click_button(page, "Search as both roles")
    wait_text(page, "Answer for: Pharmacy advocate")
    wait_text(page, "Answer for: Insurance advocate")
    _check(page)
    _next(page, 5)

    click_button(page, "Legal revises the wording")
    page.get_by_role("button", name=re.compile(r"^Publish version \d+$")).wait_for()
    _check(page)
    click_pattern(page, r"^Publish version \d+$")
    wait_text(page, "version 2")
    _check(page)
    _next(page, 6)

    click_button(page, "Send draft to author")
    wait_text(page, "Sent to the author")
    _check(page)
    _next(page, 7)

    click_button(page, "Apply the cosmetic edit")
    wait_text(page, "Cosmetic change")
    _check(page)
    click_button(page, "Apply the material edit")
    wait_text(page, "Stale: source changed")
    _check(page)
    click_button(page, "Send to Legal")
    wait_text(page, "Sent to Legal")
    _check(page)
    _next(page, 8)

    click_button(page, "Score the golden set")
    wait_text(page, "Right answer first")
    _check(page)
    for label in ("What failed", "Held-out questions", "Golden set", "Copy detection"):
        open_tab(page, label)
        _check(page)
