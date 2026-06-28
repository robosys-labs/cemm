import pytest
from cemm.types.claim import Claim, ClaimStatus


class TestClaim:
    def test_create_minimal(self):
        c = Claim(id="c1", subject_entity_id="e1", predicate="likes", source_id="s", domain="d")
        assert c.status == ClaimStatus.ACTIVE
        assert c.confidence == 0.5

    def test_claim_status_values(self):
        assert ClaimStatus.ACTIVE.value == "active"
        assert ClaimStatus.DISPUTED.value == "disputed"
