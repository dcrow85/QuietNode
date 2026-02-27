import { z } from 'zod';
export declare const healthSchema: z.ZodObject<{}, "strip", z.ZodTypeAny, {}, {}>;
export declare const createSessionSchema: z.ZodObject<{}, "strip", z.ZodTypeAny, {}, {}>;
export declare const observeSchema: z.ZodObject<{}, "strip", z.ZodTypeAny, {}, {}>;
export declare const claimSchema: z.ZodObject<{
    token: z.ZodString;
}, "strip", z.ZodTypeAny, {
    token: string;
}, {
    token: string;
}>;
export declare const telemetrySchema: z.ZodObject<{}, "strip", z.ZodTypeAny, {}, {}>;
export declare const timelineSchema: z.ZodObject<{}, "strip", z.ZodTypeAny, {}, {}>;
export declare const exportSchema: z.ZodObject<{}, "strip", z.ZodTypeAny, {}, {}>;
export declare const reflectionPackSchema: z.ZodObject<{}, "strip", z.ZodTypeAny, {}, {}>;
export declare const quietnodeTools: {
    name: string;
    description: string;
    inputSchema: z.ZodObject<{}, "strip", z.ZodTypeAny, {}, {}>;
}[];
export interface QuietNodeToolHandlers {
    quietnode_health: (params: z.infer<typeof healthSchema>) => Promise<any>;
    quietnode_create_session: (params: z.infer<typeof createSessionSchema>) => Promise<any>;
    quietnode_observe: (params: z.infer<typeof observeSchema>) => Promise<any>;
    quietnode_claim: (params: z.infer<typeof claimSchema>) => Promise<any>;
    quietnode_telemetry: (params: z.infer<typeof telemetrySchema>) => Promise<any>;
    quietnode_timeline: (params: z.infer<typeof timelineSchema>) => Promise<any>;
    quietnode_export: (params: z.infer<typeof exportSchema>) => Promise<any>;
    quietnode_reflection_pack: (params: z.infer<typeof reflectionPackSchema>) => Promise<any>;
}
