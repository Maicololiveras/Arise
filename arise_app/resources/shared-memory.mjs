// Adopt only a verified, already-running local server. Never spawn or stop Engram.
import http from 'node:http';
import net from 'node:net';
import {pathToFileURL} from 'node:url';
import {join} from 'node:path';

const endpoint = 'http://127.0.0.1:7437';
const conflicts = ['ENGRAM_BIN','ENGRAM_URL','ENGRAM_DATA_DIR','ENGRAM_PORT','ENGRAM_SOCKET',
  'ENGRAM_DATABASE_URL','ENGRAM_SERVER_MODE','ENGRAM_HTTP_TOKEN','ENGRAM_STARTUP_POLICY'];
export async function sharedMemory(root, env = process.env, notify = () => {}) {
  if (conflicts.some(key => String(env[key] || '').trim())) throw new Error('Conflicting Engram selection');
  const native = await import(pathToFileURL(join(root,'runtime/gentle-shell-bundled.mjs')).href);
  if (!native.engramProbeAllowed(env)) throw new Error('Native Engram policy rejected shared adoption');
  // One persistent transport. If that server closes its socket, never reconnect to
  // a replacement listener within this session (including between check and use).
  const agent = new http.Agent({keepAlive:true, maxSockets:1});
  let opened = false, failed = false, identity, queue = Promise.resolve();
  agent.createConnection = options => {
    if (opened) throw new Error('Shared Engram connection closed; reconnect ARISE');
    opened = true;
    return net.createConnection({host:'127.0.0.1',port:7437});
  };
  function raw(path, options = {}) {
    return new Promise((resolve,reject) => {
      const request=http.request(endpoint+path,{method:options.method||'GET',agent,
        headers:options.headers||{accept:'application/json'}}, response => {
        const chunks=[];let size=0;
        response.on('data',chunk=>{size+=chunk.length;if(size>(path==='/compatibility'?16384:16*1024*1024))request.destroy(new Error('Response too large'));else chunks.push(chunk);});
        response.on('end',()=>resolve({status:response.statusCode,headers:response.headers,body:Buffer.concat(chunks)}));
        response.on('error',reject);
      });
      request.setTimeout(5000,()=>request.destroy(new Error('Shared Engram timed out')));
      request.on('error',reject);
      if(options.signal) {
        if(options.signal.aborted) {request.destroy(new Error('Cancelled'));return;}
        options.signal.addEventListener('abort',()=>request.destroy(new Error('Cancelled')),{once:true});
      }
      request.end(options.body);
    });
  }
  async function verify() {
    const response=await raw('/compatibility');
    const text=response.body.toString();
    if(response.status!==200||!native.isReadyCompatibility(text))throw new Error('Incompatible shared Engram');
    const value=JSON.parse(text), current=value.instance_id+':'+value.runtime_id;
    if(identity && identity!==current)throw new Error('Shared Engram identity changed');
    identity=current;
    return value;
  }
  function run(action) {
    const next=queue.then(async()=>{
      if(failed)throw new Error('Shared memory disconnected; reconnect ARISE');
      try{return await action();}catch(error){failed=true;agent.destroy();notify('error');throw error;}
    });
    queue=next.catch(()=>{});
    return next;
  }
  await run(verify);
  const decision=native.classifyEngramStartup({env,core:false,endpoint:{kind:'listening',compatible:true}});
  if(decision.policy!=='allow'||decision.spawn||decision.url!==endpoint) {agent.destroy();throw new Error('Shared adoption rejected');}
  notify('verifying');
  return {
    close(){failed=true;agent.destroy();},
    verify:()=>run(verify),
    install(){
      // Explicit URL disables gentle-engram's implicit local spawn/recovery path.
      env.ENGRAM_URL=endpoint;
      env.ENGRAM_STARTUP_POLICY='allow';
      const original=globalThis.fetch;
      globalThis.fetch=(input,options={})=>{
        const url=new URL(typeof input==='string'||input instanceof URL?input:input.url);
        if(url.origin!==endpoint)return original(input,options);
        return run(async()=>{
          await verify();
          const headers=Object.fromEntries(new Headers(options.headers));
          const answer=await raw(url.pathname+url.search,{...options,headers});
          await verify();
          return new Response([204,205,304].includes(answer.status)?null:answer.body,{status:answer.status,headers:answer.headers});
        });
      };
      const timer=setInterval(()=>run(verify).catch(()=>{}),5000);timer.unref();
      return ()=>{clearInterval(timer);globalThis.fetch=original;agent.destroy();};
    }
  };
}
if(process.argv[2]==='--verify'){
  try{const connection=await sharedMemory(process.argv[3]);connection.close();}
  catch{process.exitCode=1;}
}
