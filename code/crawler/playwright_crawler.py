import copy
import json
import time
import asyncio
import logging
from playwright.async_api import async_playwright, Browser, Locator, Page
from error.page_end_error import PageEndError
import traceback
from sink.sink import Sink
from transform.transform import Transform
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("crawler.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class Crawler:
    def __init__(self, pipeline) -> None:
        self.pipeline = pipeline
        self.results = []
        self.playwright = None
        self.browser = None
        self.page = None

    async def new_page(self, url, **kwargs) -> Page:
        logger.debug(f"Opening new page: {url}")
        try:
            page = await self.browser.new_page()
            await page.context.clear_cookies()
            await page.goto(url, wait_until="domcontentloaded")
            logger.debug(f"Successfully loaded page: {url}")
        except Exception as e:
            logger.error(f"Failed to load page {url}: {str(e)}", exc_info=True)
            raise Exception(f"Error: {url} - {kwargs}")
        if kwargs.get("delay"):
            await asyncio.sleep(kwargs.get("delay"))
        return page

    async def get(self, tmp_val=None, **kwargs):
        try:
            results = []
            base_url = kwargs.get("base_url")
            fields: dict = kwargs.get("fields")
            keywords = kwargs.get("keywords", [])
            logger.debug(f"Starting scrape with keywords: {keywords}")
            for keyword in tqdm(keywords, desc="Scraping keywords"):
                page = await self.new_page(base_url)
                logger.debug(f"Searching for keyword: {keyword}")
                page = await self.search(page, keyword, **kwargs.get("search"))
                products = await page.locator(kwargs.get("product_selector")).all()
                logger.debug(f"Found {len(products)} products for keyword '{keyword}'")
                for product in tqdm(
                    products,
                    desc=f"Scraping products for '{keyword}'",
                    total=len(products),
                    leave=False,
                    ncols=80,
                ):
                    try:
                        link_info = fields.get("link")
                        link_element = product.locator(link_info["selector"]).first
                        link_value = (
                            await link_element.get_attribute(link_info["attr"])
                            if link_element
                            else None
                        )
                        if not link_value:
                            logger.warning(
                                f"No link found for product in keyword '{keyword}'"
                            )
                            continue
                        full_url = base_url + link_value
                        logger.debug(f"Processing product link: {full_url}")

                        img_info = fields.get("img")
                        img_element = product.locator(img_info["selector"]).first
                        img_value = (
                            await img_element.get_attribute(img_info["attr"])
                            if img_element
                            else ""
                        )

                        result = {
                            "keyword": keyword,
                            "link": full_url,
                            "img": img_value,
                        }

                        product_page = await self.new_page(full_url)
                        for key, value in fields.items():
                            if key in ["link", "img"]:
                                continue
                            element = await product_page.query_selector(
                                value["selector"]
                            )
                            if not element:
                                logger.warning(
                                    f"No element found for {key} on {full_url}"
                                )
                                result[key] = ""
                            elif value.get("attr") == "text":
                                result[key] = await element.inner_text()
                            else:
                                result[key] = await element.get_attribute(
                                    value.get("attr")
                                )

                        results.append(result)
                        logger.debug(f"Scraped product: {result}")

                        await product_page.context.close()
                        await product_page.close()

                    except Exception as e:
                        logger.error(
                            f"Error parsing product for keyword '{keyword}': {str(e)}",
                            exc_info=True,
                        )
                        continue

                await page.context.close()
                await page.close()

            if kwargs.get("cond"):
                expr = kwargs["cond"]["validate"]
                if not eval(expr):
                    logger.error(f"Condition failed: {expr}")
                    raise PageEndError(f"error: {expr}")

            logger.info(f"Scraping completed with {len(results)} results")
            return results

        except PageEndError as e:
            raise e
        except Exception as e:
            logger.error(f"Error in get method: {str(e)}", exc_info=True)
            raise

    async def run(self):
        logger.debug("Starting crawler run")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()
        self.page = await self.browser.new_page()
        tmp_val = None
        try:
            for action in self.pipeline:
                logger.debug(f"Executing action: {action.get('name')}")
                method = getattr(self, action.get("name"))
                tmp_val = await method(tmp_val, **action.get("params"))
        except Exception as e:
            logger.error(f"Error in pipeline execution: {str(e)}", exc_info=True)
            raise
        finally:
            await self.page.context.close()
            await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        logger.info("Crawler run completed")
        return self.results

    # Other methods (select, click, scroll, etc.) should also include logging as needed
    async def select(self, input_val=None, **kwargs) -> Locator:
        logger.debug(f"Selecting with selector: {kwargs.get('selector')}")
        if isinstance(input_val, Locator):
            return input_val.locator(kwargs.get("selector"))
        return self.page.locator(kwargs.get("selector"))

    async def click(self, input_val=None, **kwargs):
        logger.debug(f"Clicking on selector: {kwargs.get('selector')}")
        if isinstance(input_val, Locator):
            await input_val.locator(kwargs.get("selector")).click()
        else:
            await self.page.locator(kwargs.get("selector")).click()
        return self.page

    async def scroll(self, input_val=None, **kwargs):
        logger.debug("Scrolling page")
        await self.page.keyboard.press("End")
        if kwargs.get("wait"):
            await asyncio.sleep(int(kwargs.get("wait")))
        return input_val

    async def getlinks(self, input_val=None, **kwargs):
        logger.debug(f"Getting links with selector: {kwargs.get('selector')}")
        links = []
        origin = kwargs.get("origin", "")
        count = await input_val.count()
        for index in range(count):
            child = input_val.nth(index)
            href = await child.get_attribute("href")
            links.append(f"{origin}{href}")
        logger.debug(f"Found {len(links)} links")
        return links

    async def get_links_by_cond(self, input_val: Locator = None, **kwargs):
        logger.debug(
            f"Getting conditional links with selector: {kwargs.get('link_selector')}"
        )
        links = []
        callback = kwargs.get("callback")
        link_expr = kwargs.get("link_selector")
        origin = kwargs.get("origin", "")
        count = await input_val.count()
        for index in range(count):
            child = input_val.nth(index)
            if callback(child):
                href = await child.locator(link_expr).get_attribute("href")
                links.append(f"{origin}{href}")
        logger.debug(f"Found {len(links)} conditional links")
        return links

    async def search(self, page: Page, keyword: str, **kwargs) -> Page:
        logger.debug(f"Searching for keyword: {keyword}")
        input_box = page.locator(kwargs.get("input_selector"))
        await input_box.fill(keyword)

        if kwargs.get("form_selector"):
            form = page.locator(kwargs.get("form_selector"))
            async with page.expect_navigation():
                await form.evaluate("form => form.submit()")
        elif kwargs.get("btn_selector"):
            btn = page.locator(kwargs.get("btn_selector"))
            await btn.click()
            await page.wait_for_selector(".search-list-results")
        logger.debug("Search completed")
        return page

    async def foreach(self, input_val=None, **kwargs):
        logger.debug(f"Starting foreach with limit: {kwargs.get('limit')}")
        iterator = []
        if isinstance(input_val, list):
            iterator = input_val
        else:
            limit = kwargs.get("limit")
            start = kwargs.get("start", 0)
            step = kwargs.get("step", 1)
            iterator = range(start, limit, step)

        for item in iterator:
            actions = copy.deepcopy(kwargs["actions"])
            tmp_val = item
            for action in actions:
                try:
                    params = action["params"]
                    params["item"] = item
                    if kwargs.get("cond"):
                        if kwargs["cond"]["action"] == action.get("name"):
                            params["cond"] = kwargs["cond"]
                    logger.debug(
                        f"Executing foreach action: {action.get('name')} with item: {item}"
                    )
                    tmp_val = await getattr(self, action.get("name"))(tmp_val, **params)
                except PageEndError as e:
                    logger.error(f"PageEndError in foreach: {str(e)}", exc_info=True)
                    raise e
                except Exception as e:
                    logger.error(f"Error in foreach action: {str(e)}", exc_info=True)
            if kwargs.get("delay"):
                await asyncio.sleep(kwargs.get("delay"))
        return tmp_val

    async def transform(self, input_val, **kwargs):
        logger.debug("Executing transform")
        return Transform(input_val, **kwargs).process()

    async def get_detail(self, input_val: None, **kwargs) -> dict:
        logger.debug("Getting details")
        data = {}
        for key in list(kwargs.keys()):
            data[key] = ""
            text_parent = self.page.locator(kwargs.get(key))
            count = await text_parent.count()
            for index in range(count):
                data[key] += "\n" + await text_parent.nth(index).inner_text()
            data[key] = data[key].strip("\n")
        data["url"] = self.page.url
        self.results.append(data)
        logger.debug(f"Details collected: {data}")
        return data

    async def get_table(self, input_val: None, **kwargs):
        logger.debug(f"Getting table: {kwargs.get('tbl_name')}")
        data = {"name": kwargs.get("tbl_name"), "headers": [], "rows": []}
        header_selector = kwargs.get("header")
        row_selector = kwargs.get("row")
        cell_selector = kwargs.get("cell")
        headers = self.page.locator(header_selector)
        count = await headers.count()
        for i in range(count):
            data["headers"].append(await headers.nth(i).inner_text())
        rows = self.page.locator(row_selector)
        row_count = await rows.count()
        for i in range(row_count):
            cells = rows.nth(i).locator(cell_selector)
            cell_count = await cells.count()
            row = []
            for j in range(cell_count):
                row.append(await cells.nth(j).inner_text())
            data["rows"].append(row)
        self.results.append(data)
        logger.debug(f"Table collected: {data}")
        return data

    async def save(self, input_val, **kwargs):
        logger.debug(f"Saving data with type: {kwargs.get('type')}")
        result = Sink(kwargs.get("type"), input_val, **kwargs).execute()
        logger.debug("Data saved")
        return result

    async def clear_sink(self, input_val, **kwargs):
        logger.debug(f"Clearing sink with type: {kwargs.get('type')}")
        Sink(kwargs.get("type"), input_val, **kwargs).clear()
        logger.debug("Sink cleared")
