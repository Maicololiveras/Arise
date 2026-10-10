// Read installed package metadata; never start Pi or copy authentication files.
import {readFileSync, realpathSync, statSync, existsSync} from 'node:fs';
import {join, dirname, resolve, relative, isAbsolute} from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {homedir} from 'node:os';
const root = realpathSync(process.argv[2]);
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
if (!pi) throw Error('No adjacent Pi; refusing unrelated global fallback');
const meta = read(join(pi,'package.json'));
if (meta.name !== name || typeof meta.bin?.pi !== 'string') throw Error('Invalid Pi metadata');
const cli = realpathSync(join(pi,meta.bin.pi));
const rel = relative(pi,cli);
if (rel.startsWith('..') || isAbsolute(rel) || !statSync(cli).isFile()) throw Error('Invalid Pi CLI');
const launcher = await import(pathToFileURL(join(root,'runtime/gentle-shell-launcher.mjs')).href);
let config;
try { config = launcher.parseLauncherConfig(readFileSync(launcher.launcherConfigPath(homedir()),'utf8')); }
catch(e) { if(e.code !== 'ENOENT') throw e; }
const home = resolve(launcher.resolveHome({args:{link:false,isolated:false},env:process.env,homedir:homedir(),config}).dir);
if (!statSync(home).isDirectory() || !existsSync(join(home,'settings.json'))) throw Error('Run Gentle first to provision its home');
console.log(JSON.stringify({status:'ready', channel:shell.version.includes('-main.')?'main':'release', pi_root:pi,gentle_root:root,agent_home:home,version:shell.version}));
