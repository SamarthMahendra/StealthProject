

import requests
from src.Database.database import Database
import time
db = Database()

# todo, check it last checked date is more than 1 week
# check if job is still available
query = "SELECT url FROM job_details where end_date is null"
result = db.execute_query(query)

for item in result[:10]:
    # sleep for a while
    time.sleep(1)
    url = item[0]
    try:
        response = requests.head(url, timeout=10)

        if response.status_code == 200:

            print(url, " is active.")
            # todo: add last checked date
        else:
            # update the status of the job
            query = "UPDATE job_details SET end_date = %s WHERE url = %s"
            params = (time.strftime('%Y-%m-%d'), url)
            db.insert_query(query, params)
    except requests.exceptions.RequestException as e:
        print(f"{url} Error checking URL: {e}")
