# main()
#
# Generates all scraping payloads.
# Splits them into batches.
# Calls scrape_batch(...) for each batch.
# scrape_batch(...)
#
# Launches one browser instance for the entire batch.
# For each ScraperPayload in the batch:
# Opens a new page in the same browser instance.
# Scrapes data using scrape_jobs_on_page.
# Closes the page.
# Finally closes the browser when the batch is done.
# scrape_jobs_on_page(...)
#
# Navigates to the payload’s url.
# Waits for the job list selector.
# Extracts titles/links from each job listing, storing them in Redis.
# Rate Limiting
#
# A small, random delay is added between opening pages (random.uniform(1, 3) seconds).
# An additional, longer wait is inserted between batches (currently 5 seconds, previously 30).
#

import asyncio
import random
from pyppeteer import launch
from dataclasses import dataclass
from typing import List, Dict, Optional

from src.cache.Redis import Redis


@dataclass
class ScraperPayload:
    url: str
    job_list_selector: str
    title_selector: str
    link_selector: str
    date_selector: Optional[str] = None


async def get_inner_text(parent_element, selector: str, page) -> str:
    """
    Helper function to extract innerText from a nested element.
    Returns an empty string if selector is not found.
    """
    try:
        element = await parent_element.querySelector(selector)
        if element:
            text = await page.evaluate("el => el.innerText", element)
            return text.strip() if text else ""
    except Exception as e:
        print(f"Failed to get text for selector '{selector}': {e}")
    return ""


async def get_link_href(parent_element, selector: str, page) -> str:
    """
    Helper function to extract the 'href' from a link element.
    Returns an empty string if the link is not found.
    """
    try:
        link_el = await parent_element.querySelector(selector)
        if link_el:
            href = await page.evaluate("el => el.href", link_el)
            return href.strip() if href else ""
    except Exception as e:
        print(f"Failed to get href for selector '{selector}': {e}")
    return ""


async def scrape_jobs_on_page(page, payload: ScraperPayload, redis_client) -> List[Dict[str, str]]:
    """
    Scrapes a single page using a provided `page` object (instead of launching a new browser).
    """
    try:
        await page.goto(payload.url, {
            'waitUntil': 'networkidle0',
            'timeout': 90000
        })
        await page.waitForSelector(payload.job_list_selector)

        jobs = []
        job_list_elements = await page.querySelectorAll(payload.job_list_selector)

        for job_el in job_list_elements:
            # Only print outerHTML if absolutely needed, otherwise comment this out
            # print(await page.evaluate('(el) => el.outerHTML', job_el))

            try:
                title = await get_inner_text(job_el, payload.title_selector, page)
                link = await get_link_href(job_el, payload.link_selector, page)

                if title or link:
                    jobs.append({"title": title, "link": link})
                    redis_client.append_to_list("jobs", link)

            except Exception as e:
                print(f"Error extracting job element: {e}")

        return jobs

    except Exception as e:
        print(f"Error scraping {payload.url}: {str(e)}")
        return []


async def scrape_batch(payloads: List[ScraperPayload]) -> None:
    """
    Scrape a batch of payloads using a single browser instance.
    """
    redis_client = Redis()
    browser = None
    try:
        browser = await launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )

        # Create a list of pages in parallel (or sequentially) to scrape each payload
        results = []

        for payload in payloads:
            # Add a small random delay between page requests to reduce the risk of rate-limiting
            await asyncio.sleep(random.uniform(1, 3))

            page = await browser.newPage()
            page.setDefaultNavigationTimeout(90000)

            jobs = await scrape_jobs_on_page(page, payload, redis_client)
            results.append((payload.url, jobs))

            await page.close()

        # (Optional) Print or log the aggregated results for the batch:
        for url, jobs in results:
            print(f"Scraped {len(jobs)} jobs from {url}")

    finally:
        if browser:
            await browser.close()


async def main():
    base_url = "https://jobs.apple.com/en-us/search?location=united-states-USA"
    page_key = "page"
    page_limit = 175
    config = {
        'job_list_selector': ".table-col-1",
        'title_selector': ".table--advanced-search__title",
        'link_selector': ".table--advanced-search__title",
    }

    # Prepare all payloads
    queue = [
        ScraperPayload(
            url=f"{base_url}&{page_key}={i}",
            job_list_selector=config['job_list_selector'],
            title_selector=config['title_selector'],
            link_selector=config['link_selector'],
        )
        for i in range(page_limit + 1)
    ]

    # Batch size for concurrent scraping
    batch_size = 10

    for i in range(0, len(queue), batch_size):
        batch = queue[i:i + batch_size]
        print(f"Starting batch {i // batch_size + 1} with {len(batch)} tasks...")

        # Scrape the entire batch (1 browser instance).
        await scrape_batch(batch)

        print(f"Batch {i // batch_size + 1} completed.")

        # (Optional) Sleep between batches if you're concerned about rate limits
        await asyncio.sleep(5)  # Lowered from 30 for illustration


if __name__ == "__main__":
    asyncio.run(main())
