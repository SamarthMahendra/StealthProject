# producer.py
from tasks import scrape_job, ScraperPayload
from src.cache.Redis import Redis

def main():
    cache = Redis()
    queue = set(cache.get_list("jobs"))  # e.g., list of job URLs

    # Example config mapping selectors to the CSS for each field
    config = {
        "job_id": "#jobNumber",
        "title": ".jd__header--title",
        "location": [".addressCountry", "#job-location-name"],
        "department": "#job-team-name",
        "summary": "#jd-job-summary",
        "long_description": "#jd-description",
        "date": "#jobPostDate",
    }

    print(f"Found {len(queue)} job URLs to scrape.")

    for url in queue:
        payload = ScraperPayload(url=url, **config)
        # Enqueue a Celery task for each job
        scrape_job.delay(payload.__dict__)  # .delay() is what queues the task

    print("All jobs have been queued to Celery.")

if __name__ == "__main__":
    main()
