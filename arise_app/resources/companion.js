const $=id=>document.getElementById(id);let busy=false,last='',online=false,refreshing=false;
async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined,credentials:'same-origin'});const data=await r.json();if(!r.ok){if(r.status===401){online=false;$('pair').hidden=false;}throw Error(data.error||'No se confirmó la operación.');}return data;}
async function refresh(){if(refreshing)return;refreshing=true;try{const data=await api('/messages');online=true;$('pair').hidden=true;if($('activate'))$('activate').hidden=data.active;renderApprovals(data.approvals||[]);$('status').textContent=data.active?'Conectado al PC · permisos del chat conservados':'Chat inactivo en el PC · historial disponible';const signature=JSON.stringify(data.messages);if(signature===last)return;last=signature;const nearBottom=window.innerHeight+window.scrollY>=document.body.scrollHeight-100;$('messages').replaceChildren(...data.messages.map(m=>{const a=document.createElement('article');a.textContent=(m.role==='user'?'Tú':'ARISE')+'\n'+m.text;
if(m.role==='assistant'){const play=document.createElement('button');play.textContent='Escuchar';play.type='button';play.onclick=()=>speakReply(m.id);a.appendChild(play);}return a;}));if(nearBottom)window.scrollTo(0,document.body.scrollHeight);}catch(e){online=false;$('status').textContent=e.message;}finally{refreshing=false;}}
$('pair').onsubmit=async e=>{e.preventDefault();try{await api('/pair',{code:$('code').value.trim(),name:$('name').value,otp:$('otp').value.trim()});$('code').value='';$('otp').value='';await refresh();}catch(e){$('status').textContent=e.message;}};
$('compose').onsubmit=async e=>{e.preventDefault();if(busy)return;busy=true;$('send').disabled=true;const text=$('draft').value;try{const images=await readImages();await api('/prompt',{text,images});if($('images'))$('images').value='';if($('draft').value===text)$('draft').value='';await refresh();}catch(e){$('status').textContent=e.message+' Borrador conservado; verifica el chat antes de repetir.';}finally{busy=false;$('send').disabled=false;}};
$('stop').onclick=async()=>{if(recorder)recorder.stop();if(playing)playing.pause();try{await api('/stop',{});$('status').textContent='Parada confirmada por el PC.';}catch(e){$('status').textContent=e.message;}};
setInterval(refresh,4000);setInterval(async()=>{if(!online)return;try{await api('/renew',{});}catch(e){online=false;$('pair').hidden=false;$('status').textContent=e.message;}},300000);refresh();

document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});

// Pairing secrets stay in the fragment and are removed before any network request.
if (typeof location !== 'undefined' && location.hash) {
  const parameters=new URLSearchParams(location.hash.slice(1));
  const code=parameters.get('code');
  if(code && code.length<=200) $('code').value=code;
  history.replaceState(null,'',location.pathname);
}

