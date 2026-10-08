export interface PartitionedFiles {
  accepted: readonly File[];
  rejected: readonly File[];
}

function isPdf(file: File): boolean {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
}

/**
 * Filtro de captura: sólo evita enviar archivos que claramente no son PDF.
 * La validación real del contenido ocurre en el servidor.
 */
export function partitionPdfFiles(files: readonly File[]): PartitionedFiles {
  const accepted: File[] = [];
  const rejected: File[] = [];
  for (const file of files) {
    (isPdf(file) ? accepted : rejected).push(file);
  }
  return { accepted, rejected };
}
