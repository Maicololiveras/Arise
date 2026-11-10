const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const parent = ignored => ({id:'',closest: selector => ignored && selector !== 'button,[data-ui-label]' ? {} : null});
const label = {nodeValue:'Detener',parentElement:parent(false)};
const message = {nodeValue:'Detener',parentElement:parent(true)};
const input = {placeholder:'Código del autenticador',value:'private-code'};
const button = {};
let observerCallback; const writes=[];
const document = {
  body:{},documentElement:{},title:'',getElementById:()=>button,
  createTreeWalker:()=>{let i=0;return {nextNode:()=>[label,message][i++]||null};},
  querySelectorAll:()=>[input]
};
const context={document,NodeFilter:{SHOW_TEXT:4},MutationObserver:class {constructor(fn){observerCallback=fn;}observe(){}disconnect(){}},
  localStorage:{getItem:()=>null,setItem:(...args)=>writes.push(args)},window:{}};
vm.runInNewContext(fs.readFileSync('arise_app/resources/companion-language.js','utf8'),context);
context.window.ariseLanguage.defaultLanguage('en');
assert.equal(label.nodeValue,'Stop');assert.equal(message.nodeValue,'Detener');assert.equal(input.value,'private-code');
assert.equal(input.placeholder,'Authenticator code');assert.equal(writes.length,0);
button.onclick();assert.equal(label.nodeValue,'Detener');assert.equal(document.documentElement.lang,'es');
context.window.ariseLanguage.defaultLanguage('en');assert.equal(document.documentElement.lang,'es','local choice wins');
button.onclick();label.nodeValue='Hablar';observerCallback();assert.equal(label.nodeValue,'Speak');
assert.deepEqual(writes.map(w=>w[0]),['arise-ui-language','arise-ui-language']);
console.log('Live phone language preserves message bodies, drafts and credentials.');
