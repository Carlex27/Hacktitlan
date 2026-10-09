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
        "manufacturer", "supplier", "maker", "producer", "fabricante",
        "proveedor", "planta", "molino", "制造厂", "生产厂", "制造者",
    ),
    "standard": (
        "standard", "specification", "spec", "grade", "norma", "especificacion",
        "grado", "calidad", "标准", "牌号", "执行标准", "規格名稱", "规格名称",
    ),
    "issue_date": (
        "issue date", "date of issue", "fecha de emision", "fecha del acta", "签发日期",
    ),
    "shipping_date": ("shipping date", "shipment date", "fecha de embarque", "交运日期"),
    "delivery_date": ("delivery date", "fecha de entrega", "出厂日期"),
    "product_name": ("product description", "product name", "descripcion del producto", "producto declarado"),
    "customer": (
        "customer", "consignee", "buyer", "purchaser", "cliente", "destinatario",
        "comprador", "订货单位", "收货单位", "客户名称", "客戶名稱",
    ),
}

PRODUCT_ID_LABELS = (
    "coil", "roll", "plate", "placa", "sheet", "hoja",
    "coil no", "coil number", "coil id", "pack no", "package no", "bundle no",
    "bundle", "roll no", "item no", "lot no", "piece no", "rollo", "paquete",
    "bulto", "lote", "pieza", "rollo no", "no rollo", "no coil",
    "钢卷号", "卷号", "捆号", "件号",
    "product no", "product number", "label no", "material no", "产品序号", "物料号",
    "labelno", "產品序號",
)

HEAT_NO_LABELS = (
    "heat", "cast", "melt", "charge",
    "heat no", "heat number", "cast no", "melt no", "charge no", "colada",
    "numero de colada", "colada no", "no colada", "no heat",
    "炉号", "熔炼号", "浇铸号",
)

DIMENSION_LABELS: dict[str, tuple[str, ...]] = {
    "quantity": ("quantity", "qty", "件数", "數量"),
    "coating_superior_g_m2": ("superior", "top coating", "upper coating"),
    "coating_inferior_g_m2": ("inferior", "bottom coating", "lower coating"),
    "thickness_mm": ("thickness", "thick", "gauge", "espesor", "calibre", "厚度", "size", "dimensions", "规格"),
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
    "al": "Al_total", "a1": "Al_total", "aluminium": "Al_total", "aluminum": "Al_total", "aluminio": "Al_total", "铝": "Al_total",
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
    "yield_strength_mpa": ("yield strength", "yield point", "proof stress", "limite elastico", "fluencia", "屈服强度", "y s", "ys", "yp"),
    "tensile_strength_mpa": ("tensile strength", "resistencia a la traccion", "resistencia traccion", "抗拉强度", "t s", "ts"),
    "elongation_pct": ("elongation", "alargamiento", "elongacion", "伸长率", "el"),
    "hardness_hrb": ("hardness", "dureza", "硬度", "rb", "hrb"),
}

DITTO_TOKENS = {'"', "''", "〃", "同上", "ditto", "do", "“", "”", "″"}


def detect_scale_exponent(header_text: str) -> int | None:
    """Detect chemical scale exponent (e.g. 10^-4 -> -4, 10^-3 -> -3, % -> 0)."""
    normalized = header_text.lower().replace(" ", "")
    positive = re.search(r"[x×*/÷]10\^?([1-6])(?:\D|$)", normalized)
    if positive:
        return -int(positive.group(1))
    for power, superscript in enumerate("¹²³⁴⁵⁶", start=1):
        if re.search(r"[x×*/÷]10" + superscript, normalized):
            return -power
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
    def matches(alias: str) -> bool:
        compact = clean.replace(" ", "")
        return (clean == alias or clean.startswith(alias + " ") or clean.endswith(" " + alias)
                or compact == alias.replace(" ", ""))
    if clean in {"widt", "宽度", "寬度"}:
        return "dimension", "width_mm", None
    if clean in {"lengt", "長度"}:
        return "dimension", "length_m", None

    # Check Product ID
    if any(matches(alias) for alias in PRODUCT_ID_LABELS):
        return "product_id", "product_id", None

    # Check Heat No
    if any(matches(alias) for alias in HEAT_NO_LABELS):
        return "heat_no", "heat_no", None

    # Check Dimensions
    for dim_key, aliases in DIMENSION_LABELS.items():
        if any(matches(alias) for alias in aliases):
            return "dimension", dim_key, None

    # Check Mechanical
    for mech_key, aliases in MECHANICAL_LABELS.items():
        if any(matches(alias) for alias in aliases):
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
