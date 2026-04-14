# backend/tests/test_scraper_agent.py
from src.workers.agents.scraper import parse_html_articles


SAMPLE_HTML = """
<html>
<body>
<article>
    <h2 class="title"><a href="https://example.com/article-1">Breaking News Story</a></h2>
    <span class="author">John Smith</span>
    <time datetime="2026-04-10T08:00:00Z">April 10, 2026</time>
</article>
<article>
    <h2 class="title"><a href="https://example.com/article-2">Another Story</a></h2>
    <span class="author">Jane Doe</span>
    <time datetime="2026-04-10T07:00:00Z">April 10, 2026</time>
</article>
</body>
</html>
"""


def test_parse_html_articles():
    config = {
        "article_selector": "article",
        "title_selector": "h2.title a",
        "link_selector": "h2.title a",
        "link_attr": "href",
        "author_selector": "span.author",
        "time_selector": "time",
        "time_attr": "datetime",
    }
    articles = parse_html_articles(SAMPLE_HTML, config, source_name="ExampleNews")
    assert len(articles) == 2
    assert articles[0].title == "Breaking News Story"
    assert articles[0].url == "https://example.com/article-1"
    assert articles[0].author == "John Smith"
    assert articles[0].source_name == "ExampleNews"


def test_parse_html_handles_missing_fields():
    html = """
    <html><body>
    <article>
        <h2 class="title"><a href="https://example.com/a1">Title Only</a></h2>
    </article>
    </body></html>
    """
    config = {
        "article_selector": "article",
        "title_selector": "h2.title a",
        "link_selector": "h2.title a",
        "link_attr": "href",
        "author_selector": "span.author",
        "time_selector": "time",
        "time_attr": "datetime",
    }
    articles = parse_html_articles(html, config, source_name="Test")
    assert len(articles) == 1
    assert articles[0].title == "Title Only"
    assert articles[0].author is None
