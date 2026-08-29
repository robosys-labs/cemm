"""Current absence contract for the retired legacy candidate API."""


def test_legacy_candidate_api_is_absent():
    """The package must not export CandidateGenerator."""
    import cemm_authoritative_hybrid as package
    assert not hasattr(package, "CandidateGenerator")
