import { api } from "./api";

export async function getHealth(): Promise<{ status: string }> {
  const response = await api.get("/health");
  return response.data;
}
