#!/usr/bin/env node
// Keep Pi in this process so stopping ARISE never leaves a detached engine.
import { pathToFileURL, fileURLToPath } from 'node:url';
import { resolve, join } from 'node:path';
import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
const [cli, ...args] = process.argv.slice(2);
if (!cli) throw new Error('gentle-shell requires the configured Pi CLI path');
const shared = process.env.ARISE_MEMORY_MODE === 'shared';
let piArgs = [resolve(cli), ...args];
const bridgeExtension = process.env.ARISE_AGY_ROOT ? fileURLToPath(new URL('./antigravity.mjs', import.meta.url)) : null;
const root = process.env.ARISE_GENTLE_ROOT;
const home = process.env.ARISE_GENTLE_HOME;
if (root && home && process.env.ARISE_GENTLE_PREFIX) {
  const managed = await import(pathToFileURL(join(root,'scripts/bundled-install.mjs')).href);
  const layout = managed.prefixLayout({platform:process.platform, env:process.env, home:homedir(), root:process.env.ARISE_GENTLE_PREFIX});
  const id = managed.activeVersion(layout);
  if (!id) throw new Error('Gentle no tiene una versión activa; repara su instalación.');
  const managedEnv=managed.setupEnvironment(layout, {env:process.env, id});
  for (const key of Object.keys(process.env)) { if (!(key in managedEnv)) delete process.env[key]; }
  Object.assign(process.env, managedEnv);
}
if (root && home) {
  // Use the installed Gentle launch rules and its configured home. Let Pi
  // load existing packages once instead of injecting a second Gentle copy.
  const launcher = await import(pathToFileURL(join(root,'runtime/gentle-shell-launcher.mjs')).href);
  let settings = '{}';
  try { settings = readFileSync(join(home,'settings.json'),'utf8'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  const declaration = launcher.findGentlePiDeclaration(settings, {
    agentDir: home,
    readPackageName(dir) {
      try { return JSON.parse(readFileSync(join(dir,'package.json'),'utf8')).name; }
      catch { return undefined; }
    },
  });
  // Preserve 4.3's isolated config home only when the configured agent home
  // actually matches the official launcher selection. Linked/custom homes
  // retain upstream's shared-config rules.
  let launcherConfig;
  try { launcherConfig = launcher.parseLauncherConfig(readFileSync(launcher.launcherConfigPath(homedir()),'utf8')); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  const selectedHome = launcher.resolveHome({args:{link:false,isolated:false},env:process.env,homedir:homedir(),config:launcherConfig});
  const homeSelection = resolve(selectedHome.dir) === resolve(home)
    ? selectedHome : {mode:'path',dir:home,source:'config'};
  const invocation = launcher.buildPiInvocation({
    runtime:{command:process.execPath,args:[resolve(cli)]},
    home:homeSelection, bundled:!!process.env.ARISE_GENTLE_PREFIX, packageRoot:root,
    declaration,takeOver:false,otherPackagePaths:[],looseExtensionEntries:[],
    passthrough:args,baseEnv:process.env,homedir:homedir(),cwd:process.cwd(),
  });
  piArgs = invocation.args;
  if (process.env.ARISE_GENTLE_OWNED === '1') {
    const injection = await import(pathToFileURL(join(root, 'runtime/child-package-injection.mjs')).href);
    const rpcExtensions = process.env.ARISE_GENTLE_RPC_EXTENSIONS;
    if (!rpcExtensions) {
      // Interactive login/delegated terminals use upstream's complete package.
      piArgs.push('--extension', root);
    }
    invocation.env[injection.CHILD_PACKAGE_INJECTION_ENV] = injection.encodeChildPackageInjection({
      noExtensions: false, extensionPaths: [...(rpcExtensions ? JSON.parse(rpcExtensions) : [root]), ...(bridgeExtension ? [bridgeExtension] : [])],
    });
  }
  for (const key of Object.keys(process.env)) {
    if (!(key in invocation.env)) delete process.env[key];
  }
  Object.assign(process.env,invocation.env);
}
if (shared) {
  const {sharedMemory} = await import('./shared-memory.mjs');
  const notify = state => { if (args.includes('--mode') && args.includes('rpc')) process.stdout.write(JSON.stringify({type:'arise_memory_status',state})+'\n'); };
  const connection = await sharedMemory(root, process.env, notify);
  connection.install();
}
if (bridgeExtension) piArgs.push("--extension", bridgeExtension);
process.argv = [process.execPath, ...piArgs];
await import(pathToFileURL(resolve(cli)).href);
