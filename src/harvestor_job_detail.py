import asyncio
import random
from pyppeteer import launch
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScraperPayload:

    def __init__(self, url, **kwargs):
        #      "job_id": "#jobNumber",
        #         "title": ".jd__header--title",
        #         "location": ".addressCountry",
        #         "department": "#job-team-name",
        #         "summary": "#jd-job-summary",
        #         "long_description": "#jd-description",
        #         "date": "#jobPostDate"
        #     }
        self.url: str = url
        self.job_id = kwargs.get('job_id')
        self.title = kwargs.get('title')
        self.location = kwargs.get('location')
        self.department = kwargs.get('department')
        self.summary: Optional[str] = kwargs.get('summary', None)
        self.long_description :Optional[str]= kwargs.get('long_description', None)
        self.date :Optional[str]= kwargs.get('date', None)



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


        from src.Database.database import Database

        db = Database()
        #  """
        # CREATE TABLE IF NOT EXISTS job_details(
        #     job_id VARCHAR(255) PRIMARY KEY,
        #     title VARCHAR(255),
        #     location VARCHAR(255),
        #     department VARCHAR(255),
        #     summary TEXT,
        #     long_description TEXT,
        #     date DATE
        # );
        # """

        # write an insert query
        query = """
        INSERT INTO job_details(job_id, title, location, department, summary, long_description, date)
        VALUES(%s, %s, %s, %s, %s, %s, %s)
        """
        params = (str(job_id), str(title), str(location), str(department), str(summary), str(long_description), str(date))
        db.insert_query(query, params)


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

        # from src.cache.Redis import Redis
        #
        # # add to redis under result
        #
        # r = Redis()
        #
        # temp_res = {
        #     "job_id": updated_payload.job_id,
        #     "title": updated_payload.title,
        #     "location": updated_payload.location,
        #     "department": updated_payload.department,
        #     "summary": updated_payload.summary,
        #     "long_description": updated_payload.long_description,
        #     "date": updated_payload.date
        # }
        # r.append_to_list('result', temp_res)


    except Exception as e:
        print(f"Failed to scrape {payload.url}: {e}")


async def main():
    config ={
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
    queue = cache.get_list('jobs')
    jobs = []
    for item in queue[:1]:
        job = ScraperPayload(url=item, **config)
        jobs.append(job)

    batch_limit = 10
    for i in range(0, len(jobs), batch_limit):
        batch = jobs[i:i + batch_limit]
        await asyncio.gather(*[worker(job) for job in batch])
        # sleep for a while
        await asyncio.sleep(180)




if __name__ == "__main__":
    asyncio.run(main())
