import numpy as np
import pytest

from backend.app.infrastructure.ocr.table_refinement import is_ditto_image


def test_scale_crop_removes_rules_but_keeps_small_digit_strokes():
    from backend.app.infrastructure.ocr.table_refinement import _without_cell_rules

    crop = np.full((25, 30, 3), 255, dtype=np.uint8)
    crop[0] = crop[:, 0] = 0
    crop[7:13, 20:23] = 0
    cleaned = _without_cell_rules(crop)
    assert np.all(cleaned[4, 4:34] == 255)
    assert np.all(cleaned[4:29, 4] == 255)
    assert np.all(cleaned[11:17, 24:27] == 0)


def test_single_roll_rereads_chemical_cells_even_without_merged_lines():
    from backend.app.domain.document import BoundingBox, PageLayout, PageSource, TextBlock
    from backend.app.infrastructure.ocr.table_refinement import refine_cells
    from backend.app.certificate_parser.layout_rows import recover_rows

    def block(text, x, y):
        return TextBlock(1, text, BoundingBox(x - 4, y, x + 4, y + 6))

    blocks = [block('Pack No.', 20, 40), block('Heat No.', 20, 50),
              block('ROLL123456', 20, 100), block('2641568', 20, 107)]
    for element, x, scale in [('C', 100, '10-2'), ('Mn', 120, '10-2'),
                              ('P', 140, '10-3'), ('S', 160, '10-3'), ('Alt', 180, '10-3')]:
        blocks.extend([block(element, x, 40), block(scale, x, 50)])
    page = PageLayout(1, 250, 600, 0, PageSource.OCR, tuple(blocks))
    image = np.full((1200, 500, 3), 255, dtype=np.uint8)
    for x in [90, 110, 130, 150, 170, 190]:
        image[:, x * 2] = 0
    calls = []

    def recognize(crops):
        calls.append(len(crops))
        return [{'rec_text': value, 'rec_score': .99} for value in ['8', '34', '15', '8', '29']]

    refined = refine_cells(page, image, recognize, .5)
    rows, scales = recover_rows(refined)
    assert calls == [5]
    assert rows[0]['chemistry'] == {'C': '8', 'Mn': '34', 'P': '15', 'S': '8', 'Al_total': '29'}
    assert scales == {'C': -2, 'Mn': -2, 'P': -3, 'S': -3, 'Al_total': -3}
    assert all(original in refined.blocks for original in page.blocks)


@pytest.mark.parametrize('repeat', [True, False])
def test_two_short_strokes_are_repetition_but_two_numerals_are_not(repeat):
    crop = np.full((30, 40, 3), 255, dtype=np.uint8)
    height = 8 if repeat else 22
    crop[4:4 + height, 15:17] = 0
    crop[4:4 + height, 21:23] = 0
    crop[:, 0] = 0
    assert is_ditto_image(crop) is repeat
