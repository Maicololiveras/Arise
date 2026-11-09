import {createInterface} from 'node:readline';
import {EdgeSpeech} from './edge-speech.mjs';
const edge=new EdgeSpeech();
const send=value=>process.stdout.write(JSON.stringify(value)+'\n');
const input=createInterface({input:process.stdin,crlfDelay:Infinity});
input.on('line',async line=>{let r;try{r=JSON.parse(line);let data;
if(r.type==='synthesize_edge') data=await edge.synthesize(r);
else if(r.type==='cancel'){edge.stop();data={status:'cancelled'};}
else throw Error('Comando no compatible.');
send({type:'response',id:r.id,success:true,data});
}catch(e){send({type:'response',id:r?.id,success:false,error:String(e?.message??e)});}});
input.on('close',()=>{edge.stop();process.exit(0);});
process.on('SIGTERM',()=>{edge.stop();process.exit(0);});