let recorder=null,playing=null;
async function speakReply(id){
  if(playing){playing.pause();URL.revokeObjectURL(playing.src);playing=null;}
  try{const r=await fetch('/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id}),credentials:'same-origin'});
    if(!r.ok)throw Error((await r.json()).error||'No se pudo generar la voz.');
    playing=new Audio(URL.createObjectURL(await r.blob()));playing.onended=()=>URL.revokeObjectURL(playing.src);await playing.play();
  }catch(e){$('status').textContent=e.message;}
}
async function recordVoice(){
  if(recorder){recorder.stop();return;}
  let stream,context,node,source,timer,finished=false;
  try{
    if(!online)throw Error('Vincula el teléfono antes de hablar.');
    stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true},video:false});
    context=new AudioContext();source=context.createMediaStreamSource(stream);node=context.createScriptProcessor(4096,1,1);
    const chunks=[];let size=0;
    const stop=async()=>{
      if(finished)return;finished=true;clearTimeout(timer);recorder=null;
      node.disconnect();source.disconnect();stream.getTracks().forEach(t=>t.stop());
      const rate=context.sampleRate;await context.close();$('record').textContent='Hablar';$('record').disabled=true;
      try{
        const input=new Float32Array(size);let offset=0;for(const c of chunks){input.set(c,offset);offset+=c.length;}
        const count=Math.min(480000,Math.floor(size*16000/rate));if(count<1600)throw Error('La grabación fue demasiado corta.');
        const buffer=new ArrayBuffer(44+count*2),v=new DataView(buffer);
        const word=(o,t)=>{for(let i=0;i<t.length;i++)v.setUint8(o+i,t.charCodeAt(i));};
        word(0,'RIFF');v.setUint32(4,36+count*2,true);word(8,'WAVE');word(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,16000,true);v.setUint32(28,32000,true);v.setUint16(32,2,true);v.setUint16(34,16,true);word(36,'data');v.setUint32(40,count*2,true);
        for(let i=0;i<count;i++){const start=Math.floor(i*rate/16000),end=Math.min(size,Math.max(start+1,Math.floor((i+1)*rate/16000)));let sum=0;for(let j=start;j<end;j++)sum+=input[j];const sample=Math.max(-1,Math.min(1,sum/(end-start)));v.setInt16(44+i*2,sample<0?sample*32768:sample*32767,true);}
        let binary='';const bytes=new Uint8Array(buffer);for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
        $('status').textContent='Transcribiendo en tu PC…';const result=await api('/transcribe',{audio:btoa(binary)});
        $('draft').value+=($('draft').value?'\n':'')+result.text;$('status').textContent='Revisa el texto y pulsa Enviar. El audio no se guardó como archivo permanente.';
      }catch(e){$('status').textContent=e.message;}finally{$('record').disabled=false;}
    };
    recorder={stop};node.onaudioprocess=e=>{if(finished)return;const c=new Float32Array(e.inputBuffer.getChannelData(0));chunks.push(c);size+=c.length;if(size>=context.sampleRate*29)stop();};
    source.connect(node);node.connect(context.destination);timer=setTimeout(stop,29000);
    $('record').textContent='Terminar grabación';$('status').textContent='Escuchando · máximo 29 segundos. Al terminar podrás revisar el texto.';
  }catch(e){if(stream)stream.getTracks().forEach(t=>t.stop());if(context)context.close();recorder=null;$('status').textContent='No se pudo abrir el micrófono. Revisa el permiso de ARISE y vuelve a intentar.';}
}
if($('record'))$('record').onclick=recordVoice;
document.addEventListener('visibilitychange',()=>{if(document.hidden){if(recorder)recorder.stop();if(playing)playing.pause();}});

let approvalSignature='';
function renderApprovals(items){
  if(!$('approvals'))return;
  const signature=JSON.stringify(items);if(signature===approvalSignature)return;approvalSignature=signature;
  $('approvals').replaceChildren(...items.map(item=>{
    const card=document.createElement('article'),title=document.createElement('strong'),preview=document.createElement('p'),code=document.createElement('input');
    title.textContent='Tu aprobación: '+item.action;preview.textContent=typeof item.preview==='string'?item.preview:JSON.stringify(item.preview);
    code.placeholder='Código del autenticador';code.inputMode='numeric';code.maxLength=6;code.autocomplete='one-time-code';
    card.append(title,preview,code);
    for(const approved of [true,false]){const button=document.createElement('button');button.textContent=approved?'Aprobar esta acción':'Rechazar';button.onclick=async()=>{
      button.disabled=true;try{await api('/approval',{id:item.id,approved,otp:code.value.trim()});await refresh();}catch(e){$('status').textContent=e.message;}finally{button.disabled=false;code.value='';}
    };card.appendChild(button);}return card;
  }));
}
if($('activate'))$('activate').onclick=async()=>{try{await api('/activate',{});await refresh();}catch(e){$('status').textContent=e.message;}};

async function readImages(){
  const files=$('images')?Array.from($('images').files||[]):[];
  if(files.length>4)throw Error('Adjunta hasta cuatro imágenes.');
  return Promise.all(files.map(file=>{
    if(!['image/jpeg','image/png'].includes(file.type)||file.size>2097152)throw Error('Cada imagen debe ser PNG/JPEG y ocupar hasta 2 MB.');
    return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve({mimeType:file.type,data:reader.result.split(',')[1]});reader.onerror=()=>reject(Error('No se pudo leer la imagen.'));reader.readAsDataURL(file);});
  }));
}
if($('logout'))$('logout').onclick=async()=>{try{await api('/logout',{});online=false;$('pair').hidden=false;$('messages').replaceChildren();last='';$('status').textContent='Teléfono desvinculado. Genera otro QR en el PC para volver.';}catch(e){$('status').textContent=e.message;}};
