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


async def scrape_jobs(payload: ScraperPayload) -> List[Dict[str, str]]:
    r = Redis()
    """Scrapes jobs based on the given payload without using JavaScript code in page.evaluate."""
    browser = None
    try:
        # Add random delay for rate limiting
        await asyncio.sleep(random.uniform(1, 3))

        browser = await launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        page = await browser.newPage()

        # Set longer default timeout
        page.setDefaultNavigationTimeout(90000)

        # Go to the page and wait until network is idle
        await page.goto(payload.url, {
            'waitUntil': 'networkidle0',
            'timeout': 90000
        })

        # Wait for the container that holds the job listings
        await page.waitForSelector(payload.job_list_selector)

        # Scrape jobs
        jobs = []
        job_list_elements = await page.querySelectorAll(payload.job_list_selector)
        for job_el in job_list_elements:
            # print html of each job element
            print(await page.evaluate('(el) => el.outerHTML', job_el))
            try:
                title = await get_inner_text(job_el, payload.title_selector, page)
                link = await get_link_href(job_el, payload.link_selector, page)

                # Append scraped job to the list
                if title or link:
                    jobs.append({
                        "title": title,
                        "link": link
                    })

                    # todo : package links that are diverse and append to redis
                    # append job to redis list
                    r.append_to_list('jobs', link)
            except Exception as e:
                print(f"Error extracting job element: {e}")

        return jobs
    except Exception as e:
        print(f"Error scraping {payload.url}: {str(e)}")
        return []
    finally:
        if browser:
            await browser.close()


async def get_inner_text(parent_element, selector: str, page) -> str:
    """
    Helper function to extract innerText from a nested element.
    Returns an empty string if selector is not found.
    """
    try:
        element = await parent_element.querySelector(selector)
        if element:
            # Using page.evaluate to get property from the element itself (no JS code creation)
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
            # Use page.evaluate to retrieve href directly
            href = await page.evaluate("el => el.href", link_el)
            return href.strip() if href else ""
    except Exception as e:
        print(f"Failed to get href for selector '{selector}': {e}")
    return ""


async def worker(queue: ScraperPayload):
    """Worker to process the scraping jobs."""
    while queue:

        try:
            jobs = await scrape_jobs(queue)
            print(f"Jobs scraped from {queue.url}:\n", jobs)
        except Exception as e:
            print(f"Failed to scrape {queue.url}: {e}")


async def main():

    base_url = "https://jobs.apple.com/en-us/search?location=united-states-USA"
    page_key = "page"
    page_limit = 175
    config = {
        'job_list_selector': ".table-col-1",
        'title_selector': ".table--advanced-search__title",
        'link_selector': ".table--advanced-search__title",

    }

    # Create a queue of payloads
    queue = [
        ScraperPayload(
            url=f"{base_url}&{page_key}={i}",
            job_list_selector=config['job_list_selector'],
            title_selector=config['title_selector'],
            link_selector=config['link_selector'],
        ) for i in range(page_limit + 1)
    ]

    # Batch size for concurrent workers
    batch_size = 10

    # Process payloads in batches
    for i in range(0, len(queue), batch_size):
        batch = queue[i:i + batch_size]
        print(f"Starting batch {i // batch_size + 1} with {len(batch)} tasks...")
        await asyncio.gather(*(worker(payload) for payload in batch))
        print(f"Batch {i // batch_size + 1} completed.")
        # sleep for a while
        await asyncio.sleep(30)



if __name__ == "__main__":
    asyncio.run(main())

