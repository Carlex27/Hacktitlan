from datetime import datetime

import pytest

from backend.app.application.persistence import parse_certificate_date


@pytest.mark.parametrize("raw", ["JUN. 12, 2026", "JUN 12, 2026", "2026-06-12", "20260612"])
def test_exact_issue_dates(raw):
    assert parse_certificate_date(raw) == datetime(2026, 6, 12)


@pytest.mark.parametrize("raw", [None, "ON/ABOUT JUN. 28, 2026", "2026-13-12", "03/04/2026"])
def test_missing_approximate_or_ambiguous_dates_are_not_guessed(raw):
    assert parse_certificate_date(raw) is None
