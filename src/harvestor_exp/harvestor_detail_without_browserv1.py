import asyncio
import random
from dataclasses import dataclass
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup

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


# Limit concurrency to avoid overwhelming the server or your system.
SEM = asyncio.Semaphore(5)

def get_inner_text(soup: BeautifulSoup, selector: str) -> str:
    """
    Given a CSS selector, find the first matching element in `soup`
    and return its text. Otherwise return an empty string.
    """
    if not selector:
        return ""

    element = soup.select_one(selector)
    if element:
        return element.get_text(strip=True)
    return ""


async def scrape_job_details(payload: ScraperPayload, session: aiohttp.ClientSession) -> None:
    """
    Asynchronously fetches the job details page, parses required fields
    using CSS selectors, and then inserts into the database.
    """
    try:
        # Basic random delay for rate limiting
        await asyncio.sleep(random.uniform(1, 2))

        # Fetch HTML content
        async with session.get(payload.url) as response:
            # Raise if there's a non-2xx status
            response.raise_for_status()
            html = await response.text()

        # Parse the HTML
        soup = BeautifulSoup(html, "html.parser")

        # Extract info based on CSS selectors in the payload
        job_id = get_inner_text(soup, payload.job_id)
        title = get_inner_text(soup, payload.title)
        location = get_inner_text(soup, payload.location[0])
        if not location:
            location = get_inner_text(soup, payload.location[1])
        department = get_inner_text(soup, payload.department)
        summary = get_inner_text(soup, payload.summary)
        long_desc = get_inner_text(soup, payload.long_description)
        date_val = get_inner_text(soup, payload.date)

        # Insert into the database (example)
        from src.Database.database import Database
        db = Database()
        query = """
            INSERT INTO job_details (job_id, title, location, department, summary, long_description, date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (job_id, title, location, department, summary, long_desc, date_val)
        db.insert_query(query, params)

        # Optionally update the payload with the scraped info
        payload.job_id = job_id
        payload.title = title
        payload.location = location
        payload.department = department
        payload.summary = summary
        payload.long_description = long_desc
        payload.date = date_val

        print(f"[DONE] Scraped {payload.url}")

    except Exception as e:
        print(f"Error scraping {payload.url}: {e}")


async def process_job_detail(payload: ScraperPayload, session: aiohttp.ClientSession) -> None:
    """
    Process a single job detail page under semaphore control.
    """
    async with SEM:  # ensures only X tasks run concurrently
        await scrape_job_details(payload, session)


async def scrape_batch(payloads) -> None:
    """
    Given a list of ScraperPayloads, create tasks to scrape each payload concurrently.
    Uses a single shared aiohttp.ClientSession.
    """
    async with aiohttp.ClientSession() as session:
        tasks = [asyncio.create_task(process_job_detail(pl, session)) for pl in payloads]
        await asyncio.gather(*tasks)


async def main():
    # Example config mapping selectors to the CSS for each field
    config = {
        "job_id": "#jobNumber",
        "title": ".jd__header--title",
        "location": [".addressCountry", "#job-location-name"],
        "department": "#job-team-name",
        "summary": "#jd-job-summary",
        "long_description": "#jd-description",
        "date": "#jobPostDate"
    }

    from src.cache.Redis import Redis
    cache = Redis()

    # Get unique job URLs from Redis
    queue = set(cache.get_list("jobs"))
    print(f"Found {len(queue)} job URLs to scrape.")

    # Build a list of ScraperPayload objects
    jobs = [ScraperPayload(url=item, **config) for item in queue]

    # Process jobs in small batches if desired:
    batch_size = 3
    for i in range(0, len(jobs), batch_size):
        batch = jobs[i : i + batch_size]
        print(f"Scraping batch {i // batch_size + 1} with {len(batch)} items.")
        await scrape_batch(batch)

        # Optional: Sleep between batches
        await asyncio.sleep(2)

    print("All done!")


if __name__ == "__main__":
    asyncio.run(main())



