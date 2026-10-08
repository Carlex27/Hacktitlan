import type { ApiClient, RequestOptions } from "../client";
import type { HealthLiveDto, HealthReadyDto } from "../dto";

export async function getHealthLive(api: ApiClient, options?: RequestOptions) {
  return (await api.get<HealthLiveDto>("/api/v1/health/live", options)).data;
}

export async function getHealthReady(api: ApiClient, options?: RequestOptions) {
  return (await api.get<HealthReadyDto>("/api/v1/health/ready", options)).data;
}
