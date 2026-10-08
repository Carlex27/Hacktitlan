/** Textos visibles de la interfaz (es-MX). */
export const es = {
  app: {
    title: "Clasificador LIGIE",
    subtitle: "Capítulo 72",
  },
  processingStatus: {
    loading: "Procesando",
    empty: "Sin datos",
    success: "Extraído",
    needs_review: "Requiere revisión",
    error: "Error",
  },
  connection: {
    checking: "Comprobando conexión con el servidor…",
    connected: "Servidor conectado",
    retry: "Reintentar conexión",
    retrying: "Reintentando…",
    blockedNotice:
      "Sin conexión al servidor no es posible consultar, cargar, corregir ni exportar información.",
    unavailable: {
      server: {
        title: "No se puede contactar al servidor",
        description:
          "El backend no responde. Verifique que el servicio esté iniciado en el equipo servidor y que Tailscale esté conectado.",
      },
      dependencies: {
        title: "El servidor no está listo",
        description:
          "El backend responde, pero la base de datos PostgreSQL o el almacenamiento central no están disponibles.",
      },
    },
    serverAddress: (url: string) => `Servidor: ${url}`,
  },
  certificateImport: {
    title: "Importar actas de molino",
    description:
      "Los PDF se envían al servidor central, donde se extraen y normalizan. La clasificación se revisa después.",
    dropzone: {
      label: "Seleccionar certificados PDF",
      hint: "Arrastre archivos PDF aquí o presione para elegirlos.",
      rejected: (names: readonly string[]) =>
        `Se omitieron archivos que no son PDF: ${names.join(", ")}.`,
    },
    queue: {
      title: "Archivos enviados",
      emptyTitle: "No hay archivos seleccionados",
      emptyDescription: "Los certificados que agregue aparecerán aquí con su estado de procesamiento.",
      clearFinished: "Limpiar terminados",
    },
    item: {
      uploading: "Enviando al servidor…",
      queued: "En cola de extracción",
      running: "Extrayendo",
      succeeded: "Extracción completa",
      needsReview: "La extracción requiere revisión manual",
      needsOcr: "PDF escaneado: requiere OCR, todavía no disponible",
      failed: "La extracción falló",
      cancelled: "Trabajo cancelado",
      noJob: "El servidor no registró un trabajo para este documento",
      duplicate: "Archivo ya registrado previamente",
      progress: (value: number) => `${value} %`,
      progressLabel: (fileName: string) => `Progreso de ${fileName}`,
      certificateRef: (id: number) => `Acta #${id}`,
    },
  },
  errors: {
    network: "No fue posible conectar con el servidor.",
    invalidResponse: "La respuesta del servidor no es válida.",
    unexpected: "Ocurrió un error inesperado.",
    requestId: (id: string) => `Referencia: ${id}`,
  },
} as const;
