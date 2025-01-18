from src.utilities.html_cleaner import HTMLCleaner


def test_html_cleaner():
    """
     Test the HTMLCleaner class
    """
    html = """
    <html>
    <head>
        <title>Test Page</title>
    </head>
    <body>
        <div class="content">
            <p>This is a test page.</p>
            <script>alert('Hello');</script>
            <style>.hidden { display: none; }</style>
            <meta name="description" content="This is a test page">
        </div>
    </body>
    </html>
    """
    cleaner = HTMLCleaner(html)
    cleaned_html = cleaner.strip_unwanted_tags()
    assert '<script>' not in cleaned_html
    assert '<style>' not in cleaned_html
    assert '<meta>' not in cleaned_html
    cleaned_html = cleaner.remove_comments()
    assert '<!--' not in cleaned_html

    cleaned_html = cleaner.retain_allowed_attributes()
    assert 'class' in cleaned_html


