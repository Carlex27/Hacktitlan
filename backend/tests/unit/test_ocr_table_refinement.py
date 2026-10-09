import numpy as np
import pytest

from backend.app.infrastructure.ocr.table_refinement import is_ditto_image


@pytest.mark.parametrize('repeat', [True, False])
def test_two_short_strokes_are_repetition_but_two_numerals_are_not(repeat):
    crop = np.full((30, 40, 3), 255, dtype=np.uint8)
    height = 8 if repeat else 22
    crop[4:4 + height, 15:17] = 0
    crop[4:4 + height, 21:23] = 0
    crop[:, 0] = 0
    assert is_ditto_image(crop) is repeat
