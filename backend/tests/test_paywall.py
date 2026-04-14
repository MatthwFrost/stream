from src.services.paywall import is_paywalled


def test_known_paywall_domain():
    assert is_paywalled("https://www.wsj.com/articles/some-article") is True
    assert is_paywalled("https://www.ft.com/content/some-article") is True
    assert is_paywalled("https://www.bloomberg.com/news/some-article") is True


def test_known_free_domain():
    assert is_paywalled("https://www.reuters.com/article/some-article") is False
    assert is_paywalled("https://www.bbc.com/news/some-article") is False


def test_unknown_domain_defaults_free():
    assert is_paywalled("https://randomnews.example.com/article") is False


def test_respects_header_override():
    assert is_paywalled(
        "https://free-site.com/article",
        headers={"X-Paywall": "true"},
    ) is True


def test_header_override_free():
    assert is_paywalled(
        "https://free-site.com/article",
        headers={"X-Paywall": "false"},
    ) is False
