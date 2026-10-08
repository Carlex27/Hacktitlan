"""Versioned multilingual semantic dictionary and token classification for generic extraction."""

from __future__ import annotations

import re
import unicodedata

VOCABULARY_VERSION = "1.0.0"


def normalize_term(value: str) -> str:
    """Normalize text into NFKD lowercase stripped of accents and special punctuation."""
    normalized = unicodedata.normalize("NFKD", str(value).casefold())
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^\w]+", " ", without_marks, flags=re.UNICODE).strip()


METADATA_LABELS: dict[str, tuple[str, ...]] = {
    "certificate_no": (
        "certificate no", "cert no", "certificate number", "inspection certificate no",
        "no de certificado", "certificado no", "numero de certificado", "acta no",
        "证书编号", "证明书号", "质保书号",
    ),
    "supplier": (
        "mill", "manufacturer", "supplier", "maker", "producer", "fabricante",
        "proveedor", "planta", "molino", "制造厂", "生产厂", "制造者",
    ),
    "standard": (
        "standard", "specification", "spec", "grade", "norma", "especificacion",
        "grado", "calidad", "标准", "牌号", "执行标准",
    ),
    "issue_date": (
        "issue date", "date of issue", "delivery date", "date", "fecha de emision",
        "fecha", "fecha de entrega", "日期", "签发日期", "出厂日期",
    ),
    "customer": (
        "customer", "consignee", "buyer", "purchaser", "cliente", "destinatario",
        "comprador", "订货单位", "收货单位",
    ),
}

PRODUCT_ID_LABELS = (
    "coil", "roll", "plate", "placa", "sheet", "hoja",
    "coil no", "coil number", "coil id", "pack no", "package no", "bundle no",
    "bundle", "roll no", "item no", "lot no", "piece no", "rollo", "paquete",
    "bulto", "lote", "pieza", "rollo no", "no rollo", "no coil",
    "钢卷号", "卷号", "捆号", "件号",
)

HEAT_NO_LABELS = (
    "heat", "cast", "melt", "charge",
    "heat no", "heat number", "cast no", "melt no", "charge no", "colada",
    "numero de colada", "colada no", "no colada", "no heat",
    "炉号", "熔炼号", "浇铸号",
)

DIMENSION_LABELS: dict[str, tuple[str, ...]] = {
    "thickness_mm": ("thickness", "thick", "gauge", "espesor", "calibre", "厚度"),
    "width_mm": ("width", "ancho", "anchura", "宽度"),
    "length_m": ("length", "largo", "longitud", "长度"),
    "weight_kg": (
        "weight", "mass", "net weight", "gross weight", "peso", "peso neto",
        "peso bruto", "masa", "重量", "净重", "毛重",
    ),
}

ELEMENT_SYMBOLS: dict[str, str] = {
    # Carbon
    "c": "C", "carbon": "C", "carbono": "C", "碳": "C",
    # Silicon
    "si": "Si", "silicon": "Si", "silicio": "Si", "硅": "Si",
    # Manganese
    "mn": "Mn", "manganese": "Mn", "manganeso": "Mn", "锰": "Mn",
    # Phosphorus
    "p": "P", "phosphorus": "P", "fosforo": "P", "磷": "P",
    # Sulfur
    "s": "S", "sulfur": "S", "azufre": "S", "硫": "S",
    # Aluminium
    "als": "Al_soluble", "soluble al": "Al_soluble", "solubleal": "Al_soluble", "酸溶铝": "Al_soluble",
    "alt": "Al_total", "total al": "Al_total", "totalal": "Al_total", "全铝": "Al_total",
    "al": "Al_total", "aluminium": "Al_total", "aluminum": "Al_total", "aluminio": "Al_total", "铝": "Al_total",
    # Titanium
    "ti": "Ti", "titanium": "Ti", "titanio": "Ti", "钛": "Ti",
    # Copper
    "cu": "Cu", "copper": "Cu", "cobre": "Cu", "铜": "Cu",
    # Nickel
    "ni": "Ni", "nickel": "Ni", "niquel": "Ni", "镍": "Ni",
    # Chromium
    "cr": "Cr", "chromium": "Cr", "cromo": "Cr", "铬": "Cr",
    # Molybdenum
    "mo": "Mo", "molybdenum": "Mo", "molibdeno": "Mo", "钼": "Mo",
    # Boron
    "b": "B", "boron": "B", "boro": "B", "硼": "B",
    # Nitrogen
    "n": "N", "nitrogen": "N", "nitrogeno": "N", "氮": "N",
    # Vanadium
    "v": "V", "vanadium": "V", "vanadio": "V", "钒": "V",
    # Niobium / Columbium
    "nb": "Nb", "cb": "Nb", "niobium": "Nb", "columbium": "Nb", "niobio": "Nb", "铌": "Nb",
    # Calcium
    "ca": "Ca", "calcium": "Ca", "calcio": "Ca", "钙": "Ca",
}

