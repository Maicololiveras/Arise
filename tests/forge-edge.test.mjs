import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {EdgeSpeech} from '../vendor/forge-voice/edge-speech.mjs';
test('Gonzalo and +5% reach Forge synthesis without fallback',async()=>{
 const root=await mkdtemp(join(tmpdir(),'arise-edge-'));const calls=[];
 const tts={setMetadata:async(...args)=>calls.push(args),toFile:async(dir,text,opts)=>{calls.push([text,opts]);const path=join(dir,'generated.mp3');await writeFile(path,'fixture');return {audioFilePath:path};},close:()=>{}};
 try {const result=await new EdgeSpeech({create:()=>tts}).synthesize({text:'Hola',output:join(root,'reply.mp3')});assert.equal(result.status,'completed');assert.equal(calls[0][0],'es-CO-GonzaloNeural');assert.equal(calls[1][1].rate,'+5%');assert.equal(await readFile(result.output,'utf8'),'fixture');}finally{await rm(root,{recursive:true,force:true});}
});
test('network error rejects synthesis instead of switching voices',async()=>{
 let closed=false;const tts={setMetadata:async()=>{throw Error('503');},close:()=>{closed=true;}};
 await assert.rejects(new EdgeSpeech({create:()=>tts}).synthesize({text:'Hola',output:join(tmpdir(),'reply.mp3')}),/503/);assert.equal(closed,true);
});
