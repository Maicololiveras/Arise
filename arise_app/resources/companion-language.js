const ARISE_EN = {"WEG · Celular": "WEG · Phone", "Abre el icono WEG y vincula el chat allí. Mantén Tailscale conectado y el PC encendido. No necesitas una tienda de aplicaciones.": "Open the WEG icon and pair your chat there. Keep Tailscale connected and the PC on. No app store is needed.", "Adjunta hasta cuatro imágenes.": "Attach up to four images.", "Adjuntar imágenes": "Attach images", "Aprobar esta acción": "Approve this action", "Cada imagen debe ser PNG/JPEG y ocupar hasta 2 MB.": "Each image must be PNG/JPEG and no larger than 2 MB.", "Chat inactivo en el PC · historial disponible": "Chat inactive on PC · history available", "Conecta Tailscale y escanea el QR de WEG en tu PC.": "Connect Tailscale and scan WEG's QR on your PC.", "Conectado al PC · permisos del chat conservados": "Connected to PC · chat permissions preserved", "Continuar este chat en el PC": "Continue this chat on the PC", "Código del PC": "PC code", "Código del autenticador": "Authenticator code", "Decisiones pendientes": "Pending decisions", "Desvincular": "Unpair", "Detener": "Stop", "El PC realiza las tareas. Hablar graba hasta 29 segundos y transcribe en tu PC; revisa el texto antes de enviarlo. Escuchar usa una voz instalada en Windows. Puedes detener el trabajo en cualquier momento.": "The PC runs tasks. Speak records up to 29 seconds and transcribes on your PC; review before sending. Listen uses a Windows voice. You can stop work at any time.", "Enviar al PC": "Send to PC", "Escuchando · máximo 29 segundos. Al terminar podrás revisar el texto.": "Listening · up to 29 seconds. Review the text when finished.", "Escuchar": "Listen", "Hablar": "Speak", "Instalar WEG": "Install WEG", "La grabación fue demasiado corta.": "The recording was too short.", "Mensaje": "Message", "No se confirmó la operación.": "The operation was not confirmed.", "No se pudo abrir el micrófono. Revisa el permiso de WEG y vuelve a intentar.": "Could not open the microphone. Check WEG's permission and try again.", "No se pudo generar la voz.": "Could not generate speech.", "No se pudo leer la imagen.": "Could not read the image.", "Nombre del celular": "Phone name", "Parada confirmada por el PC.": "Stop confirmed by the PC.", "Rechazar": "Reject", "Revisa el texto y pulsa Enviar. El audio no se guardó como archivo permanente.": "Review the text and press Send. Audio was not saved as a permanent file.", "Teléfono desvinculado. Genera otro QR en el PC para volver.": "Phone unpaired. Generate another QR on the PC to reconnect.", "Terminar grabación": "Finish recording", "Transcribiendo en tu PC…": "Transcribing on your PC…", "Tu aprobación: ": "Your approval: ", "Tú": "You", "Usar WEG como app": "Use WEG as an app", "Vincular": "Pair", "iPhone/iPad: abre esta dirección en Safari, pulsa Compartir → Añadir a pantalla de inicio y activa Abrir como app web si aparece. Android: menú del navegador → Instalar aplicación o Añadir a pantalla de inicio.": "iPhone/iPad: open this address in Safari, tap Share → Add to Home Screen and enable Open as Web App if shown. Android: browser menu → Install app or Add to Home Screen."};
// Only the display language is stored. Never persist chat, audio, pairing or MFA data.
(() => {
  let preference = null;
  try { preference = localStorage.getItem('arise-ui-language'); } catch (_) {}
  let locale = preference === 'en' ? 'en' : 'es';
  const sources = new WeakMap();
  const translate = source => locale === 'en' ? (ARISE_EN[source] || source) : source;
  const ignored = node => node.parentElement?.closest('script,style,textarea,#messages article,#approvals p,#approvals [data-user-content]') && !node.parentElement?.closest('button,[data-ui-label]');
  const refresh = () => {
    observer.disconnect();
    document.documentElement.lang = locale;
    document.title = translate('WEG · Celular');
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      if (ignored(node) || node.parentElement?.id === 'language') continue;
      const current = node.nodeValue, old = sources.get(node);
      const source = old && old.rendered === current ? old.source : current;
      const rendered = translate(source);
      if (current !== rendered) node.nodeValue = rendered;
      sources.set(node, {source, rendered});
    }
    for (const input of document.querySelectorAll('input[placeholder]')) {
      const current=input.placeholder,old=sources.get(input);
      const source=old && old.rendered===current?old.source:current;
      const rendered=translate(source);input.placeholder=rendered;sources.set(input,{source,rendered});
    }
    document.getElementById('language').textContent = locale === 'en' ? 'Español' : 'English';
    observer.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['placeholder']});
  };
  const observer = new MutationObserver(refresh);
  document.getElementById('language').onclick = () => {
    locale = locale === 'en' ? 'es' : 'en'; preference=locale;
    try {localStorage.setItem('arise-ui-language',locale);} catch (_) {}
    refresh();
  };
  window.ariseLanguage = {defaultLanguage(value) {if(!preference && ['es','en'].includes(value) && locale!==value){locale=value;refresh();}}};
  refresh();
})();
