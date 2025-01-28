# tasks.py
import time
import requests
from bs4 import BeautifulSoup
from celery import Celery
from dataclasses import dataclass
from typing import Optional
import os
from Database.database import Database
import sys
from prometheus_client import Counter, Gauge, start_http_server
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'Database')))

# (Optional) Ensure Celery sees your config file
os.environ.setdefault('CELERY_CONFIG_MODULE', 'celeryconfig')

app = Celery("scraper")
app.config_from_envvar('CELERY_CONFIG_MODULE')  # or directly: app.config_from_object('celeryconfig')




TASK_SUCCESS = Counter('celery_task_success_total', 'Total number of successfully executed tasks')
TASK_FAILURE = Counter('celery_task_failure_total', 'Total number of failed tasks')
TASK_DURATION = Gauge('celery_task_duration_seconds', 'Task execution duration in seconds')
TASK_IN_PROGRESS = Gauge('celery_tasks_in_progress', 'Number of tasks currently being processed')


#
# # Start Prometheus metrics server
# start_http_server(8000)  # Exposes metrics on localhost:8000

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

def get_inner_text(soup: BeautifulSoup, selector: str) -> str:
    """
    Given a CSS selector, find the first matching element in `soup`
    and return its text. Otherwise return an empty string.
    """
    if not selector:
        return ""
    element = soup.select_one(selector)
    return element.get_text(strip=True) if element else ""

@app.task
def scrape_job(payload_dict):
    """
    Celery task to scrape a single job URL and insert into the DB.
    `payload_dict` is a dictionary version of ScraperPayload.
    """

    # Convert dict back to ScraperPayload
    payload = ScraperPayload(**payload_dict)

    start_time = time.time()  # Start timing
    TASK_IN_PROGRESS.inc()  # Increment tasks in progress
    try:

        db = Database()

        # Skip if already in DB
        query = "SELECT * FROM job_details WHERE url = %s"
        params = (payload.url.strip(),)
        result = db.execute_query_with_params_and_fetch_one(query, params)
        if result:
            print(f"[SKIP] Already scraped {payload.url}")
            return

        # Synchronous HTTP request (using requests)
        response = requests.get(payload.url, timeout=10)
        response.raise_for_status()
        html = response.text

        soup = BeautifulSoup(html, "html.parser")

        # Extract info
        job_id = get_inner_text(soup, payload.job_id) or None
        title = get_inner_text(soup, payload.title) or None

        # If location is a list of selectors, try them in order
        location = None
        if isinstance(payload.location, list):
            for loc_sel in payload.location:
                location = get_inner_text(soup, loc_sel)
                if location:
                    break
        else:
            location = get_inner_text(soup, payload.location)
        location = location or None

        department = get_inner_text(soup, payload.department) or None
        summary = get_inner_text(soup, payload.summary) or None
        long_desc = get_inner_text(soup, payload.long_description) or None
        date_val = get_inner_text(soup, payload.date) or None

        # Insert data into DB
        query = """
            INSERT INTO job_details (job_id, title, location, department, summary, long_description, date, end_date, url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (job_id, title, location, department, summary, long_desc, date_val, None, payload.url)
        db.insert_query(query, params)

        print(f"[DONE] Scraped {payload.url}")
        TASK_SUCCESS.inc()  # Increment successful tasks

    except Exception as e:
        print(f"Error scraping {payload.url}: {e}")
        TASK_FAILURE.inc()

    finally:
        duration = time.time() - start_time
        TASK_DURATION.set(duration)  # Record task duration
        TASK_IN_PROGRESS.dec()  # Decrement tasks in progress


from celery.app.control import Inspect

TASK_QUEUE_SIZE = Gauge('celery_task_queue_size', 'Number of tasks in the Celery queue')

@app.task
def update_queue_size():
    inspect = app.control.inspect()
    active_queues = inspect.active_queues()
    if active_queues:
        for queue_name, queue_info in active_queues.items():
            TASK_QUEUE_SIZE.labels(queue_name=queue_name).set(len(queue_info))

