import pytest
from pydantic import ValidationError
from backend.app.api.schemas import CandidateSelectionRequest


@pytest.mark.parametrize("codes", [
    {}, {"fraction": "72091701"}, {"fraction": "72091701", "nico": "1"},
    {"fraction": "7209.1701", "nico": "01"}, {"fraction": "72091701", "nico": "٠١"},
    {"candidate_id": 1, "fraction": "72091701", "nico": "01"},
])
def test_manual_request_rejects_missing_mixed_and_invalid_codes(codes):
    with pytest.raises(ValidationError):
        CandidateSelectionRequest(person_name="Administrador", reason="Revisión", **codes)


def test_manual_request_preserves_leading_zero_nico_and_candidate_compatibility():
    request = CandidateSelectionRequest(person_name="Administrador", reason="Revisión", fraction="72091701", nico="01")
    assert request.nico == "01" and request.candidate_id is None
    assert CandidateSelectionRequest(person_name="Administrador", reason="Revisión", candidate_id=7).candidate_id == 7
