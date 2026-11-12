import assert from 'node:assert/strict';
import extension from '../arise_app/resources/antigravity.mjs';
const commands=new Map(), providers=new Map(), events=new Map();
const pi=new Proxy({
 registerCommand:(n,c)=>commands.set(n,c), registerProvider:(n,c)=>providers.set(n,c),
 on:(n,f)=>{events.set(n,[...(events.get(n)||[]),f]);},
 getAllTools:()=>[],getActiveTools:()=>[], events:{on(){},emit(){}},
}, {get:(o,k)=>k in o?o[k]:(()=>{})});
await extension(pi);
assert(providers.get('antigravity').models.length>0);
assert(commands.has('agy'));
let picked=false;
await commands.get('agy').handler('',{ui:{select:async(_title,options)=>{picked=true;assert(options.includes('auth'));return undefined;}}});
assert(picked);
const guard=events.get('before_agent_start').at(-1);
process.env.AGY_READONLY='false';delete process.env.ARISE_CODE_ENABLED;
await guard();assert.equal(process.env.AGY_READONLY,'true');
process.env.ARISE_CODE_ENABLED='1';process.env.ARISE_URL='http://127.0.0.1:1';
globalThis.fetch=async(url)=>{assert.equal(new URL(url).pathname,'/api/status');return {ok:true,json:async()=>({capabilities:{local_execution_authorized:true},study_read_only:false})};};
await guard();assert.equal(process.env.AGY_READONLY,'false');
globalThis.fetch=async()=>({ok:true,json:async()=>({capabilities:{local_execution_authorized:true},study_read_only:true})});
await guard();assert.equal(process.env.AGY_READONLY,'true');
globalThis.fetch=async()=>{throw Error('offline')};
await guard();assert.equal(process.env.AGY_READONLY,'true');
console.log('Real upstream provider, RPC selector and permission boundary passed (no session/server/account started).');
