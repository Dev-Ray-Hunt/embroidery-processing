"""Browser smoke tests for the validation UI (POC 2 Step 3).

Requires the built catalogue and Playwright chromium; skips gracefully when
either is missing so the unit layer stays runnable everywhere.
"""

from __future__ import annotations


def test_page_loads_and_matches_without_js_errors(browser_page):
    page = browser_page
    page.goto(page.base_url_poc2 + "/")

    # Initial auto-match on the default color (#c8102e) renders all four
    # algorithm columns with five cards each.
    page.wait_for_selector(".algo-col .card", timeout=10_000)
    assert page.locator(".algo-col").count() == 4
    assert page.locator(".algo-col").first.locator(".card").count() == 5

    # The known spot-check: top CIEDE2000 match for #c8102e is 1637.
    first_card = page.locator(".algo-col").first.locator(".card").first
    assert "1637" in first_card.inner_text()

    # Catalogue browser populated with swatch tiles.
    page.wait_for_selector(".tile", timeout=10_000)
    assert page.locator(".tile").count() > 100

    assert page.collected_errors == [], f"JS errors: {page.collected_errors}"


def test_hex_input_and_family_filter(browser_page):
    page = browser_page
    page.goto(page.base_url_poc2 + "/")
    page.wait_for_selector(".algo-col .card", timeout=10_000)

    # Type a new color; results re-render (debounced).
    page.fill("#hex", "#1b3f94")
    page.wait_for_timeout(800)
    assert page.locator(".algo-col .card").count() > 0
    # The input swatch half of the first card reflects the new color.
    swatch_left = page.locator(".algo-col .card .swatch div").first
    assert "rgb(27, 63, 148)" in swatch_left.evaluate("el => getComputedStyle(el).background")

    # Click the "red" family chip; the grid filters down.
    total_before = page.locator(".tile").count()
    page.click('.chip[data-value="red"]')
    page.wait_for_timeout(600)
    assert 0 < page.locator(".tile").count() < total_before

    assert page.collected_errors == [], f"JS errors: {page.collected_errors}"
