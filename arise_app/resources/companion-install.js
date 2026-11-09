// Installation is optional; pairing and all work remain on the private PC.
(() => {
  const button = document.getElementById('install-app');
  const help = document.getElementById('install-help');
  let pending = null;
  const standalone = window.matchMedia('(display-mode: standalone)');
  const update = () => { help.hidden = standalone.matches || navigator.standalone === true; };
  update();
  standalone.addEventListener('change', update);
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    pending = event;
    button.hidden = false;
  });
  button.onclick = async () => {
    if (!pending) return;
    const request = pending;
    pending = null;
    button.hidden = true;
    try { await request.prompt(); await request.userChoice; }
    catch (_) { help.hidden = false; }
  };
  window.addEventListener('appinstalled', () => {
    pending = null;
    button.hidden = true;
    help.hidden = true;
  });
  // No service worker, offline queue, credential storage or cached conversations.
})();
