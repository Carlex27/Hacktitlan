"""Render the same oriented page coordinates used by document evidence."""
from io import BytesIO
from pathlib import Path


def render_page_image(path: str | Path, page_number: int, bbox: dict[str, float] | None = None, *,
                      rotation: int = 0, expected_size: tuple[float, float] | None = None) -> bytes:
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        if not 1 <= page_number <= len(pdf.pages):
            raise ValueError("Página fuera del documento")
        page = pdf.pages[page_number - 1]
        if rotation not in {0, 90, 180, 270}:
            raise ValueError("Orientación OCR no comprobable")
        if page.bbox[0] != 0 or page.bbox[1] != 0:
            raise ValueError("Origen de página no compatible con las coordenadas normalizadas")
        width, height = (page.height, page.width) if rotation in {90, 270} else (page.width, page.height)
        if expected_size is not None and (abs(width - expected_size[0]) > 1 or abs(height - expected_size[1]) > 1):
            raise ValueError("Coordenadas OCR y PDF incompatibles")
        if bbox is not None and not rotation:
            page = page.crop((bbox["x0"], bbox["top"], bbox["x1"], bbox["bottom"]))
        resolution = 240 if bbox is not None else 120
        if page.width * page.height * (resolution / 72) ** 2 > 8_000_000:
            raise ValueError("Página demasiado grande para verificación visual")
        output = BytesIO()
        rendered = page.to_image(resolution=resolution, force_mediabox=True).original
        if rotation:
            rendered = rendered.rotate(rotation, expand=True)
            if bbox is not None:
                sx, sy = rendered.width / width, rendered.height / height
                if not (0 <= bbox["x0"] < bbox["x1"] <= width and 0 <= bbox["top"] < bbox["bottom"] <= height):
                    raise ValueError("Recorte fuera de la página orientada")
                rendered = rendered.crop((round(bbox["x0"] * sx), round(bbox["top"] * sy),
                                          round(bbox["x1"] * sx), round(bbox["bottom"] * sy)))
        rendered.save(output, format="PNG")
    return output.getvalue()
