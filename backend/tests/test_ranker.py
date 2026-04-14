import math
from datetime import datetime, timezone, timedelta
from src.workers.ranker import compute_relevance_score


def test_high_tag_match_high_authority():
    score = compute_relevance_score(
        matched_tag_count=3,
        max_possible_tags=4,
        tag_priority_sum=3,
        max_priority_sum=4,
        source_authority=1.0,
        article_age_hours=0.5,
    )
    assert score > 0.8


def test_no_tags_low_authority_old():
    score = compute_relevance_score(
        matched_tag_count=0,
        max_possible_tags=4,
        tag_priority_sum=0,
        max_priority_sum=4,
        source_authority=0.2,
        article_age_hours=48.0,
    )
    assert score < 0.2


def test_recency_matters():
    recent = compute_relevance_score(
        matched_tag_count=1,
        max_possible_tags=4,
        tag_priority_sum=1,
        max_priority_sum=4,
        source_authority=0.5,
        article_age_hours=0.1,
    )
    old = compute_relevance_score(
        matched_tag_count=1,
        max_possible_tags=4,
        tag_priority_sum=1,
        max_priority_sum=4,
        source_authority=0.5,
        article_age_hours=24.0,
    )
    assert recent > old


def test_score_between_0_and_1():
    score = compute_relevance_score(
        matched_tag_count=2,
        max_possible_tags=5,
        tag_priority_sum=2,
        max_priority_sum=5,
        source_authority=0.7,
        article_age_hours=6.0,
    )
    assert 0.0 <= score <= 1.0
