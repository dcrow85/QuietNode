import { authHeaders, parseOrThrow } from './http.js';
export function createQuietNodeHandlers(config) {
    const apiUrl = config.apiUrl;
    // Session-scoped state: token is set after create_session
    let sessionToken = null;
    function requireToken() {
        if (!sessionToken) {
            throw new Error('No active session. Call quietnode_create_session first.');
        }
        return sessionToken;
    }
    return {
        async quietnode_health() {
            const response = await fetch(`${apiUrl}/health`);
            return await parseOrThrow(response, 'health');
        },
        async quietnode_create_session() {
            const response = await fetch(`${apiUrl}/session/new`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            const data = await parseOrThrow(response, 'create_session');
            sessionToken = data.session_token;
            return {
                session_id: data.session_id,
                syn_balance: data.syn_balance,
                message: `Session created. Starting balance: ${data.syn_balance} SYN.`,
            };
        },
        async quietnode_observe() {
            const token = requireToken();
            const response = await fetch(`${apiUrl}/observe`, {
                headers: authHeaders(token),
            });
            if (response.status === 402) {
                return { state: 'STARVED', message: 'SYN balance exhausted. You are locked out.' };
            }
            const data = await parseOrThrow(response, 'observe');
            if (data.state === 'OPEN') {
                return {
                    state: 'OPEN',
                    claim_token: data.claim_token,
                    message: 'OPEN window detected! Use quietnode_claim with this claim_token immediately.',
                };
            }
            // DORMANT — strip entropy from response (too large for chat), report size
            const entropyBytes = data.entropy ? data.entropy.length / 2 : 0;
            return {
                state: 'DORMANT',
                entropy_bytes: entropyBytes,
                message: `DORMANT. Received ${Math.round(entropyBytes / 1024)}KB entropy noise.`,
            };
        },
        async quietnode_claim(params) {
            const token = requireToken();
            const response = await fetch(`${apiUrl}/claim`, {
                method: 'POST',
                headers: authHeaders(token),
                body: JSON.stringify({ token: params.token }),
            });
            return await parseOrThrow(response, 'claim');
        },
        async quietnode_telemetry() {
            const token = requireToken();
            const response = await fetch(`${apiUrl}/session/me/telemetry`, {
                headers: authHeaders(token),
            });
            if (response.status === 402) {
                return { error: 'STARVED', message: 'SYN balance exhausted. Use quietnode_export instead.' };
            }
            return await parseOrThrow(response, 'telemetry');
        },
        async quietnode_timeline() {
            const token = requireToken();
            const response = await fetch(`${apiUrl}/session/me/timeline`, {
                headers: authHeaders(token),
            });
            if (response.status === 402) {
                return { error: 'STARVED', message: 'SYN balance exhausted. Use quietnode_export instead.' };
            }
            return await parseOrThrow(response, 'timeline');
        },
        async quietnode_export() {
            const token = requireToken();
            const response = await fetch(`${apiUrl}/session/me/export`, {
                headers: authHeaders(token),
            });
            return await parseOrThrow(response, 'export');
        },
        async quietnode_reflection_pack() {
            const token = requireToken();
            const response = await fetch(`${apiUrl}/session/me/reflection-pack`, {
                headers: authHeaders(token),
            });
            if (response.status === 402) {
                return { error: 'STARVED', message: 'SYN balance exhausted. Use quietnode_export instead.' };
            }
            return await parseOrThrow(response, 'reflection_pack');
        },
    };
}
