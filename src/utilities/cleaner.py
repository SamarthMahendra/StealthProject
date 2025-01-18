
from abc import ABC, abstractmethod

class Cleaner(ABC):
    """
    Abstract class defining the interface for cleaning operations.
    """

    @abstractmethod
    def strip_unwanted_tags(self, html_content):
        """
        Remove unwanted tags and their content from the input.

        Args:
            html_content (str): The HTML code as a string.

        Returns:
            str: Content without unwanted tags.
        """
        pass

    @abstractmethod
    def remove_comments(self, html_content):
        """
        Remove all comments from the input.

        Args:
            html_content (str): The HTML code as a string.

        Returns:
            str: Content without comments.
        """
        pass

    @abstractmethod
    def retain_allowed_attributes(self, html_content):
        """
        Retain only allowed attributes ('class', 'id') in the input tags.

        Args:
            html_content (str): The HTML code as a string.

        Returns:
            str: Content with only allowed attributes.
        """
        pass

    def clean(self, html_content):
        """
        Clean the content by applying all cleaning methods in sequence.

        Args:
            html_content (str): The HTML code as a string.

        Returns:
            str: Fully cleaned content.
        """
        html_content = self.strip_unwanted_tags(html_content)
        html_content = self.remove_comments(html_content)
        html_content = self.retain_allowed_attributes(html_content)
        return html_content

