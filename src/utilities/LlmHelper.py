import os

from openai import OpenAI

class LlmHelper:

    def __init__(self):
        self.api_key = os.getenv('api_key')
        self.client = self.client = OpenAI(api_key=self.api_key)


    def query(self, str):
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": " You are a AI webscraper who gives reliable DOM selectors in Json"

                },
                {
                    "role": "user",
                    "content": str
                }
            ],
            temperature=1,
            max_tokens=256,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        assistant_response = response.choices[0].message.content
        print(assistant_response)
        return assistant_response

