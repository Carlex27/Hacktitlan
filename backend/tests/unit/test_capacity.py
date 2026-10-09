from pathlib import Path

import pytest

from backend.app.operations.capacity import CapacityExtractor, summarize
from backend.app.operations.volume_seed import seed_volume
from backend.app.config import Settings


def test_latency_summary_preserves_missing_measurements_and_nearest_rank_p95():
    assert summarize([])["p95_ms"] is None
    summary = summarize(list(range(1, 21)))
    assert summary == {"samples": 20, "median_ms": 10.5, "p95_ms": 19, "max_ms": 20}


def test_daily_and_burst_normalized_fixtures_have_requested_heat_counts():
    daily = CapacityExtractor()
    counts = [len(daily.analyze_pdf(Path(f"fixture-{i}.pdf"))["certificate"]["products"]) for i in range(6)]
    assert counts == [10, 11, 12, 13, 14, 15]
    result = CapacityExtractor(15).analyze_pdf(Path("burst.pdf"))["certificate"]
    assert len({product["heat_no"] for product in result["products"]}) == 15
    assert len({product["product_id"] for product in result["products"]}) == 15


@pytest.mark.parametrize("certificates,heats", [(0,15), (18251,15), (1,0), (1,16)])
def test_seed_rejects_invalid_volume(certificates, heats):
    with pytest.raises(ValueError, match="Volumen"):
        seed_volume(Settings(), certificates, heats)
