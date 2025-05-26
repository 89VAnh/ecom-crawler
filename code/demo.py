from playwright.sync_api import sync_playwright


class Crawler:
    def __init__(self, headless=False):
        self.headless = headless
        self.browser = None
        self.page = None
        self.playwright = None

    def start(self):
        self.playwright = sync_playwright().start()
        # self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.browser = self.playwright.chromium.launch()
        self.page = self.browser.new_page()

    def close(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def scrape_thegioididong(self, url: str):
        self.page.goto(url, wait_until="domcontentloaded")
        self.page.wait_for_selector("ul.listproduct")

        products = self.page.locator("ul.listproduct > li")
        results = []

        for product in products.all():
            link_elem = product.locator("a").first
            link = link_elem.get_attribute("href") if link_elem else ""

            full_url = "https://www.thegioididong.com" + link
            print(full_url)

            detail_page = self.browser.new_page()
            try:
                detail_page.goto(full_url, wait_until="domcontentloaded")
                detail_page
                title_elem = detail_page.locator(".product-name h1")
                price_elem = detail_page.locator(".box-price-present, .bs_price strong")

                results.append(
                    {
                        "title": title_elem.inner_text() if title_elem else "",
                        "price": price_elem.inner_text() if price_elem else "",
                        "link": full_url,
                    }
                )
            except Exception as e:
                print(f"Error scraping {full_url}: {e}")
            finally:
                detail_page.close()

        return results


# Example usage
if __name__ == "__main__":
    url = "https://www.thegioididong.com/dtdd-apple-iphone?key=iphone&sc=new"
    crawler = Crawler()
    try:
        crawler.start()
        results = crawler.scrape_thegioididong(url)
        for item in results:
            print(item)
    finally:
        crawler.close()
