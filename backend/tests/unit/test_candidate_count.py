from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.app.application.review_service import ReviewService
from backend.app.config import Settings
from backend.app.domain.errors import ConflictError


@pytest.mark.parametrize("count", [1, 2, 3, 4])
def test_selection_accepts_up_to_three_candidates(count):
    result = SimpleNamespace(id=10, classification_run_id=20, details_json={})
    candidates = [SimpleNamespace(
        id=rank, rank=rank, classification_result_id=10, details_json={},
        fraction="72091701", nico="99", description="Prueba",
    ) for rank in range(1, count + 1)]
    session = MagicMock()
    session.scalar.side_effect = [result, None, None]
    session.get.side_effect = [candidates[0], SimpleNamespace(approval_status="pending_review")]
    session.scalars.return_value.all.return_value = candidates
    service = ReviewService(Settings())
    if count == 4:
        with pytest.raises(ConflictError) as error:
            service.select_classification_candidate(session, result_id=10, candidate_id=1,
                person_name="Revisor", reason="Verificación de evidencia")
        assert error.value.code == "valid_candidates_required"
        session.add.assert_not_called()
    else:
        selection = service.select_classification_candidate(session, result_id=10, candidate_id=1,
            person_name="Revisor", reason="Verificación de evidencia")
        assert selection.candidate_id == 1
        assert result.details_json["selection_required"] is False
