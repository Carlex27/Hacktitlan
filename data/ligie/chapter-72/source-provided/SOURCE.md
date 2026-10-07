# Fuente proporcionada: capítulo 72

- Archivo original: `C:\Users\ofici\Downloads\LIGIE-UNIFICADA-ACERO.pdf`
- SHA-256: `756ed9e9d43676fe973e03948f3b299d3eaac998a3d13fdea7ba109e33786155`
- Páginas del PDF: 50
- Notas del capítulo 72: páginas PDF 5 a 11
- Tabla del capítulo 72: páginas PDF 12 a 50
- Estado jurídico: **no verificado**. El documento lleva la marca visible `SIN VIGENCIA`.

Los archivos de esta carpeta son una extracción fiel de la fuente proporcionada,
no una declaración de vigencia. Antes de usar las reglas en producción habrá que
contrastarlas con el Decreto LIGIE, los acuerdos NICO y sus modificaciones del DOF.

## Archivos generados

- `catalog.csv`: catálogo tabular para revisión humana y carga inicial.
- `catalog.json`: el mismo catálogo con estructura jerárquica.
- `classification-notes.json`: reglas explícitas de las notas del capítulo.
- `notes-pages-5-11.txt`: transcripción de respaldo de las notas.
- `raw-table-rows.json`: extracción sin normalizar para auditoría.
- `qa-report.json`: conteos y anomalías detectadas automáticamente.

## Anomalía visible de la fuente

En la página PDF 38, bajo la subpartida `7219.34`, aparece la fracción
`7219.35.02`; después vuelve a aparecer `7219.35.02` bajo `7219.35`, con otra
descripción y otros NICO. La extracción conserva ambas apariciones y el reporte
de QA las marca como duplicadas. No debe corregirse por intuición: se debe
resolver contra la publicación oficial vigente.
