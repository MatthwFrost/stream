import re


def match_tags(text: str, tags: list[dict]) -> list[str]:
    """Match text against tag keyword lists. Returns list of matched tag names.

    Args:
        text: Article title or text to match against.
        tags: List of dicts with 'name' and 'keywords' keys.
    """
    matched = []
    text_lower = text.lower()
    for tag in tags:
        for keyword in tag["keywords"]:
            pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
            if re.search(pattern, text_lower):
                matched.append(tag["name"])
                break
    return matched
