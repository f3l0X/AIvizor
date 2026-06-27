// Cliente HTTP del backend — se llena en Fase 4.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function getHealth() {
  const r = await fetch(`${API_URL}/health`, { cache: 'no-store' });
  if (!r.ok) throw new Error(`Health check failed: ${r.status}`);
  return r.json() as Promise<{
    status: string;
    service: string;
    version: string;
    llm_provider: string;
  }>;
}
