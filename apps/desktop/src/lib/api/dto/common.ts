/** Valor JSON arbitrario tal como lo conserva el backend (evidencia, valores crudos). */
export type JsonValue =
  | string
  | number
  | boolean
  | null
  | readonly JsonValue[]
  | { readonly [key: string]: JsonValue };

export type JsonObject = { readonly [key: string]: JsonValue };

/** Persona y motivo obligatorios en toda acción auditada. */
export interface ActorReasonDto {
  person_name: string;
  reason: string;
}
