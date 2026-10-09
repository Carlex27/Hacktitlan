import pytest

from backend.app.certificate_parser.generic_extractor import ColumnDefinition, GenericCertificateExtractor
from backend.app.certificate_parser.measurement_units import dimension_value
from backend.app.certificate_parser.vocabulary import detect_scale_exponent
from backend.app.domain.document import BoundingBox, DocumentLayout, PageLayout, PageSource, TableRegion


@pytest.mark.parametrize('value,header,length,expected', [
    ('0.0453"', 'Thickness', False, 1.15062),
    ('43.701"', 'Width', False, 1110.0054),
    ('1/8', 'Thickness (in)', False, 3.175),
    ('1 1/2 in', 'Width', False, 38.1),
    ('2', 'Width (ft)', False, 609.6),
    ('10 feet', 'Length', True, 3.048),
    ('1200', 'Length (mm)', True, 1.2),
    ('0,35', 'Thickness (mm)', False, .35),
    ('12 bananas', 'Width', False, None),
    ('1/0 in', 'Thickness', False, None),
])
def test_explicit_dimensions(value, header, length, expected):
    actual = dimension_value(value, header, length=length)
    assert actual is None if expected is None else actual == pytest.approx(expected)


def test_generic_converter_preserves_originals_and_internal_units():
    product = {'chemistry': {}}
    extractor = GenericCertificateExtractor()
    for key, value, header in [('thickness_mm', '0.0453"', 'Thickness'), ('width_mm', '43.701', 'Width (in)'), ('length_m', '10', 'Length (ft)')]:
        extractor._apply_value(product, ColumnDefinition(0, 'dimension', key, header=header), value)
    assert product['thickness_mm'] == pytest.approx(1.15062)
    assert product['width_mm'] == pytest.approx(1110.0054)
    assert product['length_raw'] == pytest.approx(3.048)
    assert product['raw_values']['thickness_mm'] == '0.0453"'


@pytest.mark.parametrize('header,exponent', [('C (%)', 0), ('C (% / 10^4)', -4), ('Mn (×10³)', -3), ('Si (/100)', -2), ('P (ppm)', -4), ('C', None)])
def test_explicit_chemical_scale(header, exponent):
    assert detect_scale_exponent(header) == exponent


def test_table_units_and_chemical_scales_are_normalized_once():
    table = TableRegion(1, BoundingBox(0, 0, 500, 200), (
        ('Coil No', 'Thickness (in)', 'Width (in)', 'Length (ft)', 'C (%)', 'Mn (% /1000)'),
        ('TATA1', '.0453', '43.701', '10', '.0023', '333'),
    ))
    result = GenericCertificateExtractor().extract(DocumentLayout('phone.pdf', 'hash', (
        PageLayout(1, 600, 800, 0, PageSource.DIGITAL, tables=(table,)),
    )))
    assert result.certificate is not None
    product = result.certificate['products'][0]
    assert product['thickness_mm'] == pytest.approx(1.15062)
    assert product['width_mm'] == pytest.approx(1110.0054)
    assert product['length_m'] == pytest.approx(3.048)
    assert product['composition_pct'] == {'C': .0023, 'Mn': .333}
    assert product['observations']['thickness_mm']['raw_value'] == '.0453'


def test_unordered_imperial_size_is_not_assumed_thickness_first():
    product = {'chemistry': {}}
    GenericCertificateExtractor()._apply_value(product, ColumnDefinition(0, 'dimension', 'thickness_mm', header='Dimensions'), '43.701" x 0.0453"')
    assert 'thickness_mm' not in product
    assert product['raw_values']['thickness_mm'] == '43.701" x 0.0453"'
