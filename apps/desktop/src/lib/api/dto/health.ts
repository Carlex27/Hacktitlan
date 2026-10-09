export interface HealthLiveDto {
  status: "ok";
}

export interface HealthReadyDto {
  status: "ready";
  database: string;
  storage: string;
}
