from dataclasses import replace

import pytest

from backend.app.application.certificate_extraction import CertificateExtractionService
from backend.app.certificate_parser.templates import TemplateConfiguration, extractor_hash
from backend.app.certificate_parser.template_recognition import TemplateSnapshot, extract_template, matches_template
from backend.app.domain.document import BoundingBox, TextBlock
from backend.tests.unit.test_format_templates import layout, configuration, REGION


def example():
    doc = layout()
    return replace(doc, pages=(replace(doc.pages[0], blocks=(TextBlock(1, "PILOT   certificate Coil Heat", BoundingBox(0, 0, 99, 9)),)),))


def snapshot(identifier=1):
    config = configuration().model_dump(mode="json")
    config["recognition"] = [{"page_number": 1, "region": REGION, "text": text} for text in ("Pilot certificate", "Coil Heat")]
    config = TemplateConfiguration.model_validate(config)
    return TemplateSnapshot(version_id=identifier, format_id=identifier, version_number=1,
                            configuration=config, configuration_sha256=config.sha256, extractor_sha256=extractor_hash())


def test_recognition_requires_all_stable_anchors_and_valid_extractor():
    snap = snapshot()
    assert matches_template(example(), snap.configuration)
    assert not matches_template(layout(), snap.configuration)
    assert not matches_template(example(), TemplateConfiguration())
    snap.extractor_sha256 = "old"
    with pytest.raises(ValueError):
        extract_template(example(), snap)


def test_automatic_ambiguous_and_explicit_template_selection():
    class Reader:
        def read(self, path, **kwargs):
            return example()
    service = CertificateExtractionService(Reader())
    candidates = [snapshot().model_dump(mode="json")]
    result = service.analyze_pdf("example.pdf", template_candidates=candidates)
    assert result["adapter"] == "user_template" and result["status"] == "needs_review"
    result = service.analyze_pdf("example.pdf", template_candidates=[*candidates, snapshot(2).model_dump(mode="json")])
    assert result["adapter"] == "ambiguous_user_templates" and result["status"] == "needs_review"
    candidates[0]["configuration"]["recognition"][0]["text"] = "Other manufacturer"
    candidates[0]["configuration_sha256"] = TemplateConfiguration.model_validate(candidates[0]["configuration"]).sha256
    result = service.analyze_pdf("example.pdf", template_candidates=candidates, explicit_template=True)
    assert result["status"] == "needs_review" and "certificate" not in result
