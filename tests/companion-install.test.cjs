const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
(async () => {
  const button = { hidden: true }, help = { hidden: false }, events = {};
  let prompts = 0;
  const context = {
    document: { getElementById: id => id === 'install-app' ? button : help },
    navigator: {},
    window: { matchMedia: () => ({matches: false, addEventListener() {}}),
      addEventListener: (name, fn) => { events[name] = fn; } }
  };
  vm.runInNewContext(fs.readFileSync('arise_app/resources/companion-install.js', 'utf8'), context);
  assert.equal(button.hidden, true, 'unsupported browsers retain manual instructions');
  await button.onclick();
  events.beforeinstallprompt({preventDefault() {}, prompt: async () => { prompts++; }, userChoice: Promise.resolve({outcome: 'dismissed'})});
  assert.equal(prompts, 0, 'never prompt without the user clicking');
  assert.equal(button.hidden, false);
  await button.onclick(); await button.onclick();
  assert.equal(prompts, 1, 'install prompt is consumed once');
  assert.equal(help.hidden, false, 'dismissal keeps manual instructions');
  events.appinstalled();
  assert.equal(help.hidden, true);
  assert.equal(button.hidden, true);
  console.log('PWA installation: explicit click, dismissal and installed state passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
