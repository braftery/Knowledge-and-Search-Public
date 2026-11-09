"""Every Explore view opens every page, and the guided demo keeps its place."""

from tests.e2e.support import (
    EXPLORE_PAGES,
    activity_text,
    assert_no_exception,
    choose_view,
    click_button,
    go_to_step,
    heading,
    open_demo,
    sidebar_button,
    wait_for_activity_change,
)


def test_every_explore_page_loads(page, app_url):
    open_demo(page, app_url)
    for label, pages in EXPLORE_PAGES.items():
        choose_view(page, label)
        for name in pages:
            sidebar_button(page, name).click()
            page.locator("h1.screen-title", has_text=name).wait_for()
            assert heading(page) == name
            assert_no_exception(page)


def test_explore_round_trip_keeps_demo_step_and_approvals(page, app_url):
    open_demo(page, app_url)
    previous = activity_text(page)
    click_button(page, "Jump to short demo")
    wait_for_activity_change(page, previous)
    go_to_step(page, 3, "Legal approves")
    page.get_by_role("button", name="Approve and publish").wait_for()
    waiting = page.locator(".meta", has_text="Now:").first.inner_text()
    click_button(page, "Approve and publish")
    page.get_by_text("Published").first.wait_for()
    after = page.locator(".meta", has_text="Now:").first.inner_text()
    assert after != waiting
    assert "Step 3 of 8" in page.locator("body").inner_text()

    choose_view(page, "Pharmacy advocate")
    page.locator("h1.screen-title", has_text="Agent desktop").wait_for()
    assert_no_exception(page)

    choose_view(page, "Guided demo")
    page.locator("h1.screen-title", has_text="Legal approves units, not documents").wait_for()
    body = page.locator("body").inner_text()
    assert "Step 3 of 8" in body
    assert page.locator(".meta", has_text="Now:").first.inner_text() == after
    assert waiting not in page.locator(".meta", has_text="Now:").first.inner_text()
    assert_no_exception(page)
