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
        for tag in soup(['script', 'style', 'base', 'meta', 'svg']):
            tag.decompose()

        return str(soup)


    def remove_comments(self):
        soup = BeautifulSoup(self.html_content, 'html.parser')

        # Remove all comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        return str(soup)

    def retain_allowed_attributes(self):
        soup = BeautifulSoup(self.html_content, 'html.parser')

        # Retain only 'class' and 'id' attributes
        for tag in soup.find_all(True):  # True matches all tags
            allowed_attributes = {
                key: value
                for key, value in tag.attrs.items()
                if key in ['class', 'id']
            }
            tag.attrs = allowed_attributes

        return str(soup)

