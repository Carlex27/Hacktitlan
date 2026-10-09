from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from backend.app.application.review_service import ReviewService
from backend.app.config import Settings
from backend.app.domain.enums import ApprovalStatus
from backend.app.domain.errors import ConflictError
from backend.app.infrastructure.database.models import ApprovalEvent, ClassificationRun, MillCertificate


@pytest.mark.parametrize("current", ["needs_review", "rejected", "draft"])
def test_draft_preserves_classification_and_updates_latest_certificate(current):
    run = ClassificationRun(id=12, certificate_id=4, approval_status=current, input_snapshot_json={"preserved": True})
    certificate = MillCertificate(id=4, approval_status=current)
    session = Mock(spec=Session)
    session.get.side_effect = lambda model, key: run if model is ClassificationRun else certificate
    session.scalar.return_value = run.id
    result = ReviewService(Settings()).transition_classification(session, run_id=12,
        target=ApprovalStatus.DRAFT, person_name="Ana", reason="Continuar revisión mañana")
    assert result is run
    assert run.approval_status == "draft"
    assert certificate.approval_status == "draft"
    assert run.input_snapshot_json == {"preserved": True}
    if current == "draft":
        session.add.assert_not_called()
    else:
        event = session.add.call_args.args[0]
        assert isinstance(event, ApprovalEvent)
        assert (event.from_status, event.to_status) == (current, "draft")
        assert event.person_name == "Ana"


def test_approved_run_cannot_be_returned_to_draft():
    session = Mock(spec=Session)
    run = ClassificationRun(id=12, certificate_id=4, approval_status="approved")
    session.get.return_value = run
    with pytest.raises(ConflictError):
        ReviewService(Settings()).transition_classification(session, run_id=12,
            target=ApprovalStatus.DRAFT, person_name="Ana", reason="Guardar cambios")
    assert run.approval_status == "approved"
    session.add.assert_not_called()


def test_draft_endpoint_is_typed_and_requires_actor(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from backend.app.api.app import create_app, get_session

    app = create_app(Settings(storage_root=tmp_path))
    app.dependency_overrides[get_session] = lambda: Mock(spec=Session)
    transition = Mock(return_value=ClassificationRun(id=12, certificate_id=4, approval_status="draft"))
    monkeypatch.setattr(ReviewService, "transition_classification", transition)
    client = TestClient(app)
    assert client.post("/api/v1/classification-runs/12/draft", json={"person_name": " ", "reason": "Guardar"}).status_code == 422
    transition.assert_not_called()
    response = client.post("/api/v1/classification-runs/12/draft", json={"person_name": "Ana", "reason": "Guardar"})
    assert response.status_code == 200
    assert response.json()["data"] == {"classification_run_id": 12, "approval_status": "draft"}
    schema = app.openapi()
    response_schema = schema["paths"]["/api/v1/classification-runs/{run_id}/draft"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert response_schema["$ref"].endswith("RunDecisionEnvelope")
