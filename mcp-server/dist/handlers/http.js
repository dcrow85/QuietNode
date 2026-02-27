export function authHeaders(token) {
    const headers = { 'Content-Type': 'application/json' };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}
export async function parseOrThrow(response, label) {
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.detail || data.message || data.error || `${label} failed (${response.status})`);
    }
    return data;
}
