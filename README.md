# Clasificador local LIGIE - Capítulo 72

Proyecto para extraer certificados de materiales y determinar de forma
explicable una fracción arancelaria mexicana y su NICO dentro del capítulo 72.

## Estado actual

La fase de descubrimiento y normalización inicial está en curso. Ya existe una
extracción reproducible del PDF proporcionado en
`data/ligie/chapter-72/source-provided/` y una propuesta de arquitectura en
`docs/`.

El documento fuente está marcado `SIN VIGENCIA`; los datos extraídos no deben
usarse en operaciones aduaneras hasta ser contrastados con fuentes oficiales.

## Regenerar la extracción

```powershell
python tools/extract_chapter72.py
```

El script conserva filas crudas, catálogo normalizado, notas y un reporte de
calidad para permitir auditoría.
