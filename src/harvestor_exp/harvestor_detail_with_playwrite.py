import asyncio
import random
from dataclasses import dataclass
from typing import Optional

from playwright.async_api import async_playwright

@dataclass
class ScraperPayload:
    url: str
    job_id: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    department: Optional[str] = None
    summary: Optional[str] = None
    long_description: Optional[str] = None
    date: Optional[str] = None

sem = asyncio.Semaphore(5)

async def get_inner_text(page, selector: str) -> str:
    """
    Helper function to extract innerText from an element via Playwright.
    Returns an empty string if the selector is not found.
    """
    if not selector:
        return ""
    try:
        element = await page.query_selector(selector)
        if element:
            text = await element.inner_text()
            return text.strip() if text else ""
    except Exception as e:
        print(f"Failed to get text for selector '{selector}': {e}")
    return ""

async def scrape_job_details_on_page(page, payload: ScraperPayload):
    """
    Scrapes a single job detail page using an *already open* browser page.
    Updates the payload with scraped info and inserts into the DB.
    """
    try:
        # Add random delay (rate-limiting)
        await asyncio.sleep(random.uniform(1, 3))

        # Navigate to the job detail page
        # (Playwright uses wait_until="networkidle" instead of "networkidle0")
        await page.goto(payload.url, wait_until="networkidle", timeout=90000)

        # Extract info
        job_id = await get_inner_text(page, payload.job_id)
        title = await get_inner_text(page, payload.title)
        location = await get_inner_text(page, payload.location)
        department = await get_inner_text(page, payload.department)
        summary = await get_inner_text(page, payload.summary)
        long_desc = await get_inner_text(page, payload.long_description)
        date_val = await get_inner_text(page, payload.date)

        # Insert into DB
        from src.Database.database import Database
        db = Database()
        query = """
            INSERT INTO job_details(job_id, title, location, department, summary, long_description, date)
            VALUES(%s, %s, %s, %s, %s, %s, %s)
        """
        params = (job_id, title, location, department, summary, long_desc, date_val)
        db.insert_query(query, params)

        # Update the payload with the scraped details (optional)
        payload.job_id = job_id
        payload.title = title
        payload.location = location
        payload.department = department
        payload.summary = summary
        payload.long_description = long_desc
        payload.date = date_val

    except Exception as e:
        print(f"Error scraping job details from {payload.url}: {e}")

async def process_job_detail(payload, browser):
    page = None
    try:
        # Create a new page in the existing browser
        page = await browser.new_page()
        await scrape_job_details_on_page(page, payload)
    except Exception as e:
        # Log error
        print(f"Error processing {payload.url}: {e}")
    finally:
        if page:
            try:
                await page.close()
            except Exception:
                pass  # Page may already be closed

async def scrape_batch(payloads):
    """
    Scrapes a batch of jobs using a single browser instance for all payloads.
    """
    async with async_playwright() as p:
        # Launch the browser (headless mode)
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )

        # Use asyncio.gather to process each job (potentially concurrently)
        tasks = [process_job_detail(payload, browser) for payload in payloads]
        await asyncio.gather(*tasks)

        # Browser automatically closes at the end of the context block

async def main():
    config = {
        "job_id": "#jobNumber",
        "title": ".jd__header--title",
        "location": ".addressCountry",
        "department": "#job-team-name",
        "summary": "#jd-job-summary",
        "long_description": "#jd-description",
        "date": "#jobPostDate"
    }

    from src.cache.Redis import Redis
    cache = Redis()

    # Grab URLs from Redis (stored under the 'jobs' list)
    queue = set(cache.get_list('jobs'))

    print(f"Found {len(queue)} job URLs to scrape.")

    # Build ScraperPayload objects
    jobs = [ScraperPayload(url=item, **config) for item in queue]

    # You can process all at once, or in batches
    batch_size = 3
    for i in range(0, len(jobs), batch_size):
        batch = jobs[i : i + batch_size]
        print(f"Scraping batch {i // batch_size + 1} with {len(batch)} items.")
        await scrape_batch(batch)

        # Optional: Wait between batches if you need more rate-limiting
        await asyncio.sleep(10)

    print("All done!")

if __name__ == "__main__":
    asyncio.run(main())
