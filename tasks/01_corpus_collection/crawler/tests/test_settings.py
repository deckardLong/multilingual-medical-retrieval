from corpus_crawler.settings import load_settings


def test_member_b_assignment_contains_exactly_53_domains() -> None:
    settings = load_settings()
    assert settings.owner == "b"
    assert len(settings.domains) == 53
