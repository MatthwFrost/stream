from urllib.parse import urlparse

PAYWALL_DOMAINS = {
    "wsj.com",
    "ft.com",
    "bloomberg.com",
    "nytimes.com",
    "washingtonpost.com",
    "economist.com",
    "barrons.com",
    "hbr.org",
    "thetimes.co.uk",
    "telegraph.co.uk",
    "theathletic.com",
    "businessinsider.com",
    "seekingalpha.com",
    "foreignaffairs.com",
    "wired.com",
    "theatlantic.com",
}


def is_paywalled(url: str, headers: dict | None = None) -> bool:
    if headers:
        paywall_header = headers.get("X-Paywall", "").lower()
        if paywall_header == "true":
            return True
        if paywall_header == "false":
            return False

    hostname = urlparse(url).hostname or ""
    hostname = hostname.removeprefix("www.")

    return hostname in PAYWALL_DOMAINS
