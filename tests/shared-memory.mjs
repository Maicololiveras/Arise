import assert from 'node:assert/strict';
import http from 'node:http';
import {mkdtemp,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {spawn} from 'node:child_process';
import {sharedMemory} from '../arise_app/resources/shared-memory.mjs';
const root=process.argv[2];
let ready=true, identity='a'.repeat(32), calls=0;
const server=http.createServer((req,res)=>{
  res.setHeader('content-type','application/json');
  if(req.url==='/compatibility')res.end(JSON.stringify({status:ready?'ready':'blocked',active_reuse_authorized:true,capability:'startup-verified-store-v1',revision:1,source:'active',offline_automatic_opening_authorized:false,instance_id:identity,runtime_id:'b'.repeat(32)}));
  else {calls++;res.end(JSON.stringify({ok:true}));}
});
await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(7437,'127.0.0.1',resolve);});
try {
  await assert.rejects(sharedMemory(root,{ENGRAM_BIN:'/explicit'}));
  ready=false;await assert.rejects(sharedMemory(root,{}));ready=true;
  const home=await mkdtemp(join(tmpdir(),'arise-memory-'));
  try {
    const cli=join(home,'synthetic.mjs');
    await writeFile(cli, `import assert from 'node:assert/strict';
      assert.equal(process.env.ENGRAM_DATA_DIR,undefined);
      assert.equal(process.env.ENGRAM_SERVER_MODE,undefined);
      assert.equal(process.env.ENGRAM_BIN,undefined);
      assert.equal(process.env.ENGRAM_URL,'http://127.0.0.1:7437');
      const result=await fetch(process.env.ENGRAM_URL+'/synthetic');
      assert.equal(result.status,200);
      console.log('ADAPTER_OK');`);
    const env={...process.env,ARISE_GENTLE_ROOT:root,ARISE_GENTLE_HOME:home,ARISE_MEMORY_MODE:'shared'};
    for(const key of Object.keys(env))if(key.startsWith('ENGRAM_'))delete env[key];
    const result=await new Promise(resolveResult=>{
      const child=spawn(process.execPath,[resolve('arise_app/resources/gentle-shell.mjs'),cli],{env});
      let out='',error='';
      child.stdout.on('data',data=>out+=data);child.stderr.on('data',data=>error+=data);
      child.on('exit',code=>resolveResult({code,out,error}));
    });
    assert.equal(result.code,0,result.error);assert.match(result.out,/ADAPTER_OK/);
    calls=0;
  } finally {await rm(home,{recursive:true,force:true});}
  const states=[],env={};
  const connection=await sharedMemory(root,env,state=>states.push(state));
  const restore=connection.install();
  assert.equal(env.ENGRAM_URL,'http://127.0.0.1:7437');
  assert.equal(env.ENGRAM_BIN,undefined);
  assert.deepEqual(await (await fetch(env.ENGRAM_URL+'/synthetic')).json(),{ok:true});
  assert.equal(calls,1);
  identity='c'.repeat(32);
  await assert.rejects(fetch(env.ENGRAM_URL+'/synthetic'));
  assert.equal(calls,1,'changed server cannot receive memory operations');
  assert.equal(states.at(-1),'error');
  restore();
  assert.equal(server.listening,true,'ARISE must never stop the external server');
  // Closing the validated transport cannot silently reconnect or spawn.
  const second=await sharedMemory(root,{});
  const restore2=second.install();
  server.closeAllConnections();
  await new Promise(resolve=>setTimeout(resolve,30));
  await assert.rejects(fetch('http://127.0.0.1:7437/synthetic'));
  assert.equal(calls,1);
  restore2();
} finally {server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
await assert.rejects(sharedMemory(root,{}),'missing listener must fail without spawn');
console.log('Shared memory native contract, pinned transport and lifecycle passed');
