import { createRequire } from 'node:module';
const {MsEdgeTTS,OUTPUT_FORMAT}=createRequire(new URL('../node/package.json',import.meta.url))('msedge-tts');
import { isAbsolute, dirname, extname } from 'node:path';
import { rename, unlink } from 'node:fs/promises';

// Adapted from Forge msedge-tts synthesis. ARISE owns cancellable PCM playback.
export class EdgeSpeech {
  constructor({create=()=>new MsEdgeTTS()}={}) {this.create=create;this.tts=null;this.generation=0;}
  async synthesize({text,voice='es-CO-GonzaloNeural',rate='+5%',output}) {
    if(typeof text!=='string'||!text.trim()||text.length>10000)throw Error('Texto inválido.');
    if(voice!=='es-CO-GonzaloNeural'||!/^[-+]\d{1,2}%$/.test(rate))throw Error('Voz o velocidad no compatible.');
    if(typeof output!=='string'||!isAbsolute(output)||extname(output)!=='.mp3')throw Error('Destino MP3 inválido.');
    this.stop();const generation=this.generation;const tts=this.create();this.tts=tts;let generated;
    try {
      await tts.setMetadata(voice,OUTPUT_FORMAT.AUDIO_24KHZ_48KBITRATE_MONO_MP3);
      const result=await tts.toFile(dirname(output),text,{rate});generated=result.audioFilePath;
      if(this.generation!==generation)throw Error('Síntesis cancelada.');
      await rename(generated,output);generated=null;
      return {status:'completed',voice,rate,output};
    } finally {tts.close();if(this.tts===tts)this.tts=null;if(generated)await unlink(generated).catch(()=>{});}
  }
  stop(){this.generation++;this.tts?.close();this.tts=null;}
}
