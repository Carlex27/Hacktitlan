export interface PartitionedFiles {
  accepted: readonly File[];
  rejected: readonly File[];
}

function isSupportedDocument(file: File): boolean {
  return file.type === "application/pdf" || file.type === "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" || /\.(pdf|xlsx)$/i.test(file.name);
}

/**
 * Filtro de captura: sólo evita enviar archivos que claramente no son PDF o XLSX.
 * La validación real del contenido ocurre en el servidor.
 */
export function partitionPdfFiles(files: readonly File[]): PartitionedFiles {
  const accepted: File[] = [];
  const rejected: File[] = [];
  for (const file of files) {
    (isSupportedDocument(file) ? accepted : rejected).push(file);
  }
  return { accepted, rejected };
}
