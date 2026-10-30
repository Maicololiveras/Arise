import readline from 'node:readline';
import path from 'node:path';
import {rm} from 'node:fs/promises';
import {PARAKEET_MODEL_MANIFEST, voiceRuntimeManifest} from './lib/voice-artifacts.mjs';
import {readVoiceStatus, installVoiceModel, installVoiceRuntime} from './lib/voice-install.mjs';
import {createVoiceSession} from './lib/voice-session.mjs';
import {diagnoseVoicePlatform, readVoicePlatformProbe} from './lib/voice-platform.mjs';

// One UI-owned operation. No Pi tool, shell command or automatic prompt submission.
const send = data => process.stdout.write(JSON.stringify(data)+'\n');
const abort = new AbortController();
let session, cancelled=false, stopRequested;
const stopped = new Promise(resolve => {stopRequested=resolve;});
const input = readline.createInterface({input:process.stdin});
const cancel = () => {cancelled=true; abort.abort(); stopRequested(); void session?.cancel();};
input.on('close',cancel);
input.on('line',line=>{
  if(line==='stop') stopRequested();
  else if(line==='cancel') cancel();
});
try {
  const voiceHome=process.argv[2];
  if(!voiceHome || !path.isAbsolute(voiceHome)) throw {code:'invalid-request'};
  if(Number(process.versions.node.split('.')[0])<22) throw {code:'node-version'};
  const diagnosis=diagnoseVoicePlatform(readVoicePlatformProbe());
  if(diagnosis.support==='unsupported' || !diagnosis.target) throw {code:'unsupported'};
  const target=diagnosis.target;
  if(process.argv[3]==='--repair') {
    await rm(path.join(voiceHome,'models',PARAKEET_MODEL_MANIFEST.id,'.gentle-voice.json'),{force:true});
    await rm(path.join(voiceHome,'runtime',voiceRuntimeManifest(target).id,'.gentle-voice.json'),{force:true});
  }
  const status=await readVoiceStatus({voiceHome,target});
  if(cancelled) throw {code:'cancelled'};
  if(status.runtime?.state!=='installed' || status.model.state!=='installed') {
    send({type:'state',state:'installing'});
    let last=0;
    const onProgress=p=>{if(Date.now()-last>250){last=Date.now();send({type:'progress',received:p.overallReceivedBytes,total:p.overallTotalBytes});}};
    if(status.runtime?.state!=='installed') await installVoiceRuntime({voiceHome,target,signal:abort.signal,onProgress});
    if(status.model.state!=='installed') await installVoiceModel({voiceHome,signal:abort.signal,onProgress});
    if(!cancelled) send({type:'installed'});
  } else {
    session=createVoiceSession({voiceHome,target,onStateChange:state=>{
      if(['starting','recording','transcribing'].includes(state)) send({type:'state',state});
      if(state==='finished') stopRequested();
    }});
    await session.start();
    await stopped;
    if(!cancelled) {
      const result=await session.stop();
      if(!cancelled) send({type:'result',text:result.text,truncated:result.truncated});
    }
  }
} catch(error) {
  if(!cancelled) send({type:'error',code:error?.code || 'internal'});
} finally {
  if(session) await session.dispose();
  input.removeAllListeners('close'); input.close(); process.stdin.destroy();
}
