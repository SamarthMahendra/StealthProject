import asyncio
import random
from pyppeteer import launch
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScraperPayload:
    url: str
    job_id: str
    title: str
    location: str
    department: str
    summary: Optional[str]
    long_description: Optional[str]
    date: Optional[str]



async def scrape_job_details(payload: ScraperPayload) -> ScraperPayload:
    """
    Navigates to a single job details page and extracts details.
    Updates the payload with the scraped information.
    """
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

        # Navigate to the job detail page
        await page.goto(payload.url, {
            'waitUntil': 'networkidle0',
            'timeout': 90000
        })

        job_id = await get_inner_text(page, payload.job_id)
        title = await get_inner_text(page, payload.title)
        location = await get_inner_text(page, payload.location)
        department = await get_inner_text(page, payload.department)
        summary = await get_inner_text(page, payload.summary) if payload.summary else None
        long_description = await get_inner_text(page, payload.long_description) if payload.long_description else None
        date = await get_inner_text(page, payload.date) if payload.date else None

        # Update the payload with the scraped details
        payload.job_id = job_id  # Example: Extract job ID from URL if applicable
        payload.title = title
        payload.location = location
        payload.department = department
        payload.summary = summary
        payload.long_description = long_description
        payload.date = date

        return payload

    except Exception as e:
        print(f"Error scraping job details from {payload.url}: {e}")
        return payload
    finally:
        if browser:
            await browser.close()


async def get_inner_text(page, selector: str) -> str:
    """
    Helper function to extract innerText from an element.
    Returns an empty string if the selector is not found.
    """
    try:
        element = await page.querySelector(selector)
        if element:
            text = await page.evaluate("el => el.innerText", element)
            return text.strip() if text else ""
    except Exception as e:
        print(f"Failed to get text for selector '{selector}': {e}")
    return ""


async def worker(payload: ScraperPayload):
    """Worker to scrape a single job details page."""
    print(f"Processing: {payload.url}")
    try:
        updated_payload = await scrape_job_details(payload)
        print(f"Updated Payload:\n{updated_payload}")
    except Exception as e:
        print(f"Failed to scrape {payload.url}: {e}")


async def main():
    payload = ScraperPayload(
        url="https://jobs.apple.com/en-us/details/114438148/us-business-expert?team=SLDEV",
        job_id="#jobNumber",
        title=".jd__header--title",
        location=".addressCountry",
        department="#job-team-name",
        summary="#jd-job-summary",
        long_description="#jd-description",
        date="#jobPostDate"
    )

    # Run the worker for the single job
    payload = await worker(payload)
    print(payload)



if __name__ == "__main__":
    asyncio.run(main())
