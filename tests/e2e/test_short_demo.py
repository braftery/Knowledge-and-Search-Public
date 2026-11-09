"""Short demo: approve the three Legal units, then both roles get a saved answer."""

from tests.e2e.support import (
    activity_text,
    assert_no_exception,
    assert_saved_answers,
    click_button,
    go_to_step,
    open_demo,
    wait_for_activity_change,
    wait_text,
)


def _approve_three(page) -> None:
    for _ in range(3):
        current = ""
        now = page.locator(".meta", has_text="Now:")
        if now.count():
            current = now.first.inner_text()
        click_button(page, "Approve and publish")
        page.wait_for_function(
            """(prev) => {
                const nodes = [...document.querySelectorAll('.meta')];
                const now = nodes.map((node) => node.innerText).find((text) => text && text.includes('Now:'));
                const empty = document.body.innerText.includes('Queue is empty');
                return empty || (now && now !== prev);
            }""",
            arg=current,
        )
        assert_no_exception(page)
    wait_text(page, "Queue is empty")


def test_short_demo_approves_three_units_and_answers_both_roles(page, app_url):
    open_demo(page, app_url)
    previous = activity_text(page)
    click_button(page, "Jump to short demo")
    wait_for_activity_change(page, previous)
    go_to_step(page, 3, "Legal approves")
    page.get_by_role("button", name="Approve and publish").wait_for()
    _approve_three(page)
    assert_saved_answers(page)

    go_to_step(page, 4, "Search")
    click_button(page, "Search as both roles")
    wait_text(page, "Answer for: Pharmacy advocate")
    wait_text(page, "Answer for: Insurance advocate")
    body = page.locator("body").inner_text()
    assert body.count("Saved model answer.") >= 2
    assert "No approved answer" not in body
    assert_no_exception(page)
    assert_saved_answers(page)
