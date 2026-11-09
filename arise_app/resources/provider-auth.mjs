// Desktop-only account bridge. Credentials stay in Pi's locked auth store.
import {createInterface} from 'node:readline';
import {pathToFileURL} from 'node:url';
import {join} from 'node:path';
import {randomUUID} from 'node:crypto';
const send = value => process.stdout.write(JSON.stringify(value)+'\n');
for (const name of ['log','info','warn','error','debug']) console[name]=()=>{};
process.on('uncaughtException',()=>process.exit(1));
process.on('unhandledRejection',()=>process.exit(1));
const {ModelRuntime,SettingsManager}=await import(pathToFileURL(join(process.env.ARISE_AUTH_PACKAGE,'dist/index.js')));
const home=process.env.PI_CODING_AGENT_DIR;
const runtime=await ModelRuntime.create({authPath:join(home,'auth.json'),modelsPath:join(home,'models.json'),allowModelNetwork:false});
if (process.env.ARISE_GENTLE_ROOT) {
  const {createRequire}=await import('node:module');
  const require=createRequire(join(process.env.ARISE_AUTH_PACKAGE,'package.json'));
  const {createJiti}=require('jiti');
  const jiti=createJiti(import.meta.url,{fsCache:false});
  const {createNanProviderConfig}=await jiti.import(join(process.env.ARISE_GENTLE_ROOT,'lib/nan-provider.ts'));
  runtime.registerNativeProvider(createNanProviderConfig());
}
const settings=SettingsManager.create(process.cwd(),home);
let flow=null, pending=null, controller=null;
const safeUrl=value=>{try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password?u.href:undefined;}catch{return undefined;}};
const text=value=>typeof value==='string'?value.slice(0,2000):'';
function providers(){return runtime.getProviders().flatMap(p=>{
 const methods=[];
 if(p.auth?.oauth && p.id!=='anthropic')methods.push('oauth');
 if(p.auth?.apiKey)methods.push('api_key');
 return methods.length?[{id:p.id,name:p.name,methods,oauthName:p.auth?.oauth?.name,...runtime.getProviderAuthStatus(p.id)}]:[];
});}
function models(provider){return runtime.getModels(provider).filter(m=>!m.type||m.type==='chat').map(m=>({id:m.id,name:m.name,provider:m.provider}));}
function snapshot(){return flow?{...flow}: {state:'idle'};}
async function call(r){
 if(r.action==='providers')return {providers:providers()};
 if(r.action==='models')return {models:models(r.provider)};
 if(r.action==='status')return snapshot();
 if(r.action==='answer'){
  if(!pending||r.prompt_id!==flow?.prompt?.id||typeof r.value!=='string'||r.value.length>16384)throw Error();
  if(flow.prompt.kind==='secret' && /^[!$]/.test(r.value.trim()))throw Error();
  const resolve=pending;pending=null;delete flow.prompt;flow.state='waiting';resolve(r.value);return snapshot();
 }
 if(r.action==='cancel'){controller?.abort();pending=null;if(flow)flow={state:'cancelled',provider:flow.provider};return snapshot();}
 if(r.action==='logout'){
  if(flow&&['waiting','prompt'].includes(flow.state))throw Error();
  if(!providers().some(p=>p.id===r.provider))throw Error();
  await runtime.logout(r.provider);return {providers:providers()};
 }
 if(r.action==='start'){
  if(flow&&['waiting','prompt'].includes(flow.state))throw Error();
  const provider=providers().find(p=>p.id===r.provider&&p.methods.includes(r.method));if(!provider)throw Error();
  controller=new AbortController();const signal=controller.signal;
  const current={state:'waiting',provider:r.provider};flow=current;
  const interaction={signal,
   prompt:request=>new Promise((resolve,reject)=>{
    if(signal.aborted)return reject(Error());
    const abort=()=>{pending=null;reject(Error());};signal.addEventListener('abort',abort,{once:true});
    current.prompt={id:randomUUID(),kind:request.type,message:text(request.message),placeholder:text(request.placeholder),optional:!!request.optional,
      options:request.options?.map(o=>({id:o.id,label:text(o.label)}))};current.state='prompt';
    pending=value=>{signal.removeEventListener('abort',abort);resolve(value);};
   }),
   notify:event=>{
    if(signal.aborted||flow!==current)return;
    const notice={kind:event.type,message:text(event.instructions||event.message)};
    if(event.type==='auth_url')notice.url=safeUrl(event.url);
    if(event.type==='device_code'){notice.url=safeUrl(event.verificationUri);notice.code=text(event.userCode);notice.expires=event.expiresInSeconds;}
    // Keep the actionable URL/code when a subsequent progress event arrives.
    current.notice={...current.notice,...notice};
   }
  };
  void runtime.login(r.provider,r.method,interaction,{getDeviceId:()=>settings.getOrCreateDeviceId()}).then(()=>{
   if(flow===current&&!signal.aborted)flow={state:'done',provider:r.provider};
  }).catch(()=>{if(flow===current)flow={state:signal.aborted?'cancelled':'error',provider:r.provider,message:'No se pudo completar el acceso. Revisa la autorización e inténtalo de nuevo.'};});
  return snapshot();
 }
 throw Error();
}
const input=createInterface({input:process.stdin,crlfDelay:Infinity});
input.on('line',async line=>{let r;try{if(line.length>24000)throw Error();r=JSON.parse(line);const data=await call(r);send({id:r.id,type:'response',success:true,data});}catch{send({id:r?.id,type:'response',success:false,error:'No se pudo realizar la operación de cuenta.'});}});
input.on('close',()=>{controller?.abort();process.exit(0);});
process.on('SIGTERM',()=>{controller?.abort();process.exit(0);});
