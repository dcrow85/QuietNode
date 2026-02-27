export function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function parseOrThrow<T = any>(response: Response, label: string): Promise<T> {
  const data: any = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || data.message || data.error || `${label} failed (${response.status})`);
  }
  return data as T;
}
