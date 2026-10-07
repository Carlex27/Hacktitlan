# Reglas de extracción de certificados de molino

## Alcance de esta primera versión

Estas reglas convierten documentos heterogéneos a un contrato canónico. No
deciden todavía la fracción arancelaria ni el NICO. La extracción debe preservar
el texto original y su evidencia antes de normalizarlo.

## Detección de formatos no conocidos

- El detector genérico busca evidencia semántica de certificado, identificadores
  de producto o colada, composición y propiedades. No depende del nombre del
  fabricante ni de coordenadas fijas.
- Un título aislado no basta para aceptar el documento como acta de molino.
- Las variantes de encabezados se mapean mediante un catálogo determinista de
  sinónimos. Las coincidencias conservan texto, página, región y confianza.
- Las tablas candidatas pueden comenzar en cualquier posición y tener cualquier
  cantidad de filas. Para aceptarlas deben reconocerse al menos dos columnas.
- Un formato probable sin adaptador produce `needs_review`; nunca crea rollos ni
  valores para completar el contrato.
- Una página sin texto utilizable o con una capa fragmentada produce
  `needs_ocr`. Hasta incorporar OCR local no se intenta normalizar esa página.
- Los adaptadores conocidos continúan produciendo el contrato intermedio que
  recibe `normalize_certificate`; el detector genérico no reemplaza sus reglas.
- La futura interpretación mediante IA deberá conectarse después de la ingesta y
  antes de la normalización. No forma parte de la implementación actual.

## Flujo por capas

1. **Ingesta:** detectar PDF digital o imagen y conservar página/coordenadas.
   Detectar además la orientación por contenido: no confiar únicamente en el
   indicador de rotación del PDF.
2. **Adaptador de formato:** localizar encabezado, tabla, filas y totales mediante
   etiquetas y geometría, no mediante posiciones absolutas de una sola plantilla.
3. **Segmentación:** crear una entidad por `coil`, `pack`, `item`, `lot` o fila de
   producto. El número de colada puede repetirse y no identifica por sí solo un
   rollo.
4. **Normalización:** convertir escalas, unidades, idiomas y sinónimos sin perder
   el valor original.
5. **Validación:** comparar cantidad de filas, piezas y sumas de peso. Una
   contradicción bloquea la clasificación automática.

## Reglas químicas

- La unidad canónica es porcentaje en masa (`%`).
- El multiplicador se lee del encabezado de la columna. Si `C` muestra `10^-4`,
  cada celda de C se calcula como `valor_crudo × 10^-4`.
- Ejemplo obligatorio: `13 × 10^-4 = 0.0013 %`.
- La operación se realiza con aritmética decimal exacta, no con redondeo binario.
- Celda vacía significa `unknown`; nunca cero. Un `0` impreso sí significa 0 %.
- `Als` se conserva como `Al_soluble`; no se fusiona con aluminio total sin una
  regla explícita.
- `Alt` se conserva como `Al_total`. `Als` y `Alt` son observaciones distintas y
  nunca se sustituyen entre sí.
- Si un elemento no tiene columna en el certificado, queda no reportado
  (`unknown`); no se agrega con valor cero.
- Una comilla o símbolo ditto sólo hereda el valor de la fila anterior en la
  misma columna. Una celda vacía continúa siendo desconocida. Es error usar un
  ditto cuando aún no existe valor anterior.
- El resultado normalizado conserva para cada valor heredado `raw_value`,
  `normalized_value`, `unit`, `inherited=true` e `inherited_from`. Los campos
  planos usados por clasificación contienen siempre el valor expandido; por
  ejemplo, `T137279.thickness_mm=1.8` aunque el PDF muestre `"`.
- Todo valor fuera de 0..100 % o toda columna sin exponente produce error de
  extracción/revisión.
- Los exponentes aceptados incluyen `10^-4`, `10⁻⁴` y el entero `-4`.

## Reglas de producto y dimensiones

- En `MOLINO 1`, `Pack No.` es el identificador único del rollo y `Heat No.` es
  la colada compartida.
- `C` en la columna de longitud se interpreta como **coiled/en rollo**, no como
  una longitud ni como el elemento carbono.
- `Cold-rolled steel strip` fija `form=flat_rolled` y `rolling=cold`.
- `annealed, skin passed` se conserva como dos condiciones de proceso.
- Espesor y ancho se normalizan a milímetros; peso neto y bruto, a kilogramos.

## Controles para MOLINO 1

