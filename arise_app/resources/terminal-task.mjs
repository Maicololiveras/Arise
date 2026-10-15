// A single visible Gentle task. No ARISE bridge credentials, peer messaging or private reasoning logs.
import {readFileSync,writeFileSync,renameSync} from 'node:fs';
import {join} from 'node:path';
export default function terminalTask(pi) {
  const directory=process.env.ARISE_TERMINAL_TASK;
  if (!directory) return;
  let started=false;
  pi.on('tool_call',event=>{
    if (['orchestrator_list','orchestrator_consult','orchestrator_send_message'].includes(event.toolName))
      return {block:true,reason:'Esta terminal pertenece a una delegación de ARISE; no tiene autorización para contactar otras sesiones.'};
  });
  pi.on('session_start',(_event,ctx)=>{
    if(started)return;
    started=true;
    const {task}=JSON.parse(readFileSync(join(directory,'task.json'),'utf8'));
    ctx.ui.notify('Tarea delegada por ARISE. Detener o cambiar de chat cerrará esta terminal.','info');
    pi.sendUserMessage(task);
  });
  pi.on('agent_end',(event,ctx)=>{
    const replies=(event.messages||[]).filter(m=>m.role==='assistant');
    const text=replies.flatMap(m=>(m.content||[]).filter(b=>b.type==='text').map(b=>b.text)).join('\n').slice(0,60000);
    const failed=replies.some(m=>['error','aborted'].includes(m.stopReason));
    const tmp=join(directory,'result.tmp');
    writeFileSync(tmp,JSON.stringify({status:failed?'failed':'completed',text}));
    renameSync(tmp,join(directory,'result.json'));
    ctx.shutdown();
  });
}
