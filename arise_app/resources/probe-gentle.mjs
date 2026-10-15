// Read installed package metadata; never start Pi or copy authentication files.
import {readFileSync, realpathSync, statSync, existsSync} from 'node:fs';
import {join, dirname, resolve, relative, isAbsolute} from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {homedir} from 'node:os';
let root = realpathSync(process.argv[2]);
let managedNode, bundleRoot, managedVersion;
if (process.argv.includes('--bundle')) {
  bundleRoot = root;
  if (readFileSync(join(root,'.gentle-shell-bundle'),'utf8').trim() !== 'gentle-shell bundled install') throw Error('Invalid managed marker');
  const managed = await import(pathToFileURL(process.argv[process.argv.indexOf('--bundle')+1]).href);
  const layout = managed.prefixLayout({platform:process.platform,env:process.env,home:homedir(),root});
  const id = managed.activeVersion(layout);
  if (!id || id.includes('..')) throw Error('No active managed version');
  const version = realpathSync(join(layout.versions,id));
  managedVersion = version;
  const inside = (base, target) => {const rel=relative(realpathSync(base),realpathSync(target)); if(rel.startsWith('..') || isAbsolute(rel)) throw Error('Managed path escapes prefix');};
  inside(root,version);
  if (readFileSync(join(version,'.gentle-shell-version'),'utf8') !== `${id}\n`) throw Error('Incomplete managed version');
  root = realpathSync(join(version,'node_modules/gentle-pi'));
  inside(version,root);
  managedNode = realpathSync(layout.node);
  inside(bundleRoot,managedNode);
  if (!statSync(managedNode).isFile()) throw Error('Missing managed Node');
  const prepared = {...managed.setupEnvironment(layout,{env:process.env,id})};
  for (const key of Object.keys(process.env)) delete process.env[key];
  Object.assign(process.env,prepared);
}
const read = p => JSON.parse(readFileSync(p, 'utf8').replace(/^\uFEFF/, ''));
const shell = read(join(root, 'package.json'));
if (!['gentle-pi','gentle-shell'].includes(shell.name)) throw Error('Not Gentle');
if (process.env.GENTLE_SHELL_PI) throw Error('Explicit GENTLE_SHELL_PI override requires manual configuration');
const require = createRequire(join(root,'bin/gentle-shell.mjs'));
const name = '@earendil-works/pi-coding-agent';
let pi;
for (const base of require.resolve.paths(name) || []) {
  const candidate = join(base,name);
  if (existsSync(join(candidate,'package.json'))) { pi = realpathSync(candidate); break; }
}
// The linked launcher falls back to Pi on PATH when it has no adjacent Pi.
if (!pi && process.argv.includes('--link') && process.argv.includes('--pi-cli')) {
  const fallback=realpathSync(process.argv[process.argv.indexOf('--pi-cli')+1]);
  let parent=dirname(fallback);
  for(let depth=0;depth<4;depth++,parent=dirname(parent)) {
    if (!existsSync(join(parent,'package.json'))) continue;
    const candidate=read(join(parent,'package.json'));
    if(candidate.name===name && typeof candidate.bin?.pi==='string' && realpathSync(join(parent,candidate.bin.pi))===fallback) {pi=parent;break;}
  }
}
if (!pi) throw Error('No verified Pi runtime for this Gentle installation');
if (bundleRoot) {
  const rel=relative(managedVersion,pi);
  if(rel.startsWith('..') || isAbsolute(rel)) throw Error('Pi outside managed versions');
}
const meta = read(join(pi,'package.json'));
if (meta.name !== name || typeof meta.bin?.pi !== 'string') throw Error('Invalid Pi metadata');
const cli = realpathSync(join(pi,meta.bin.pi));
const rel = relative(pi,cli);
if (rel.startsWith('..') || isAbsolute(rel) || !statSync(cli).isFile()) throw Error('Invalid Pi CLI');
const launcher = await import(pathToFileURL(join(root,'runtime/gentle-shell-launcher.mjs')).href);
let config;
try { config = launcher.parseLauncherConfig(readFileSync(launcher.launcherConfigPath(homedir()),'utf8')); }
catch(e) { if(e.code !== 'ENOENT') throw e; }
const home = resolve(launcher.resolveHome({args:{link:process.argv.includes('--link'),isolated:false},env:process.env,homedir:homedir(),config}).dir);
if (!statSync(home).isDirectory() || !existsSync(join(home,'settings.json'))) throw Error('Run Gentle first to provision its home');
// Apply Gentle's own integrity/development-override policy; never skip verification.
const native = await import(pathToFileURL(join(root,'runtime/gentle-ai-binary.mjs')).href);
native.resolveGentleAiBinary(root);
console.log(JSON.stringify({node:managedNode,bundle_root:bundleRoot,status:'ready', channel:shell.version.includes('-main.')?'main':'release', pi_root:pi,gentle_root:root,agent_home:home,version:shell.version}));
