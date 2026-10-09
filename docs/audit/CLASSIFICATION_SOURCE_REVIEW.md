# Revisión de reglas contra la fuente proporcionada

Fecha: 8 de octubre de 2026. Alcance: motor de laminados planos del capítulo 72,
catálogo extraído, candidatos, factores, aprobación y navegación normativa.
No es una certificación de vigencia ni una validación integral de todas las
mercancías del capítulo. La fuente tiene 50 páginas y marca «SIN VIGENCIA»;
el hash del PDF coincide con el registrado en `SOURCE.md`.

## Hallazgos y correcciones

| Regla | Hallazgo | Resultado del cambio | Página PDF |
| --- | --- | --- | --- |
| Nota 1(f), 16 umbrales | Los porcentajes y `>=` coinciden con el PDF; Ti >= 0.05% y B >= 0.0008% | Pruebas debajo/en/encima de todos los límites; inoxidable conserva prioridad | 7 |
| Demás elementos | Se ignoraban elementos individuales informados fuera de la lista principal | Elementos adicionales >= 0.1% demuestran aleación, excluyendo Fe, C, N, P y S; se preserva el símbolo original | 7 |
| Al soluble | Podía probar aleación pero faltaba en los factores explicativos | Se conserva su valor y evidencia; un Al soluble bajo no demuestra Al total bajo | 7 |
| Carbono ausente | Con los demás elementos bajos podía declararse sin alear | Bloqueo hasta informar C | 6 |
| Nota 1(k) | No se comprobaban proporciones de productos sin enrollar | Conflicto si no cumplen anchura/espesor | 8 |
| 7210.49.99 | Se inventaban límites de 0.35 y 1 mm y NICO 03/04 | 01: espesor < 3 mm y deformación >= 275 MPa; 02: alta resistencia; 99 exige descartar ambos | 23 |
| 7210.41 | No se distinguían las dos caras | 7210.41.01/99 según ambas caras; ausencia no equivale a falso | 23 |
| Recubrimiento por cara | Una cara ausente se interpretaba como sin revestir | Se distingue una cara desconocida de una cara expresamente con cero | 22–27 |
| 7210.61.01 | Se devolvía NICO 01 inexistente | NICO 00 | 23 |
| 7210.50, 7210.69, 7210.70, 7210.90 y 7212 | Varios NICO 00 inexistentes y categorías residuales sin comprobar | Fracción candidata y NICO pendientes de calificador; no se declaran demostrados | 22–27 |
| 7211.13.01 | Bastaba indicar laminado en cuatro caras | Comprueba ancho > 150, espesor >= 4, sin enrollar y sin relieve | 24 |
| 7211.14/19 | Se usaba carbono para NICO definidos por fleje/chapa/enrollado | Se eliminan reglas de carbono; 7211.14.91.03 corresponde a enrollados; otras condiciones necesitan tipo de producto | 25 |
| 7211.23/29 | Se aplicaba espesor 0.35 mm inventado | Flejes >= 0.05 mm; chapas > 0.46 y <= 3.4 mm; se exige distinguir fleje/chapa | 25–26 |
| 7219, series AISI | Se inferían series con Ni >= 8, Cr >= 16 o Mn >= 5; códigos incorrectos | Serie explícita; en 7219.13/14/22/33, 200→01, 300→02, 400→03 | 36–38 |
| 7219.12.02 | Se usaba serie AISI para NICO dimensional | 01: espesor <= 6 y anchura 710–1350; 99: complemento | 36 |
| 7219.31.01 | Se usaba serie AISI para «enrollados» | 01: enrollado; 99: sin enrollar | 37 |
| 7219.32.02 | Se omitían series y frontera de 4 mm | <= 4: 200→02, 300→03, 400→04; > 4: 200→91, 300→92, 400→93 | 37–38 |
| 7220.11/12 | Se devolvía NICO 99 inexistente | NICO 00 | 39 |
| 7225.92.01 | Se devolvía NICO 00 inexistente | 01: alta resistencia; 99: debajo de 355 MPa; proceso ausente en revisión | 44 |
| 7225.50.91 | Presencia de datos podía marcar condiciones no comprobadas como cumplidas | Comparaciones explícitas de B, dimensiones y excepciones; «los demás» exige excluir especialidades; porcelanizable general no se confunde con partes expuestas | 43–44 |
| 7225.30/40 y 7226 | Se elegía 99 sin demostrar exclusiones; revestido estrecho podía ir a laminado simple | NICO pendiente; revestidos estrechos van a 7226.99 como candidatos | 42–47 |
| Evidencia normativa | Cada factor apuntaba a la tabla del NICO, incluso para Ti | Química→nota página 7 y región real; fracción/NICO→su entrada; PDF incluido y verificado al servirlo | 7 y tabla |
| Aprobación | Sólo se consultaban faltantes en detalles del candidato | También se rechazan factores obligatorios no demostrados | — |

