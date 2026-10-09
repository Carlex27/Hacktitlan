from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from backend.app.application.review_service import ReviewService
from backend.app.config import Settings
from backend.app.domain.enums import ApprovalStatus
from backend.app.domain.errors import ConflictError
from backend.app.infrastructure.database.models import (
    ClassificationCandidate, ClassificationResult, ClassificationRun, MillCertificate, Product,
)


@pytest.mark.parametrize("scenario", ["complete", "missing_product", "missing_heat", "foreign_product", "unselected", "missing_nico"])
def test_approval_requires_authorized_results_for_every_product_and_heat(scenario):
    run = ClassificationRun(id=12, certificate_id=4, approval_status="needs_review")
    certificate = MillCertificate(id=4, approval_status="needs_review")
    products = [Product(id=1, certificate_id=4, heat_id=10), Product(id=2, certificate_id=4, heat_id=20)]
    results = [ClassificationResult(id=i, product_id=i, outcome="classified", fraction="72091504", nico="01", details_json={}) for i in (1, 2)]
    heat_ids = [10, 20]
    selected = [1, 2]
    if scenario == "missing_product":
        results.pop()
    elif scenario == "missing_heat":
        heat_ids.append(30)
    elif scenario == "foreign_product":
        results[1].product_id = 3
    elif scenario == "unselected":
        selected.pop()
    elif scenario == "missing_nico":
        results[1].nico = None
    session = Mock(spec=Session)
    session.get.side_effect = lambda model, key: run if model is ClassificationRun else certificate
    session.scalars.side_effect = [Mock(all=Mock(return_value=items)) for items in (results, products, heat_ids, selected)]
    session.scalar.return_value = run.id
    service = ReviewService(Settings())
    if scenario == "complete":
        service.transition_classification(session, run_id=12, target=ApprovalStatus.APPROVED, person_name="Ana", reason="Revisado")
        assert run.approval_status == certificate.approval_status == "approved"
        session.add.assert_called_once()
    else:
        with pytest.raises(ConflictError) as error:
            service.transition_classification(session, run_id=12, target=ApprovalStatus.APPROVED, person_name="Ana", reason="Revisado")
        assert error.value.code == "classification_incomplete"
        assert run.approval_status == certificate.approval_status == "needs_review"
        session.add.assert_not_called()


@pytest.mark.parametrize("scenario", ["missing", "unknown", "conflict", "not_matched"])
def test_human_review_allows_missing_data_but_preserves_conflict_blocking(scenario):
    run = ClassificationRun(id=12, certificate_id=4, approval_status="needs_review")
    certificate = MillCertificate(id=4, approval_status="needs_review")
    product = Product(id=1, certificate_id=4, heat_id=10)
    result = ClassificationResult(id=1, product_id=1, outcome="classified", fraction="72091504", nico="01",
                                  details_json={"selected_candidate_id": 2})
    candidate = ClassificationCandidate(id=2, classification_result_id=1, details_json={
        "missing_fields": ["composition_pct.Cr"], "conflicts": ["coated"] if scenario == "conflict" else [],
    })
    session = Mock(spec=Session)
    session.get.side_effect = lambda model, key: {ClassificationRun: run, MillCertificate: certificate,
                                                  ClassificationCandidate: candidate}[model]
    session.scalars.side_effect = [Mock(all=Mock(return_value=items)) for items in ([result], [product], [10], [1])]
    session.scalar.side_effect = [99 if scenario == "not_matched" else None, run.id]
    service = ReviewService(Settings())
    if scenario in {"conflict", "not_matched"}:
        with pytest.raises(ConflictError):
            service.transition_classification(session, run_id=12, target=ApprovalStatus.APPROVED,
                                              person_name="Administrador", reason="Revisión humana completa")
        assert run.approval_status == "needs_review"
    else:
        service.transition_classification(session, run_id=12, target=ApprovalStatus.APPROVED,
                                          person_name="Administrador", reason="Revisión humana completa")
        assert run.approval_status == certificate.approval_status == "approved"
        assert candidate.details_json["missing_fields"] == ["composition_pct.Cr"]
        factor_query = str(session.scalar.call_args_list[0].args[0])
        assert "candidate_factors.outcome IN" in factor_query
