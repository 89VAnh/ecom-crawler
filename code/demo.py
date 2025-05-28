from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://gearvn.com", wait_until="domcontentloaded")

    title = page.title()
    print("Page Title:", title)

    browser.close()
