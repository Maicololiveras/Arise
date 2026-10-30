const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
(async () => {
  const elements = Object.fromEntries(['pair','status','messages','code','name','compose','draft','send','stop'].map(id => [id,{hidden:true,value:'',textContent:'',replaceChildren(){}}]));
  let calls=0, response;
  const context={
    document:{getElementById:id=>elements[id],addEventListener(){},createElement:()=>({}),body:{scrollHeight:100}},
    window:{innerHeight:500,scrollY:0,scrollTo(){}},
    setInterval(){}, fetch:()=>{calls++;return new Promise(resolve=>{response=resolve;});},
    Error, JSON
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync('arise_app/resources/companion.js','utf8'), context);
  assert.equal(calls,1);
  await vm.runInContext('refresh()',context);
  assert.equal(calls,1,'concurrent refresh must not overlap');
  response({ok:false,status:401,json:async()=>({error:'Sesión vencida'})});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(elements.pair.hidden,false,'expired cookie must show pairing');
  elements.draft.value='Documento pendiente';
  const send=elements.compose.onsubmit({preventDefault(){}});
  await new Promise(resolve=>setImmediate(resolve));
  response({ok:false,status:503,json:async()=>({error:'No confirmado'})});
  await send;
  assert.equal(elements.draft.value,'Documento pendiente');
  assert.equal(elements.send.disabled,false);
  assert.match(elements.status.textContent,/Borrador conservado/);
  assert.equal(calls,2,'uncertain prompt must not be retried');
  console.log('Companion client: expiry, poll serialization, draft and no retry passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
