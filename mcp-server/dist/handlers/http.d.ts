export declare function authHeaders(token: string | null): Record<string, string>;
export declare function parseOrThrow<T = any>(response: Response, label: string): Promise<T>;
