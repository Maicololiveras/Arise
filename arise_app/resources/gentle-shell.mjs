#!/usr/bin/env node
// Keep Pi in this process so stopping ARISE never leaves a detached engine.
import { pathToFileURL } from 'node:url';
import { resolve, join } from 'node:path';
import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
const [cli, ...args] = process.argv.slice(2);
if (!cli) throw new Error('gentle-shell requires the configured Pi CLI path');
let piArgs = [resolve(cli), ...args];
const root = process.env.ARISE_GENTLE_ROOT;
const home = process.env.ARISE_GENTLE_HOME;
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
  const invocation = launcher.buildPiInvocation({
    runtime:{command:process.execPath,args:[resolve(cli)]},
    home:{mode:'path',dir:home,source:'config'}, packageRoot:root,
    declaration,takeOver:false,otherPackagePaths:[],looseExtensionEntries:[],
    passthrough:args,baseEnv:process.env,homedir:homedir(),cwd:process.cwd(),
  });
  piArgs = invocation.args;
  for (const key of Object.keys(process.env)) {
    if (!(key in invocation.env)) delete process.env[key];
  }
  Object.assign(process.env,invocation.env);
}
process.argv = [process.execPath, ...piArgs];
await import(pathToFileURL(resolve(cli)).href);
