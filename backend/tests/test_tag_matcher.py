from src.services.tag_matcher import match_tags


def test_matches_single_tag():
    tags = [
        {"name": "technology", "keywords": ["tech", "AI", "software"], "priority": 1},
    ]
    result = match_tags("New AI software released today", tags)
    assert result == ["technology"]


def test_matches_multiple_tags():
    tags = [
        {"name": "technology", "keywords": ["tech", "AI", "software"], "priority": 1},
        {"name": "politics", "keywords": ["election", "congress", "senate"], "priority": 1},
    ]
    result = match_tags("AI policy debated in congress", tags)
    assert "technology" in result
    assert "politics" in result


def test_no_match_returns_empty():
    tags = [
        {"name": "oil", "keywords": ["oil", "petroleum", "OPEC"], "priority": 1},
    ]
    result = match_tags("New smartphone announced", tags)
    assert result == []


def test_case_insensitive_matching():
    tags = [
        {"name": "technology", "keywords": ["AI"], "priority": 1},
    ]
    result = match_tags("ai is changing the world", tags)
    assert result == ["technology"]


def test_word_boundary_matching():
    """'oil' should not match 'soiled' or 'foil'."""
    tags = [
        {"name": "oil", "keywords": ["oil"], "priority": 1},
    ]
    assert match_tags("oil prices rise", tags) == ["oil"]
    assert match_tags("the soiled ground", tags) == []
