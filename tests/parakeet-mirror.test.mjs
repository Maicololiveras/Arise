import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync, mkdtempSync, rmSync, existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {PARAKEET_MODEL_MANIFEST, VOICE_TARGETS, VOICE_MIRROR_BASE, VOICE_MIRROR_REDIRECTS, voiceRuntimeManifest} from '../arise_app/resources/parakeet/lib/voice-artifacts.mjs';
import {installVoiceModel} from '../arise_app/resources/parakeet/lib/voice-install.mjs';

test('every model and runtime uses GitHub and keeps the original upstream pins',()=>{
  const source=JSON.parse(readFileSync(new URL('../distribution/parakeet/manifest.json',import.meta.url)));
  const originals=new Map(source.files.map(f=>[f.name,f]));
  assert.equal(PARAKEET_MODEL_MANIFEST.baseUrl,VOICE_MIRROR_BASE);
  assert.deepEqual(PARAKEET_MODEL_MANIFEST.redirects,VOICE_MIRROR_REDIRECTS);
  for(const f of PARAKEET_MODEL_MANIFEST.files){
    const original=originals.get(f.name);
    assert.equal(f.size,original.size);assert.equal(f.sha256,original.digest);
  }
  for(const target of VOICE_TARGETS){
    const runtime=voiceRuntimeManifest(target);
    assert.deepEqual(runtime.redirects,VOICE_MIRROR_REDIRECTS);
    for(const p of runtime.packages){
      const filename=`${p.name}-${p.version}.tgz`;
      assert.equal(p.tarball,`${VOICE_MIRROR_BASE}/${filename}`);
      assert.equal(p.size,originals.get(filename).size);
      assert.equal(p.integrity,originals.get(filename).digest);
    }
  }
});

test('GitHub CDN redirect works; foreign redirect and modified bytes never publish',async()=>{
  const payload=Buffer.from('pinned speech model fixture');
  const manifest={id:'mirror-test',revision:'fixed',baseUrl:VOICE_MIRROR_BASE,
    files:[{name:'model.onnx',size:payload.length,sha256:createHash('sha256').update(payload).digest('hex')}],redirects:VOICE_MIRROR_REDIRECTS};
  for(const mode of ['ok','foreign','corrupt']){
    const voiceHome=mkdtempSync(path.join(tmpdir(),'arise-mirror-'));
    try{
      const fetch=async url=>{
        if(url.startsWith(VOICE_MIRROR_BASE))return new Response(null,{status:302,headers:{location:mode==='foreign'?'https://example.com/model':'https://release-assets.githubusercontent.com/github-production-release-asset/123/model?signature=test'}});
        assert.ok(url.startsWith('https://release-assets.githubusercontent.com/'));
        return new Response(mode==='corrupt'?Buffer.alloc(payload.length):payload,{status:200});
      };
      if(mode==='ok'){
        const result=await installVoiceModel({voiceHome,manifest,fetch});
        assert.deepEqual(readFileSync(path.join(result.path,'model.onnx')),payload);
      }else{
        await assert.rejects(installVoiceModel({voiceHome,manifest,fetch}),e=>e.code===(mode==='foreign'?'redirect':'integrity'));
        assert.equal(existsSync(path.join(voiceHome,'models',manifest.id)),false);
      }
    }finally{rmSync(voiceHome,{recursive:true,force:true});}
  }
});
