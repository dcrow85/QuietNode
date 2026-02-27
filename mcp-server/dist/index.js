#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema, } from '@modelcontextprotocol/sdk/types.js';
import { quietnodeTools } from './tools/index.js';
import { createQuietNodeHandlers } from './handlers/index.js';
// Zod introspection: convert Zod schema → MCP Tool JSON Schema
function resolveZodType(def) {
    if (!def)
        return 'string';
    const tn = def.typeName;
    if (tn === 'ZodOptional' || tn === 'ZodDefault' || tn === 'ZodNullable') {
        return resolveZodType(def.innerType?._def);
    }
    if (tn === 'ZodString' || tn === 'ZodEnum' || tn === 'ZodLiteral')
        return 'string';
    if (tn === 'ZodNumber')
        return 'number';
    if (tn === 'ZodBoolean')
        return 'boolean';
    if (tn === 'ZodArray')
        return 'array';
    if (tn === 'ZodObject')
        return 'object';
    return 'string';
}
function resolveDescription(value) {
    if (value?._def?.description)
        return value._def.description;
    if (value?._def?.innerType?._def?.description)
        return value._def.innerType._def.description;
    return '';
}
function convertTool(tool) {
    try {
        const shapeFn = tool.inputSchema?._def?.shape;
        const shape = typeof shapeFn === 'function' ? shapeFn() : null;
        const properties = {};
        const required = [];
        if (shape && typeof shape === 'object') {
            for (const [key, value] of Object.entries(shape)) {
                properties[key] = {
                    type: resolveZodType(value?._def),
                    description: resolveDescription(value),
                };
                if (typeof value?.isOptional === 'function' && !value.isOptional()) {
                    required.push(key);
                }
            }
        }
        return {
            name: tool.name,
            description: tool.description,
            inputSchema: { type: 'object', properties, required },
        };
    }
    catch (err) {
        console.error(`[MCP] Failed to introspect tool "${tool.name}":`, err);
        return {
            name: tool.name,
            description: tool.description,
            inputSchema: { type: 'object', properties: {}, required: [] },
        };
    }
}
export async function createQuietNodeMCPServer(config) {
    const allTools = quietnodeTools.map(convertTool);
    const server = new Server({ name: 'quietnode-mcp-server', version: '0.1.0' }, { capabilities: { tools: {} } });
    const handlers = createQuietNodeHandlers(config);
    server.setRequestHandler(ListToolsRequestSchema, async () => ({
        tools: allTools,
    }));
    server.setRequestHandler(CallToolRequestSchema, async (request) => {
        const { name, arguments: args } = request.params;
        const handler = handlers[name];
        if (!handler) {
            throw new Error(`Unknown tool: ${name}`);
        }
        try {
            const result = await handler(args || {});
            return {
                content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
            };
        }
        catch (error) {
            const message = error instanceof Error ? error.message : 'Unknown error';
            return {
                content: [{ type: 'text', text: JSON.stringify({ error: message }) }],
                isError: true,
            };
        }
    });
    return server;
}
async function main() {
    const config = {
        apiUrl: process.env.QUIETNODE_API_URL || 'http://89.167.102.244:8085',
    };
    const server = await createQuietNodeMCPServer(config);
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error('Quiet Node MCP Server running on stdio');
}
main().catch((error) => {
    console.error('Failed to start MCP server:', error);
    process.exit(1);
});