## Tres sugerencias

Se conservan como máximo tres combinaciones distintas existentes y compatibles
con lo comprobado. Una opción condicional debe mostrar qué falta; no equivale
a una clasificación demostrada. Si hay menos de tres, se informa el número real
y se mantiene `needs_review`, conforme al requisito existente. Una clasificación
única correcta puede quedar bloqueada permanentemente por ese requisito: pedir
tres opciones no crea tres alternativas jurídicas. Hace falta decidir el flujo
de excepción para resultados únicos, sin rellenar con incompatibles.

## Brechas abiertas que impiden declarar todas las reglas correctas

1. **Vigencia:** contrastar el catálogo completo con Decreto LIGIE, acuerdos NICO
   y modificaciones aplicables a la fecha de operación. Se consultó el portal
   oficial SNICE como punto de entrada; no se sustituyó la fuente ni se certificó
   vigencia: https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html.
2. **Anomalía 7219.35.02:** duplicada en páginas 38–39 bajo subpartidas distintas.
   Sigue bloqueada; resolver con publicación oficial, sin corregir por intuición.
3. **Aceros especiales:** las banderas de magnético, rápido y herramienta aún
   requieren verificación química completa contra notas de páginas 10–11,
   incluidas exclusiones y precedencia. W/kg e inducción no sustituyen esa
   definición. NICO 7225.30/40 y 7226.91/92 necesitan predicados completos.
4. **Tipo de producto y usos:** falta captura auditada de fleje/chapa/desbaste,
   porcelanizable general, acabado, temple ASTM y usos expresamente definidos
   en el catálogo. La etiqueta comercial no basta. Los factores sin condición
   comprobada permanecen desconocidos y no son aprobables.
5. **Procesos y formas:** la definición de plano no modela todavía formas no
   rectangulares, artículos ya manufacturados, todo proceso posterior o metal
   férreo predominante en chapados. No existe cobertura del capítulo completo.
6. **Interfaz:** sigue pendiente la pantalla de tres sugerencias y el visor con
   resaltado. El backend proporciona URL/página/región; todavía no existe un
   botón operativo que abra esa región en la aplicación.

## Evidencia y verificaciones

La batería dedicada revisa los 16 umbrales y sus tres fronteras, carbono ausente,
otros elementos, Al soluble, series AISI, galvanizado, definición dimensional,
páginas distintas por factor, integridad del archivo, descarga y OpenAPI.
Las pruebas antiguas que afirmaban reglas distintas al PDF se actualizaron.
Validación final: `pytest -q` pasó con 325 pruebas y dos advertencias del runtime
(deprecación de TestClient y ausencia de ccache para Paddle). La prueba de
integración en PostgreSQL comprueba selección auditada y rechazo de aprobación
con factor normativo desconocido. `compileall` y `git diff --check` pasaron.
No se probó un visor frontend ni se certificó vigencia legal.

El hash reproducible del motor incluye también `nico_rules.py`; ejecuciones con
otro código histórico no se reproducen fingiendo que usan las mismas reglas.
El catálogo original se conserva íntegro, incluida su anomalía.
