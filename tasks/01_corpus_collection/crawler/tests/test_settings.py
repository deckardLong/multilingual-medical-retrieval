from corpus_crawler.settings import load_settings


def test_member_a_assignment_contains_exactly_44_domains() -> None:
    settings = load_settings()
    assert settings.owner == "a"
    assert len(settings.domains) == 44