MECHANICAL_LABELS: dict[str, tuple[str, ...]] = {
    "yield_strength_mpa": ("yield strength", "yield point", "proof stress", "limite elastico", "fluencia", "屈服强度"),
    "tensile_strength_mpa": ("tensile strength", "resistencia a la traccion", "resistencia traccion", "抗拉强度"),
    "elongation_pct": ("elongation", "alargamiento", "elongacion", "伸长率"),
    "hardness_hrb": ("hardness", "dureza", "硬度"),
}

DITTO_TOKENS = {'"', "''", "〃", "同上", "ditto", "do"}


def detect_scale_exponent(header_text: str) -> int | None:
    """Detect chemical scale exponent (e.g. 10^-4 -> -4, 10^-3 -> -3, % -> 0)."""
    normalized = header_text.lower().replace(" ", "")
    # Check 10^-4 or 10^-3 or 10^-2 patterns
    match_neg = re.search(r"10\^?[-−](\d+)", normalized)
    if match_neg:
        return -int(match_neg.group(1))

    # Unicode superscripts: 10⁻⁴, 10⁻³, 10⁻²
    if "10⁻⁴" in normalized:
        return -4
    if "10⁻³" in normalized:
        return -3
    if "10⁻²" in normalized:
        return -2

    # Multiplication forms: *10000 -> -4, *1000 -> -3, *100 -> -2
    if "*10000" in normalized or "x10000" in normalized or "/10000" in normalized:
        return -4
    if "*1000" in normalized or "x1000" in normalized or "/1000" in normalized:
        return -3
    if "*100" in normalized or "x100" in normalized or "/100" in normalized:
        return -2

    if "ppm" in normalized:
        return -4  # 1 ppm = 0.0001% = 10^-4 %

    if "%" in normalized or "wt%" in normalized or "mass%" in normalized:
        return 0

    return None


def match_column_semantic(header_cell: str) -> tuple[str, str | None, int | None]:
    """Classify a table header cell.

    Returns (category, canonical_key, scale_exponent)
    Categories:
    - "product_id"
    - "heat_no"
    - "dimension" (key in thickness_mm, width_mm, length_m, weight_kg)
    - "chemistry" (key is element symbol, e.g. "C", "Mn", "Al_soluble")
    - "mechanical" (key is yield_strength_mpa, tensile_strength_mpa, elongation_pct, hardness_hrb)
    - "unknown"
    """
    clean = normalize_term(header_cell)
    if not clean:
        return "unknown", None, None

    # Check Product ID
    if any(alias == clean or clean.startswith(alias) or clean.endswith(alias) for alias in PRODUCT_ID_LABELS):
        return "product_id", "product_id", None

    # Check Heat No
    if any(alias == clean or clean.startswith(alias) or clean.endswith(alias) for alias in HEAT_NO_LABELS):
        return "heat_no", "heat_no", None

    # Check Dimensions
    for dim_key, aliases in DIMENSION_LABELS.items():
        if any(alias == clean or clean.startswith(alias) or clean.endswith(alias) for alias in aliases):
            return "dimension", dim_key, None

    # Check Mechanical
    for mech_key, aliases in MECHANICAL_LABELS.items():
        if any(alias == clean or clean.startswith(alias) or clean.endswith(alias) for alias in aliases):
            return "mechanical", mech_key, None

    # Check Chemistry
    # Extract element candidates by looking at words or compact tokens
    exponent = detect_scale_exponent(header_cell)
    tokens = clean.split()
    for token in tokens:
        elem = ELEMENT_SYMBOLS.get(token)
        if elem:
            return "chemistry", elem, exponent

    # Check if whole clean string maps to element
    compact = clean.replace(" ", "")
    elem = ELEMENT_SYMBOLS.get(compact)
    if elem:
        return "chemistry", elem, exponent

    return "unknown", None, None
