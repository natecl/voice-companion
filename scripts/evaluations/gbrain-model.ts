// Real providers behind a metered SSH transport; upstream extraction/storage unchanged.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { createInterface } from 'node:readline';
import { gunzipSync } from 'node:zlib';
import { execFileSync, spawn } from 'node:child_process';
const [upstreamArg, outArg] = process.argv.slice(2);
if (!upstreamArg || !outArg)
    throw Error('Expected upstream and fresh output directory');
const upstream = resolve(upstreamArg), out = resolve(outArg);
const pin = '46ad5153a362815e4bd7a21f804561d492816fc5';
if (execFileSync('git', ['-C', upstream, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim() !== pin)
    throw Error('Upstream revision mismatch');
mkdirSync(out);
process.env.GBRAIN_HOME = resolve(out, 'home');
const { PGLiteEngine } = await import(upstream + '/src/core/pglite-engine.ts');
const gateway = await import(upstream + '/src/core/ai/gateway.ts');
const { dispatchToolCall } = await import(upstream + '/src/mcp/dispatch.ts');
const { __setUsageLogPathForTests } = await import(upstream + '/src/core/verbs/usage-log.ts');
__setUsageLogPathForTests(resolve(out, 'usage.jsonl'));
const report: any = { upstream: pin, scope: 'Luna extraction and OpenAI embeddings; custom metered transport, not upstream default model', provider: [], operations: [], queries: [] };
const save = () => writeFileSync(resolve(out, 'report.json'), JSON.stringify(report, null, 2));
const sources = JSON.parse(readFileSync('Backend/fixtures/gbrain-comparison/model-cases.json', 'utf8'));
let chatCount = 0, embeddingCount = 0, stage = '', stageChat = false;
// Reuse successfully saved provider responses after local harness/protocol repairs.
const cache = new Map<string, any>();
for (const file of process.argv.slice(4)) {
    const bytes = readFileSync(file);
    const prior = JSON.parse((file.endsWith('.gz') ? gunzipSync(bytes) : bytes).toString());
    for (const r of prior.provider ?? [])
        cache.set(JSON.stringify(r.request), r);
}
let bridge: any = null, pending: any = null;
let providerQueue: Promise<any> = Promise.resolve();
function bridgeCall(request: any): Promise<any> {
    const task = providerQueue.then(() => sendOne(request));
    providerQueue = task.catch(() => { });
    return task;
}
function sendOne(request: any): Promise<any> {
    if (!bridge) {
        bridge = spawn('ssh', ['-i', '/Users/n.chinlue/.ssh/voice_companion_render', '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
            'srv-daqtfs7lot8c73dleuug@ssh.virginia.render.com', 'python3 /tmp/gbrain-provider-20260926.py --stream']);
        createInterface({ input: bridge.stdout }).on('line', (line: string) => {
            if (!pending)
                return;
            const p = pending;
            pending = null;
            clearTimeout(p.timer);
            try {
                const r = JSON.parse(line);
                r.transport_error ? p.reject(Error(r.transport_error)) : p.accept(r);
            }
            catch (e) {
                p.reject(e);
            }
        });
        bridge.stderr.on('data', (x: any) => process.stderr.write(x));
        const fail = (e: any) => { if (pending) {
            clearTimeout(pending.timer);
            pending.reject(e);
            pending = null;
        } };
        bridge.on('error', fail);
        bridge.on('close', (code: any) => fail(Error('Provider bridge closed: ' + code)));
    }
    if (pending)
        throw Error('Only one provider request may run at a time');
    return new Promise((accept, reject) => {
        const timer = setTimeout(() => { pending = null; bridge.kill(); reject(Error('Provider timeout; no retry')); }, 60000);
        pending = { accept, reject, timer };
        bridge.stdin.write(JSON.stringify(request) + '\n');
    });
}
const attempted = new Set<string>();
let offlineMisses = 0;
async function provider(kind: string, body: any) {
    const request = { kind, body }, signature = JSON.stringify(request);
    if (cache.has(signature)) {
        const result = cache.get(signature);
        report.provider.push({ stage, ...result, replayed: true });
        save();
        return result.response;
    }
    if (process.env.GBRAIN_EVAL_OFFLINE === '1') {
        offlineMisses++;
        throw Error('Offline provider cache miss');
    }
    if (attempted.has(signature))
        throw Error('Automatic provider retry blocked');
    attempted.add(signature);
    const result = await bridgeCall(request);
    cache.set(signature, result);
    report.provider.push({ stage, ...result });
    save();
    return result.response;
}
gateway.configureGateway({ embedding_model: 'openai:text-embedding-3-small', embedding_dimensions: 1536, env: { OPENAI_API_KEY: 'test-seam-no-real-credential' } });
gateway.__setChatTransportForTests(async (opts: any) => {
    if (stageChat || ++chatCount > sources.length)
        throw Error('Automatic chat retry or extra model call blocked');
    stageChat = true;
    if (opts.model !== 'openai:gpt-6-luna' || opts.tools?.length)
        throw Error('Unexpected upstream model/tools');
    const body: any = { model: 'gpt-6-luna', instructions: opts.system, input: opts.messages,
        reasoning: { effort: 'none' }, service_tier: 'default', max_output_tokens: opts.maxTokens, store: false, tools: [], truncation: 'disabled' };
    // Preserve upstream schema without imposing stronger strict-schema constraints.
    if (opts.responseSchema)
        body.text = { format: { type: 'json_schema', ...opts.responseSchema, strict: false } };
    let r: any;
    try {
        r = await provider('chat', body);
    }
    catch (e) {
        report.transport_failure = String(e);
        save();
        throw e;
    }
    const text = (r.output ?? []).flatMap((x: any) => x.content ?? []).filter((x: any) => x.type === 'output_text').map((x: any) => x.text).join('');
    return { text, blocks: [{ type: 'text', text }], stopReason: r.status === 'completed' ? 'end' : 'length',
        usage: { input_tokens: r.usage?.input_tokens ?? 0, output_tokens: r.usage?.output_tokens ?? 0, cache_read_tokens: r.usage?.input_tokens_details?.cached_tokens ?? 0, cache_creation_tokens: 0 },
        model: opts.model, responseModel: r.model, providerId: 'openai' };
});
gateway.__setEmbedTransportForTests(async (opts: any) => {
    if (++embeddingCount > 45)
        throw Error('Embedding count limit');
    const r = await provider('embed', { model: 'text-embedding-3-small', input: opts.values, dimensions: 1536, encoding_format: 'float' });
    return { embeddings: r.data.sort((a: any, b: any) => a.index - b.index).map((x: any) => x.embedding), usage: { tokens: r.usage.total_tokens } };
});
const engine = new PGLiteEngine();
async function call(name: string, params: any) {
    const r = await dispatchToolCall(engine, name, params, { remote: true, sourceId: 'default', takesHoldersAllowList: ['world'] });
    const body = JSON.parse(r.content[0].text);
    report.operations.push({ stage, name, params, isError: !!r.isError, body });
    save();
    if (body.error === 'write_pending' && body.write_request?.request_id) {
        for (let poll = 0; poll < 60; poll++) {
            await new Promise(r => setTimeout(r, 1000));
            const receipt = await call('get_write_request', { request_id: body.write_request.request_id });
            if (receipt.state === 'committed')
                return receipt;
            if (['failed', 'cancelled'].includes(receipt.state))
                throw Error(JSON.stringify(receipt));
        }
        throw Error('Write receipt did not finish within bounded wait');
    }
    if (r.isError)
        throw Error(JSON.stringify(body));
    return body;
}
try {
    await engine.connect({ database_path: resolve(out, 'database') });
    await engine.initSchema();
    await engine.setConfig('facts.extraction_enabled', 'false');
    await engine.setConfig('facts.extraction_model', 'openai:gpt-6-luna');
    for (const source of sources) {
        stage = source.id;
        stageChat = false;
        await call('put_page', { slug: 'recordings/' + source.id, content: `---\ntitle: ${source.id}\ntype: meeting\n---\n\n${source.text}` });
        await engine.setConfig('facts.extraction_enabled', 'true');
        const extracted = await call('extract_facts', { turn_text: source.text, session_id: source.id, source_slug: 'recordings/' + source.id, visibility: 'world', valid_from: source.captured_at });
        if (extracted.skipped || extracted.skipped_reason)
            throw Error('Extraction skipped: ' + JSON.stringify(extracted));
        await engine.setConfig('facts.extraction_enabled', 'false');
        await call('recall', { session_id: source.id, limit: 30 });
    }
    stage = 'retrieval';
    for (const query of ['When does Project Juniper prefer to meet?', 'Where does Project Juniper meet now?', 'What does Maya enjoy?', 'What food should we avoid for Milo?']) {
        const result = await call('recall', { query, budget_tokens: 1800, limit: 20 });
        report.queries.push({ query, result });
        save();
    }
    stage = 'deletion';
    const page = await call('get_page', { slug: 'recordings/correction' });
    await call('delete_page', { slug: 'recordings/correction', expected_revision: page.revision ?? page.page?.revision });
    report.after_delete = await call('recall', { session_id: 'correction', limit: 30 });
    report.chat_calls = chatCount;
    report.embedding_calls = embeddingCount;
    report.offline_cache_misses = offlineMisses;
    save();
    if (offlineMisses)
        throw Error('Offline run was incomplete');
    console.log(JSON.stringify({ chat_calls: chatCount, embedding_calls: embeddingCount, report: out + '/report.json' }));
}
catch (e) {
    report.failure = String(e);
    save();
    throw e;
}
finally {
    await providerQueue;
    if (bridge)
        bridge.stdin.end();
    await engine.disconnect();
}
