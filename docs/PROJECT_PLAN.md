# Plan del proyecto

## 1. Objetivo

Construir una aplicación de escritorio completamente local que reciba uno o
varios certificados de materiales en PDF, separe los productos o rollos,
extraiga sus propiedades, determine la fracción arancelaria y el NICO del
capítulo 72, y genere un reporte explicable y auditable.

El modo normal debe ser automático. La revisión humana será una excepción para
documentos incompletos, ilegibles, contradictorios o fuera del capítulo 72.

## 2. Principios no negociables

1. La decisión final proviene de reglas deterministas, no de una respuesta libre
   de un modelo de lenguaje.
2. Toda clasificación conserva la versión de reglas, datos de entrada, ruta de
   decisión y evidencia documental.
3. Un dato ausente nunca se interpreta como cero ni como “no aplica”.
4. La aplicación no inventa valores para resolver una rama.
5. Las reglas tienen vigencia temporal y pruebas de frontera.
6. El sistema distingue entre confianza de extracción y certeza de
   clasificación.
7. El PDF proporcionado es material de trabajo, no fuente jurídica vigente.

## 3. Alcance funcional

### Entrada

- Uno o varios PDF digitales o escaneados.
- Certificados multipágina en inglés o chino; español como idioma adicional.
- Varios rollos, coladas, lotes o productos en el mismo archivo.
- Captura manual de datos faltantes con registro de quién los agregó.

### Procesamiento

- Detección de PDF digital frente a escaneado.
- Extracción de texto, tablas y coordenadas.
- OCR local cuando sea necesario.
- Separación por `heat`, `coil`, `lot`, `item` o equivalente.
- Normalización de elementos químicos, unidades, dimensiones, normas y grados.
- Validación física y química.
- Clasificación completa dentro del capítulo 72.
- Generación de alternativas sólo cuando la evidencia sea insuficiente.

### Salida

- Fracción arancelaria de ocho dígitos.
- NICO de dos dígitos.
- Descripción oficial asociada.
- Datos usados y datos faltantes.
- Explicación de cada regla evaluada.
- Referencia a página y región del certificado de cada valor.
- Exportación a XLSX, CSV y PDF.
- Historial de ejecuciones y correcciones.

## 4. Lo que un certificado químico no garantiza

Todo el capítulo 72 incluye fundición en bruto, ferroaleaciones, productos de
reducción directa, desperdicios y chatarra, lingotes, productos intermedios,
planos, alambrón, barras, perfiles y alambre. La composición química por sí sola
no separa todas esas ramas.

El modelo de entrada debe poder representar también:

- forma física y sección transversal;
- método de producción;
- enrollado o no;
- trabajo en caliente o en frío;
- decapado, chapado o revestimiento;
- ancho, espesor, diámetro y otras dimensiones;
- propiedades mecánicas;
- norma, grado y serie;
- uso previsto cuando una descripción NICO lo exige.

Si algún proveedor no incluye uno de estos datos, la aplicación deberá buscarlo
en una orden de compra, ficha técnica o captura complementaria. “Tomar todos los
elementos químicos presentes” es necesario, pero no suficiente.

## 5. Fases

### Fase 0 - Autoridad y corpus

- Obtener la publicación oficial vigente del capítulo 72 y los NICO.
- Registrar cada fuente con hash, fecha de publicación y vigencia.
- Resolver las anomalías del PDF proporcionado.
- Conseguir certificados reales anonimizados y clasificaciones históricas.

**Salida:** corpus jurídico versionado y conjunto inicial de casos.

### Fase 1 - Ontología y motor de reglas

- Diseñar el esquema canónico del producto.
- Convertir notas y filas arancelarias en un grafo de decisiones.
- Implementar operadores exactos (`>`, `>=`, `<`, `<=`) y unidades.
- Crear pruebas para cada límite y exclusión.
- Producir una explicación reproducible.

**Salida:** clasificador probado mediante entradas JSON, todavía sin OCR.

### Fase 2 - Ingesta documental

- Extraer texto y tablas de PDF digitales.
- Incorporar OCR inglés/chino para documentos escaneados.
- Detectar plantillas por proveedor.
- Segmentar certificados multipágina y productos.
- Presentar revisión visual de campos con baja confianza.

**Salida:** certificado PDF convertido al esquema canónico.

### Fase 3 - Aplicación local

- Interfaz para importar archivos y revisar lotes.
- API local y cola de trabajos.
- Persistencia SQLite, auditoría y gestión de reglas.
- Reportes XLSX/CSV/PDF.
- Empaquetado e instalador de Windows.

### Fase 4 - Validación

- Crear un conjunto dorado validado por expertos.
- Medir exactitud por campo, fracción y NICO.
- Probar límites químicos y dimensionales.
- Ejecutar pruebas de regresión al cambiar la tarifa.
- Habilitar operación automática sólo para ramas con evidencia suficiente.

### Fase 5 - Operación y actualización

- Importador de nuevas versiones oficiales.
- Comparación semántica de reglas anteriores y nuevas.
- Aprobación de dos personas para publicar reglas.
- Respaldo y restauración local.

## 6. Criterios de aceptación recomendados

- 100% de decisiones con rastro explicativo y versión de reglas.
- 100% de valores extraídos con página y coordenadas de evidencia.
- Cero clasificación silenciosa cuando falta un campo obligatorio.
- 100% de umbrales jurídicos cubiertos por pruebas de frontera.
- Exactitud de fracción y NICO medida por separado sobre un conjunto dorado.
- Tiempo objetivo inicial: menos de 30 segundos por PDF digital típico y menos
  de 90 segundos por PDF escaneado multipágina, sujeto al hardware y al tamaño.

No conviene fijar un porcentaje de exactitud final hasta contar con documentos
reales y etiquetas confiables. Una meta sin conjunto de prueba sería engañosa.

## 7. Riesgos principales

| Riesgo | Consecuencia | Control |
|---|---|---|
| Fuente sin vigencia | Clasificación legal incorrecta | Fuentes oficiales versionadas y aprobación |
| Certificado incompleto | Rama irresoluble | Datos complementarios y estado `needs_input` |
| Error OCR en decimal | Cambio de tipo de acero | Validaciones, evidencia y doble lectura de campos críticos |
| Términos distintos por proveedor | Extracción inconsistente | Diccionario canónico y adaptadores por plantilla |
| Reglas superpuestas | Más de un resultado | Prioridades legales y detector de conflicto |
| Cambio normativo | Resultados obsoletos | Vigencia temporal y pruebas de regresión |
| Cero casos reales | Falsa confianza | Conjunto dorado antes de uso operativo |

## 8. Decisiones pendientes

1. Quién será responsable de validar y publicar una nueva versión de reglas.
2. Fuentes oficiales exactas que se usarán como autoridad.
3. Formato de reporte prioritario: XLSX, PDF o ambos.
4. Si la aplicación será de una sola computadora o compartida en red local.
5. Política ante evidencia insuficiente: bloquear, pedir captura o devolver
   alternativas ordenadas.
