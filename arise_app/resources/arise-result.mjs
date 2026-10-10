// Observe the official runner's result. Never change its plan, consent or channel.
import { readFile, writeFile, rename } from 'node:fs/promises';
import { join } from 'node:path';
import { homedir } from 'node:os';
import { pathToFileURL } from 'node:url';
import { createProbes } from '../scripts/installer-probes.mjs';

export async function reportToArise(result, channel, context) {
  const destination = new URL('../arise-result.json', import.meta.url);
  let report = {status:'failed', reason:result.failedStep || result.reason || result.outcome};
  if (['ready','terminal-action-required'].includes(result.outcome)) {
    try {
      const probes = createProbes(context);
      const shell = await probes.locateShell();
      const pi = await probes.locatePi();
      if (!shell?.root || !pi?.root) throw new Error('Missing package roots');
      const launcher = await import(pathToFileURL(join(shell.root,'runtime/gentle-shell-launcher.mjs')).href);
      let config;
      try {config=launcher.parseLauncherConfig(await readFile(launcher.launcherConfigPath(homedir()),'utf8'));}
      catch (error) {if(error.code!=='ENOENT') throw error;}
      const home=launcher.resolveHome({args:{link:false,isolated:false,home:undefined},env:context.env,homedir:homedir(),config});
      report={status:'ready',channel:channel==='main'?'main':'release',pi_root:pi.root,gentle_root:shell.root,agent_home:home.dir,version:shell.version};
    } catch { report={status:'failed',reason:'No se pudo localizar la instalación terminada.'}; }
  }
  const temporary=new URL('../arise-result.tmp',import.meta.url);
  await writeFile(temporary,JSON.stringify(report),'utf8');
  await rename(temporary,destination);
}
