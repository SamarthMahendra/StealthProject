import asyncio
import random
from pyppeteer import launch
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class ScraperPayload:
    url: str
    job_list_selector: str
    title_selector: str
    description_selector: str
    location_selector: str
    link_selector: str
    date_selector: Optional[str] = None


async def scrape_jobs(payload: ScraperPayload) -> List[Dict[str, str]]:
    """Scrapes jobs based on the given payload without using JavaScript code in page.evaluate."""
    browser = None
    try:
        # Add random delay for rate limiting
        await asyncio.sleep(random.uniform(1, 3))

        browser = await launch(
            headless=False,
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
            try:
                title = await get_inner_text(job_el, payload.title_selector, page)
                description = await get_inner_text(job_el, payload.description_selector, page)
                location = await get_inner_text(job_el, payload.location_selector, page)
                link = await get_link_href(job_el, payload.link_selector, page)

                # Append scraped job to the list
                if title or description or location or link:
                    jobs.append({
                        "title": title,
                        "description": description,
                        "location": location,
                        "link": link
                    })
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


async def worker(queue: List[ScraperPayload]):
    """Worker to process the scraping jobs."""
    while queue:
        payload = queue.pop(0)
        print(f"Processing: {payload.url}")
        try:
            jobs = await scrape_jobs(payload)
            print(f"Jobs scraped from {payload.url}:\n", jobs)
        except Exception as e:
            print(f"Failed to scrape {payload.url}: {e}")


async def main():
    queue = [
        ScraperPayload(
            url="https://jobs.careers.microsoft.com/global/en/search?l=en_us&pg=1&pgSz=20",
            job_list_selector=".ms-List-cell",
            title_selector="h2",
            description_selector="div div div:nth-child(2) div span",
            location_selector="div.ms-Stack:nth-child(2) span",
            link_selector=None,
            date_selector=None
        ),
    ]

    # Create tasks for concurrent execution
    tasks = [worker([payload]) for payload in queue]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())

