# Decisiones funcionales aprobadas

Fecha de consolidación: 7 de octubre de 2026.

## 1. Usuarios y aprobación

- La primera versión no tendrá cuentas, inicio de sesión ni roles de usuario.
- La clasificación usará los estados `draft`, `needs_review`, `approved` y
  `rejected`.
- Aprobar o rechazar será una acción manual dentro de la aplicación.
- Mientras no existan usuarios, la auditoría registrará fecha y equipo de origen
  automáticamente; el nombre de la persona y el motivo serán obligatorios al
  corregir, aprobar o rechazar.
- Incorporar usuarios posteriormente no debe requerir reescribir el historial
  existente.

## 2. Archivos originales

- Los PDF originales se almacenan de forma centralizada y administrada por el
  backend del equipo principal.
- PostgreSQL conserva metadatos, relaciones, tamaño, tipo de archivo, ubicación
  controlada y hash SHA-256; el binario no se guarda como una columna grande en
  la base de datos.
- El backend asigna el nombre y la ruta física. Nunca se confía en una ruta
  enviada por el frontend.
- La escritura se realiza primero en un archivo temporal, se valida el hash y
  después se publica atómicamente.
- Un mismo archivo detectado por hash no se duplica sin una razón registrada.
- El segundo equipo obtiene originales y evidencias por la API a través de
  Tailscale; no accede directamente al sistema de archivos del servidor.

## 3. Disponibilidad

- Si el backend principal, PostgreSQL o Tailscale no están disponibles, el
  segundo equipo queda bloqueado para consulta, carga, corrección y exportación.
- La aplicación debe mostrar qué componente no está disponible y permitir
  reintentar la conexión.
- La primera versión no tendrá modo offline, cola local ni sincronización
  posterior.

## 4. Correcciones e historial

- Una corrección nunca sobrescribe la observación o clasificación anterior.
- Se conserva valor anterior, valor nuevo, motivo, fecha, equipo y ejecución
  afectada.
- Reclasificar crea una nueva ejecución vinculada con la anterior.
- Los reportes históricos pueden regenerarse usando una ejecución específica.

## 5. Volumen inicial de diseño

La estimación inicial es:

- aproximadamente 10 actas de molino por día;
- aproximadamente 10 a 15 coladas por acta;
- aproximadamente 100 a 150 coladas por día;
- como referencia de capacidad, hasta 3,650 actas y 54,750 coladas por año si
  se opera todos los días.

Estas cantidades no son límites funcionales. El diseño debe usar consultas
paginadas, claves foráneas indexadas y filtros ejecutados por PostgreSQL. Los
rollos por colada continúan siendo variables y deben medirse durante las pruebas
piloto para ajustar almacenamiento y rendimiento.

## 6. Respaldo y restauración

- Se ejecutará un respaldo automático diario.
- El respaldo integral incluye PostgreSQL, PDF originales, archivos derivados,
  reglas versionadas y un manifiesto con hashes.
- La aplicación o una herramienta administrativa permitirá generar manualmente
  un paquete completo de respaldo para copiarlo a otro dispositivo.
- La exportación Excel no sustituye un respaldo porque no contiene toda la
  estructura operativa ni garantiza restauración.
- Todo paquete debe poder verificarse antes de considerarse válido.
- Debe documentarse y probarse el procedimiento de restauración en un entorno
  separado.
- Se conservarán 7 copias diarias, 4 semanales y 12 mensuales. El destino de la
  segunda copia es configurable y debe estar en una ubicación distinta del
  almacenamiento principal.

## 7. Reportes

- El formato inicial será genérico, sin logotipo ni personalización corporativa.
- Se podrá generar por acta, día, semana, mes o rango personalizado.
- También podrá generarse para una colada o selección de resultados.
- Los reportes usarán exclusivamente la información disponible y marcarán
  campos desconocidos; no inventarán datos para completar el diseño.
- La salida tabular principal será XLSX conforme a
  `EXCEL_EXPORT_REQUIREMENTS.md`; PDF se usará para presentación y archivo.

## 8. Fuente de reglas

- Durante esta etapa se utilizará solamente el PDF de reglas entregado para el
  proyecto.
- El conjunto se identificará como una versión de fuente proporcionada, con
  hash y fecha de incorporación.
- No se mezclará silenciosamente con reglas obtenidas de otras fuentes.
- Se conservará la advertencia sobre su vigencia hasta que sea reemplazado o
  validado formalmente.

## 9. Plataforma

- La plataforma objetivo es Windows 11 de 64 bits.
- Se retira el objetivo de funcionar con 8 GB de RAM por instrucción del usuario.
  No hay un presupuesto fijo de RAM; los modelos se eligen por calidad y
  capacidad del equipo disponible. La aplicación base puede operar sin GPU dedicada.
- Cuando exista GPU dedicada compatible se utilizará preferentemente conforme a
  `LOCAL_MODELS_REQUIREMENTS.md`.
- Windows 10, Windows ARM y otros sistemas operativos quedan fuera del alcance
  inicial.
