// Synthetic infrastructure comparison, not a model-quality or mobile test.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { execFileSync } from 'node:child_process';
const [upstreamArg, outputArg, sourceFile] = process.argv.slice(2);
if (!upstreamArg || !outputArg || !sourceFile) throw new Error('Expected upstream, fresh output directory, sources.json');
const upstream=resolve(upstreamArg), out=resolve(outputArg);
const revision=execFileSync('git',['-C',upstream,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
if(revision!=='46ad5153a362815e4bd7a21f804561d492816fc5')throw new Error('Unexpected upstream revision');
mkdirSync(out,{recursive:false});
process.env.GBRAIN_HOME=resolve(out,'home');
const {PGLiteEngine}=await import(upstream+'/src/core/pglite-engine.ts');
const {configureGateway,__setChatTransportForTests,__setEmbedTransportForTests}=await import(upstream+'/src/core/ai/gateway.ts');
const {dispatchToolCall}=await import(upstream+'/src/mcp/dispatch.ts');
const {__setUsageLogPathForTests}=await import(upstream+'/src/core/verbs/usage-log.ts');
configureGateway({env:{}});
let providerAttempts=0;
const forbidden=async()=>{providerAttempts++;throw new Error('Provider call forbidden in keyless evaluation');};
__setChatTransportForTests(forbidden);__setEmbedTransportForTests(forbidden);
__setUsageLogPathForTests(resolve(out,'usage.jsonl'));
const sources=JSON.parse(readFileSync(sourceFile,'utf8'));
let engine=new PGLiteEngine();const started=performance.now();
await engine.connect({database_path:resolve(out,'database')});await engine.initSchema();
const report:any={upstream:'46ad5153a362815e4bd7a21f804561d492816fc5',scope:'keyless explicit-fact storage; no automatic extraction',startup_ms:performance.now()-started,calls:[],checks:{}};
const save=()=>writeFileSync(resolve(out,'report.json'),JSON.stringify(report,null,2));
async function call(name:string,params:any,sourceId='default',allowError=false){
 const at=performance.now();const res=await dispatchToolCall(engine,name,params,{remote:true,sourceId,takesHoldersAllowList:['world']});
 const body=JSON.parse(res.content[0].text);report.calls.push({name,params,sourceId,isError:!!res.isError,body,ms:performance.now()-at});save();
 if(res.isError&&!allowError)throw new Error(JSON.stringify(body));return body;
}
const texts=(r:any)=>(r.facts??[]).map((f:any)=>f.fact);
try{
 for(const s of sources){await call('put_page',{slug:'recordings/'+s.session_id,content:`---\ntitle: ${s.session_id}\ntype: meeting\n---\n\n`+s.passages.map((p:any)=>`[${p.id}] ${p.text}`).join('\n')});}
 const entity='projects/juniper';
 const first=await call('remember',{fact:"Project Juniper's meeting location is the library.",entity,provenance:'recordings/'+sources[0].session_id+'#p1,p3'});
 const recall=await call('recall',{entity});
 report.checks.explicit_fact_recall=texts(recall).some((t:string)=>t.includes('library'));
 report.checks.provenance_present=(recall.facts??[]).some((f:any)=>String(f.provenance).includes(sources[0].session_id));
 const correction=await call('remember',{fact:'Project Juniper now meets at the community center instead of the library.',entity,provenance:'recordings/'+sources[1].session_id+'#p1'});
 const corrected=await call('recall',{entity});
 report.checks.automatic_correction=texts(corrected).some((t:string)=>t.includes('community center'))&&!texts(corrected).includes("Project Juniper's meeting location is the library.");
 // Probe source deletion without disguising an extra fact-forget operation as native cascade.
 const page=await call('get_page',{slug:'recordings/'+sources[1].session_id});
 const deletion=await call('delete_page',{slug:'recordings/'+sources[1].session_id,expected_revision:page.revision??page.page?.revision});
 const afterDelete=await call('recall',{entity});
 report.checks.recording_delete_invalidates_derived_fact=!texts(afterDelete).some((t:string)=>t.includes('community center'));
 await call('forget',{id:String(correction.id),reason:'Synthetic withdrawal check'});
 report.checks.explicit_withdrawal=!texts(await call('recall',{entity})).some((t:string)=>t.includes('community center'));
 const reinsert=await call('remember',{fact:'Project Juniper now meets at the community center instead of the library.',entity,provenance:'synthetic stale reimport'},'default',true);
 report.checks.withdrawal_blocks_reinsert=!!reinsert.error;
 // Storage-only probe matching the documented DB-only extraction metadata.
 await call('put_page',{slug:'recordings/structured',content:'---\ntitle: Structured provenance probe\ntype: meeting\n---\n\nMaya enjoys swimming.'});
 const seeded=await engine.insertFact({fact:'Maya enjoys swimming.',kind:'preference',entity_slug:'people/maya',visibility:'world',source:'conversation',source_session:'structured',context:'recordings/structured'}, {source_id:'default'});
 report.checks.structured_fact_visible_before_delete=texts(await call('recall',{entity:'people/maya'})).includes('Maya enjoys swimming.');
 const structuredPage=await call('get_page',{slug:'recordings/structured'});
 await call('delete_page',{slug:'recordings/structured',expected_revision:structuredPage.revision??structuredPage.page?.revision});
 report.checks.structured_recording_delete_invalidates_fact=!texts(await call('recall',{entity:'people/maya'})).includes('Maya enjoys swimming.');
 await engine.executeRaw("INSERT INTO sources(id,name) VALUES('other-user','other-user') ON CONFLICT DO NOTHING");
 report.checks.source_scope_isolation=texts(await call('recall',{entity},'other-user')).length===0;
 await engine.disconnect();engine=new PGLiteEngine();await engine.connect({database_path:resolve(out,'database')});await engine.initSchema();
 report.checks.restart_preserves_withdrawal=!texts(await call('recall',{entity})).some((t:string)=>t.includes('community center'));
 report.provider_attempts=providerAttempts;report.max_rss=process.resourceUsage().maxRSS;save();
 console.log(JSON.stringify({checks:report.checks,provider_attempts:providerAttempts,max_rss:report.max_rss}));
} catch(e){report.failure=String(e);save();throw e;} finally {await engine.disconnect();}