- Deben existir 6 rollos únicos.
- La suma de peso neto debe ser 47,615 kg.
- La suma de peso bruto debe ser 47,975 kg.
- Los siete valores químicos de cada fila son C=13, Si=0, Mn=12, P=11, S=8,
  Als=31 y Ti=68 antes de aplicar el exponente.
- La composición normalizada resultante es C=0.0013 %, Si=0 %, Mn=0.12 %,
  P=0.011 %, S=0.008 %, Al soluble=0.031 % y Ti=0.068 %.

## Variante MOLINO 2

- Mantiene la misma estructura general, pero la imagen está girada 90 grados sin
  que el metadato de rotación lo indique.
- Contiene 1 rollo, lo que confirma que la cantidad de filas es dinámica y debe
  validarse contra `Total Pieces`, no contra un número fijo.
- El rollo `263W220590210`, colada `2641568`, tiene 1.71 mm × 1220 mm, peso neto
  8,995 kg y peso bruto 9,075 kg.
- Sus encabezados químicos son C y Mn con `10^-2`, y P, S y Alt con `10^-3`.
- La composición normalizada es C=0.08 %, Mn=0.34 %, P=0.015 %, S=0.008 % y
  Al total=0.029 %. Si y Ti no están reportados; no valen cero.

## Variante MOLINO 3 - China Steel Corporation

- Es una plantilla distinta con 11 rollos y norma `SAE 1035`.
- `COIL NO.` es el identificador principal del rollo; `LABEL NO.` se conserva
  como identificador auxiliar y `HEAT` identifica la colada.
- `MASS kg` es una masa sin declaración de neto o bruto. Se guarda como
  `weight_kg` con `weight_kind=mass`; no se inventa que sea peso neto.
- Las dimensiones repetidas mediante comillas heredan 1.800 mm, 895 mm y
  `COIL`. La misma regla se aplica a composición química por columna.
- La suma de las 11 masas debe ser 80,320 kg y la suma de cantidades debe ser
  11.
- Es producto plano enrollado, laminado en caliente y con borde de molino
  (`mill edge`).
- Para la colada `3VL99`, la composición es C=0.35 %, Mn=0.63 %, P=0.017 %,
  S=0.001 %, Si=0.20 %, Cu=0.01 %, Ni=0.01 %, Cr=0.01 %, Al total=0.019 %,
  B=0.0003 %, Mo=0 % y N=0.004 %.
- Para la colada `1FN43`, la composición es C=0.33 %, Mn=0.64 %, P=0.016 %,
  S=0.002 %, Si=0.18 %, Cu=0.01 %, Ni=0.01 %, Cr=0.01 %, Al total=0.025 %,
  B=0.0002 %, Mo=0 % y N=0.004 %.
- La notación compacta `X10` con el exponente impreso sobre la columna debe
  interpretarse mediante el adaptador de esta plantilla y validarse contra
  rangos físicos; no mediante OCR lineal sin contexto geométrico.

## Variante MOLINO 4 - POSCO

- Contiene 6 rollos electrogalvanizados `EG COIL (ZN)`, norma `SECC`, repartidos
  entre las coladas `SB06562` y `SB05270`.
- La celda `1.21x914xC` o `1.52x914xC` se divide en espesor milimétrico, ancho
  milimétrico y estado enrollado. La cadena original se conserva como evidencia.
- `Weight` se guarda como masa genérica; el certificado no declara neto/bruto.
- La química ya está expresada directamente en porcentaje. No se desplaza el
  decimal: C=0.0136 significa 0.0136 %, no 0.000136 %.
- Se registra que el análisis es de cuchara (`ladle analysis`).
- El recubrimiento es zinc electrolítico. Se conservan por separado las masas de
  recubrimiento superior e inferior: 19.1/19.1 g/m² para `CBG2629A-C` y
  19.5/19.5 g/m² para `CBG4348A-C`.
- El tratamiento posterior `PL (Cr-Free Phosphate)` se conserva como propiedad
  del producto; no debe inferirse únicamente desde la norma `SECC`.
- Deben validarse los subtotales: 3 piezas y 15,810 kg para `SB06562`; 3 piezas
  y 18,240 kg para `SB05270`. El total general es 6 piezas y 34,050 kg.

## Política de confianza

Los identificadores, decimales, exponentes químicos y totales son campos
críticos. Si OCR y lectura de tabla discrepan, si falta el exponente o si no
cuadran los totales, el resultado es `needs_review`; no se corrige ni se infiere
silenciosamente. Distintos formatos deben implementar adaptadores que produzcan
el mismo contrato intermedio usado por `normalize_certificate`.
