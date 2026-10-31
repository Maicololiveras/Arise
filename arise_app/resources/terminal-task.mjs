// A chat-owned mailbox, not a bridge to other sessions or ARISE credentials.
import {readFileSync,writeFileSync,renameSync,readdirSync,unlinkSync,mkdirSync,statSync} from 'node:fs';
import {join} from 'node:path';
import {randomUUID} from 'node:crypto';
export default function terminalTask(pi) {
  const directory=process.env.ARISE_TERMINAL_TASK;
  if (!directory) return;
  const inbox=join(directory,'inbox'); mkdirSync(inbox,{recursive:true});
  let started=false, finished=false, finishReport=null, context, question=null;
  const atomic=(name,value)=>{const tmp=join(directory,name+'.tmp');writeFileSync(tmp,JSON.stringify(value));renameSync(tmp,join(directory,name+'.json'));};
  const state=(status,text='',request=null)=>atomic('state',{status,text:text.slice(0,60000),question:request});
  const schema=(properties,required)=>({type:'object',properties,required,additionalProperties:false});
  const textSchema={type:'string',minLength:1,maxLength:12000};
  const result=text=>({content:[{type:'text',text}],details:undefined});
  pi.registerTool({name:'arise_ask_user',label:'Ask through ARISE',description:'Ask the user a blocking question in the originating ARISE chat. Wait for their reply; never invent approval.',parameters:schema({question:textSchema},['question']),
    async execute(_id,args,signal){
      if(question)throw Error('A question is already pending');
      if(typeof args.question!=='string'||!args.question.trim()||args.question.length>12000)throw Error('Invalid question');
      const id=randomUUID();question={id,prompt:args.question};state('waiting_user','',question);
      try {
        while(!finished){
          if(signal?.aborted)throw Error('Question cancelled');
          const path=join(directory,'reply-'+id+'.json');
          try {
            if(statSync(path).size>65536)throw Error('Reply exceeds limit');
            const reply=JSON.parse(readFileSync(path,'utf8'));unlinkSync(path);
            if(reply.cancelled)throw Error('User declined the question. Do not treat this as approval.');
            if(typeof reply.value!=='string')throw Error('Invalid reply');
            return result(reply.value.slice(0,12000));
          }catch(error){if(error.code!=='ENOENT')throw error;}
          await new Promise(resolve=>setTimeout(resolve,200));
        }
        throw Error('Delegation stopped');
      }finally{question=null;state('running');}
    }});
  pi.registerTool({name:'arise_finish',label:'Finish delegated task',description:'Report a verified final outcome to ARISE. For missing user input use arise_ask_user instead. Do not report success for unfinished work.',parameters:schema({status:{type:'string',enum:['completed','failed']},summary:textSchema},['status','summary']),
    async execute(_id,args){
      if(!['completed','failed'].includes(args.status)||typeof args.summary!=='string'||!args.summary.trim()||args.summary.length>12000)throw Error('Invalid final report');
      finishReport={status:args.status,text:args.summary};return result('Final outcome recorded; the terminal will close after this turn.');
    }});
  pi.on('before_agent_start',event=>({systemPrompt:event.systemPrompt+'\nThis is an ARISE delegation. Ask blocking questions with arise_ask_user. Remain available for new instructions. Call arise_finish only after verifying completion or reporting a definitive failure. A turn ending is not task completion. Never bypass tool approvals.'}));
  pi.on('tool_call',event=>{
    if (['orchestrator_list','orchestrator_consult','orchestrator_send_message'].includes(event.toolName))
      return {block:true,reason:'This terminal may communicate only with its originating ARISE chat.'};
  });
  const timer=setInterval(()=>{
    if(!context||finished||question)return;
    try{
      for(const name of readdirSync(inbox).filter(n=>/^[0-9]{20}-[a-f0-9]{32}\.json$/.test(n)).sort().slice(0,32)){
        const path=join(inbox,name);
        if(statSync(path).size>65536)throw Error('Instruction exceeds limit');
        const message=JSON.parse(readFileSync(path,'utf8'));
        if(typeof message.text!=='string'||!message.text.trim()||message.text.length>12000)throw Error('Invalid instruction');
        pi.sendUserMessage(message.text,{deliverAs:context.isIdle?.()===false?'steer':'followUp'});
        unlinkSync(path);state('running');
      }
    }catch(error){context.ui.notify('ARISE mailbox: '+error.message,'error');}
  },200);timer.unref();
  pi.on('session_start',(_event,ctx)=>{
    if(started)return;started=true;context=ctx;
    const {task}=JSON.parse(readFileSync(join(directory,'task.json'),'utf8'));
    ctx.ui.notify('ARISE delegation: questions and new instructions stay linked to the originating chat. Stop or switch chat to end it.','info');
    state('running');pi.sendUserMessage(task);
  });
  pi.on('agent_end',(event,ctx)=>{
    if(finished)return;
    const replies=(event.messages||[]).filter(m=>m.role==='assistant');
    const text=replies.flatMap(m=>(m.content||[]).filter(b=>b.type==='text').map(b=>b.text)).join('\n').slice(0,60000);
    const failed=replies.some(m=>['error','aborted'].includes(m.stopReason));
    if(!finishReport&&!failed){state('waiting',text);return;}
    finished=true;clearInterval(timer);
    atomic('result',failed?{status:'failed',text}:finishReport);ctx.shutdown();
  });
  pi.on('session_shutdown',()=>{finished=true;clearInterval(timer);});
}
