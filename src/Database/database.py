# connect to postgresql database

from psycopg2 import connect
from psycopg2.extras import DictCursor
from psycopg2.extensions import connection as pg_connection
import os


class Database:

    def __init__(self):
        # host - localhost: 5432
        # user - postgres
        # database - Jobstats
        # password - os.getenv('DB_PASSWORD')
        self.connection = connect(
            host='localhost',
            port=5432,
            user='postgres',
            password=os.getenv('DB_PASSWORD'),
            database='postgres')
        self.cursor = self.connection.cursor(cursor_factory=DictCursor)

    def test_connection(self):
        self.cursor.execute("SELECT version();")
        record = self.cursor.fetchone()
        print("You are connected to - ", record, "\n")

    def __enter__(self) -> pg_connection:
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.commit()
        self.cursor.close()
        self.connection.close()

    def test_connection(self):
        self.cursor.execute("SELECT version();")
        record = self.cursor.fetchone()
        print("You are connected to - ", record, "\n")

    def execute_query(self, query: str):
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def execute_query_with_params(self, query: str, params: tuple):
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def execute_query_with_params_and_fetch_one(self, query: str, params: tuple):
        self.cursor.execute(query, params)
        return self.cursor.fetchone()

    def execute_query_with_params_and_fetch_all(self, query: str, params: tuple):
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def insert_query(self, query: str, params: tuple):
        self.cursor.execute(query, params)
        self.connection.commit()
        print("Data inserted successfully")


    def create_table_job_details(self):
        """
             config ={
        "job_id": "#jobNumber",
        "title": ".jd__header--title",
        "location": ".addressCountry",
        "department": "#job-team-name",
        "summary": "#jd-job-summary",
        "long_description": "#jd-description",
        "date": "#jobPostDate"
    }"""
        query = """
        CREATE TABLE IF NOT EXISTS job_details(
            job_id VARCHAR(255) PRIMARY KEY,
            title VARCHAR(255),
            location VARCHAR(255),
            department VARCHAR(255),
            summary TEXT,
            long_description TEXT,
            date DATE
        );
        """
        self.cursor.execute(query)
        self.connection.commit()
        print("Table created successfully")


# testing the connection
ob = Database()
ob.test_connection()

# # creating table
# ob.create_table_job_details()
#
