from src.utilities.cleaner import Cleaner
from bs4 import BeautifulSoup, Comment


class HTMLCleaner(Cleaner):
    """
    Concrete implementation of the Cleaner abstract class for HTML content.
    """

    def __init__(self, html_content):
        self.html_content = html_content

    def strip_unwanted_tags(self):
        soup = BeautifulSoup(self.html_content, 'html.parser')

        # Remove unwanted tags and their content
        for tag in soup(['script', 'fieldset', 'form', 'style', 'option', 'base', 'meta', 'svg', 'header', 'footer', 'nav', 'aside', 'noscript', 'input', 'title', 'button', 'li']):
            tag.decompose()

        self.html_content = str(soup)
        return str(soup)


    def remove_comments(self):
        soup = BeautifulSoup(self.html_content, 'html.parser')

        # Remove all comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        self.html_content = str(soup)
        return str(soup)

    def retain_allowed_attributes(self):
        soup = BeautifulSoup(self.html_content, 'html.parser')

        tags = set()
        # Retain only 'class' and 'id' attributes
        for tag in soup.find_all(True):  # True matches all tags
            # print(tag)
            tags.add(tag.name)
            allowed_attributes = {
                key: value
                for key, value in tag.attrs.items()
                if key in ['class', 'id']
            }
            tag.attrs = allowed_attributes
        print("ALL UNIQUE TAGS: ", tags)
        self.html_content = str(soup)
        return str(soup)


    def return_only_body(self):
        soup = BeautifulSoup(self.html_content, 'html.parser')
        body = soup.find('body')
        # remove all attributes from the body tag
        body.attrs = {}
        self.html_content = str(body)
        return str(body)


