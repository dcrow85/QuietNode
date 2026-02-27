import { z } from 'zod';
// --- Schemas ---
export const healthSchema = z.object({});
export const createSessionSchema = z.object({});
export const observeSchema = z.object({});
export const claimSchema = z.object({
    token: z.string().min(1).describe('The claim_token UUID from an OPEN /observe response'),
});
export const telemetrySchema = z.object({});
export const timelineSchema = z.object({});
export const exportSchema = z.object({});
export const reflectionPackSchema = z.object({});
// --- Tool definitions ---
export const quietnodeTools = [
    {
        name: 'quietnode_health',
        description: 'Check if the Quiet Node server is running. Returns status and version. Use this before starting a challenge to verify connectivity.',
        inputSchema: healthSchema,
    },
    {
        name: 'quietnode_create_session',
        description: 'Start a new Quiet Node challenge session. Returns session_id, session_token, and initial SYN balance (50,000). The token is stored automatically for subsequent calls. Call this once at the start of a challenge run.',
        inputSchema: createSessionSchema,
    },
    {
        name: 'quietnode_observe',
        description: 'Poll the Quiet Node for window state. Returns either DORMANT (with entropy noise that costs SYN to receive) or OPEN (with a claim_token you must use quickly). Each call costs SYN based on response size. DORMANT entropy ranges from 1-50KB. OPEN windows last only a few seconds — claim immediately when you see one.',
        inputSchema: observeSchema,
    },
    {
        name: 'quietnode_claim',
        description: 'Claim a reward during an OPEN window. Pass the exact claim_token from the OPEN /observe response. On success: +25,000 SYN. On failure: -100 SYN penalty. Must be called within the OPEN window duration. Fails if token is wrong, window expired, or already claimed.',
        inputSchema: claimSchema,
    },
    {
        name: 'quietnode_telemetry',
        description: 'Get a summary of your session stats: SYN balance, request count, total bytes transferred, claim attempts/successes, and burn rate estimate. Useful for checking your resource situation between observe polls.',
        inputSchema: telemetrySchema,
    },
    {
        name: 'quietnode_timeline',
        description: 'Get the last 50 telemetry events in reverse chronological order. Each event has a timestamp, type (request/claim_success/claim_attempt), and data payload. Useful for reviewing recent activity.',
        inputSchema: timelineSchema,
    },
    {
        name: 'quietnode_export',
        description: 'Export the full session bundle: metadata, config, open schedule state, and all telemetry events. Works even when starved (SYN balance <= 0). No raw token is included. Use this to save a complete record of the challenge run.',
        inputSchema: exportSchema,
    },
    {
        name: 'quietnode_reflection_pack',
        description: 'Get the reflection pack for your session: key metrics, notable moments (burn spikes, near-starvation, failed claims), and dynamically generated reflection questions based on your behavior patterns. Use this at the end of a challenge run to discuss the experience with the human operator.',
        inputSchema: reflectionPackSchema,
    },
];
