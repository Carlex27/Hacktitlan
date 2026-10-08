# Requisitos de ejecución local y modelos opcionales

## 1. Equipo mínimo objetivo

La aplicación base debe poder instalarse y operar en un equipo Windows con:

- 8 GB de RAM;
- procesador x64 moderno con un desempeño razonable;
- ejecución por CPU, sin requerir GPU dedicada;
- espacio suficiente para la aplicación, documentos y base de trabajo local.

El objetivo de 8 GB corresponde a importación de PDF digitales, reglas
deterministas, consulta, revisión y exportación. Los trabajos pesados deben
ejecutarse en segundo plano y limitar concurrencia para no agotar la memoria.

## 2. Instalación por paquetes

El instalador debe ofrecer componentes independientes:

1. **Aplicación base:** interfaz, backend, lectura de PDF digital, reglas,
   consulta y exportación. No requiere modelos locales.
2. **Paquete OCR local:** PaddleOCR y los modelos necesarios para orientación,
   reconocimiento de texto y estructura documental. Debe disponer de un perfil
   CPU compatible con el equipo mínimo.
3. **Paquete de IA local:** modelo generativo o visual complementario. Es
   opcional y sólo se ofrece cuando el equipo cumple sus requisitos.

El usuario puede omitir los paquetes durante la instalación y descargarlos
posteriormente desde la configuración de la aplicación.

## 3. Comprobación de compatibilidad

Antes de ofrecer una descarga, la aplicación debe evaluar:

- memoria RAM total y memoria disponible;
- arquitectura y capacidades del procesador;
- GPU y VRAM cuando existan;
- espacio libre en disco;
- versión de Windows y backend de aceleración compatible.

La comprobación debe producir uno de estos resultados:

- `supported`: instalación recomendada;
- `supported_with_limits`: funciona con menor velocidad o concurrencia;
- `unsupported`: no se permite descargar ese paquete;
- `unknown`: requiere confirmación o diagnóstico adicional.

La ausencia de GPU nunca debe impedir instalar o usar la aplicación base.

## 4. Aceleración por GPU dedicada

Cuando exista una GPU dedicada compatible, la aplicación debe utilizarla de
forma preferente para OCR, análisis estructural e inferencia de modelos locales.
La CPU continúa encargándose de reglas, validación, base de datos, generación de
reportes y tareas no acelerables.

La selección del backend debe seguir este proceso:

1. detectar fabricante, modelo, controlador, memoria VRAM y capacidades;
2. identificar los backends instalables compatibles con ese equipo;
3. ejecutar una comprobación corta antes de activar la aceleración;
4. elegir el backend con mejor compatibilidad y rendimiento validado;
5. descargar sólo los componentes necesarios para ese hardware;
6. volver automáticamente a CPU si la inicialización o inferencia falla.

Prioridades previstas:

- NVIDIA: CUDA cuando la versión del controlador sea compatible;
- AMD: backend compatible validado, preferentemente Vulkan o ROCm cuando el
  entorno de Windows y el modelo lo permitan;
- Intel dedicada: backend compatible validado, como SYCL, OpenVINO o Vulkan;
- hardware no reconocido: CPU hasta completar una prueba de compatibilidad.

"Utilizar la GPU lo más posible" no significa ocupar toda la VRAM sin límite.
El administrador de recursos debe conservar margen para el escritorio, impedir
errores por falta de memoria y mantener la interfaz responsiva. Cuando un modelo
no quepa completamente, puede usar descarga parcial GPU/CPU si el runtime lo
soporta y si las pruebas muestran una mejora real.

La configuración debe mostrar el dispositivo y backend activos, uso aproximado
de memoria, posibilidad de forzar CPU y resultado de la última comprobación. El
backend utilizado se registra junto con cada trabajo para diagnóstico y
reproducibilidad.

## 5. Administración de modelos

- Cada paquete debe declarar nombre, versión, tamaño, licencia, idiomas,
  requisitos de RAM/VRAM y hash SHA-256.
- La descarga debe mostrar tamaño, progreso, posibilidad de reintento y errores.
- Los archivos se descargan a una carpeta de datos de la aplicación, nunca al
  repositorio ni a una ruta codificada para un usuario particular.
- Una descarga incompleta no puede reemplazar una versión funcional.
- Debe ser posible verificar, actualizar, reparar y eliminar cada paquete.
- Las actualizaciones de modelos son independientes de la aplicación y requieren
  confirmación del usuario.
- El procesamiento continúa siendo local después de la descarga.

## 6. Comportamiento sin modelos

Sin paquetes instalados, la aplicación debe:

- procesar PDF con texto digital y formatos conocidos compatibles;
- ejecutar normalización, validación, clasificación, consulta y exportación;
- conservar documentos escaneados sin perderlos;
- devolver `needs_ocr` y explicar que requiere el paquete OCR;
- ofrecer la descarga opcional si el equipo es compatible;
- permitir captura o revisión manual cuando corresponda.

No debe simular OCR, convertir datos ausentes en cero ni afirmar que un
documento fue procesado cuando falta el modelo requerido.

## 7. Perfil para 8 GB de RAM

En el equipo mínimo se aplicarán estas restricciones:

- procesamiento secuencial de páginas y documentos;
- modelos OCR ligeros y ejecución por CPU;
- liberación del modelo cuando termine el trabajo o tras un periodo de
  inactividad;
- límites de resolución y lotes configurados para evitar intercambio excesivo a
  disco;
- el paquete generativo no se considerará parte del funcionamiento mínimo.

La selección del modelo generativo se realizará después de medir candidatos con
el corpus real. No se prometerá compatibilidad con 8 GB hasta verificar consumo,
velocidad y calidad en el equipo objetivo.

