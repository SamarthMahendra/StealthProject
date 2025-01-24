import asyncio
import aiohttp
import logging
import redis
import json
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from urllib.parse import urljoin
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError
from pyppeteer import launch
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class JobSite:
    name: str
    base_url: str
    selectors: Dict[str, str]
    pagination: Dict[str, str]
    js_required: bool = False
    wait_for_selector: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


class JobHarvester:
    def __init__(self, mongo_uri: str, redis_uri: str):
        """Initialize the job harvester with database connections."""
        # MongoDB for storing jobs
        self.mongo_client = AsyncIOMotorClient(mongo_uri)
        self.db = self.mongo_client.jobs_db
        self.jobs_collection = self.db.jobs

        # Redis for job deduplication and rate limiting
        self.redis_client = redis.from_url(redis_uri)

        # Session for making HTTP requests
        self.session = None
        self.browser = None

        # User agent rotation
        self.ua = UserAgent()

    async def __aenter__(self):
        """Setup async resources."""
        self.session = aiohttp.ClientSession()
        if any(site.js_required for site in self.job_sites):
            self.browser = await launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup async resources."""
        if self.session:
            await self.session.close()
        if self.browser:
            await self.browser.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_page_content(self, url: str, site: JobSite) -> str:
        """Fetch page content with retry logic and appropriate method."""
        if site.js_required:
            return await self._fetch_with_pyppeteer(url, site)
        else:
            return await self._fetch_with_aiohttp(url, site)

    async def _fetch_with_aiohttp(self, url: str, site: JobSite) -> str:
        """Fetch page content using aiohttp."""
        headers = {
            'User-Agent': self.ua.random,
            **(site.headers or {})
        }
        async with self.session.get(url, headers=headers) as response:
            response.raise_for_status()
            return await response.text()

    async def _fetch_with_pyppeteer(self, url: str, site: JobSite) -> str:
        """Fetch page content using pyppeteer for JavaScript-heavy sites."""
        page = await self.browser.newPage()
        try:
            await page.setUserAgent(self.ua.random)
            await page.goto(url, {'waitUntil': 'networkidle0'})
            if site.wait_for_selector:
                await page.waitForSelector(site.wait_for_selector)
            return await page.content()
        finally:
            await page.close()

    async def process_job_listing(self, job_data: Dict, site: JobSite):
        """Process and store individual job listing."""
        # Generate unique ID for deduplication
        job_id = f"{site.name}_{job_data['title']}_{job_data['location']}"

        # Check if job already exists in Redis
        if not self.redis_client.setnx(f"job:{job_id}", "1"):
            return

        # Set TTL for Redis key (e.g., 30 days)
        self.redis_client.expire(f"job:{job_id}", 2592000)

        # Prepare job document
        job_doc = {
            "_id": job_id,
            "source": site.name,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            **job_data
        }

        try:
            await self.jobs_collection.update_one(
                {"_id": job_id},
                {"$set": job_doc},
                upsert=True
            )
            logger.info(f"Stored job: {job_id}")
        except DuplicateKeyError:
            logger.warning(f"Duplicate job found: {job_id}")
        except Exception as e:
            logger.error(f"Error storing job {job_id}: {str(e)}")

    async def extract_jobs(self, html: str, site: JobSite) -> List[Dict]:
        """Extract job listings from HTML content."""
        page = await self.browser.newPage()
        try:
            await page.setContent(html)

            jobs = await page.evaluate('''(selectors) => {
                return Array.from(document.querySelectorAll(selectors.job_list))
                    .map(job => {
                        try {
                            const title = job.querySelector(selectors.title)?.innerText?.trim();
                            const location = job.querySelector(selectors.location)?.innerText?.trim();
                            const description = job.querySelector(selectors.description)?.innerText?.trim();
                            const link = job.querySelector(selectors.link)?.href;
                            const company = job.querySelector(selectors.company)?.innerText?.trim();

                            if (!title || !link) return null;

                            return {
                                title,
                                location: location || '',
                                description: description || '',
                                link,
                                company: company || ''
                            };
                        } catch (err) {
                            console.error('Error processing job:', err);
                            return null;
                        }
                    })
                    .filter(job => job !== null);
            }''', site.selectors)

            return jobs
        finally:
            await page.close()

    async def crawl_site(self, site: JobSite):
        """Crawl a job site including pagination."""
        current_url = site.base_url
        while current_url:
            try:
                html = await self.fetch_page_content(current_url, site)
                jobs = await self.extract_jobs(html, site)

                for job in jobs:
                    await self.process_job_listing(job, site)

                # Handle pagination
                if site.pagination:
                    page = await self.browser.newPage()
                    try:
                        await page.setContent(html)
                        next_url = await page.evaluate('''(selector) => {
                            const next = document.querySelector(selector);
                            return next ? next.href : null;
                        }''', site.pagination['next_button'])
                        current_url = urljoin(site.base_url, next_url) if next_url else None
                    finally:
                        await page.close()
                else:
                    current_url = None

            except Exception as e:
                logger.error(f"Error crawling {current_url}: {str(e)}")
                break

    async def run(self, job_sites: List[JobSite]):
        """Run the harvester for multiple job sites."""
        self.job_sites = job_sites
        async with self:
            tasks = [self.crawl_site(site) for site in job_sites]
            await asyncio.gather(*tasks)


# Example usage
if __name__ == "__main__":
    # Example job site configurations
    job_sites = [
        JobSite(
            name="microsoft",
            base_url="https://careers.microsoft.com/jobs/search",
            selectors={
                "job_list": ".job-card",
                "title": "h2",
                "location": ".location",
                "description": ".description",
                "link": "a",
                "company": ".company"
            },
            pagination={
                "next_button": ".pagination .next"
            },
            js_required=True,
            wait_for_selector=".job-card"
        ),
        # Add more job sites here
    ]

    # Initialize and run harvester
    harvester = JobHarvester(
        mongo_uri="mongodb://localhost:27017",
        redis_uri="redis://localhost:6379"
    )

    asyncio.run(harvester.run(job_sites))