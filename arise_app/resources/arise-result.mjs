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
      let shell, pi, node, bundleRoot;
      if (context.request?.plan?.bundled) {
        const managed = await import('../scripts/bundled-install.mjs');
        bundleRoot = context.request.plan.bundled.root;
        const layout = managed.prefixLayout({platform:context.platform, env:context.env, home:homedir(), root:bundleRoot});
        const id = managed.activeVersion(layout);
        if (!id) throw new Error('Missing active version');
        const modules = join(layout.versions,id,'node_modules');
        shell = {root:join(modules,'gentle-pi')};
        shell.version=JSON.parse(await readFile(join(shell.root,'package.json'),'utf8')).version;
        pi = {root:join(modules,'@earendil-works/pi-coding-agent')};
        node=layout.node;
      } else {
        shell = await probes.locateShell();
        pi = await probes.locatePi();
        // A pnpm adjacent Pi is the runtime the installed launcher actually runs.
        if (shell?.root) {
          const { createRequire } = await import('node:module');
          const require=createRequire(join(shell.root,'package.json'));
          for (const base of require.resolve.paths('@earendil-works/pi-coding-agent') || []) {
            const candidate=join(base,'@earendil-works/pi-coding-agent');
            try {
              const metadata=JSON.parse(await readFile(join(candidate,'package.json'),'utf8'));
              if (metadata.name==='@earendil-works/pi-coding-agent') {pi={root:candidate};break;}
            } catch (error) {if(error.code!=='ENOENT') throw error;}
          }
        }
      }
      if (!shell?.root || !pi?.root) throw new Error('Missing package roots');
      const launcher = await import(pathToFileURL(join(shell.root,'runtime/gentle-shell-launcher.mjs')).href);
      let config;
      try {config=launcher.parseLauncherConfig(await readFile(launcher.launcherConfigPath(homedir()),'utf8'));}
      catch (error) {if(error.code!=='ENOENT') throw error;}
      const home=launcher.resolveHome({args:{link:false,isolated:false,home:undefined},env:context.env,homedir:homedir(),config});
      report={node,bundle_root:bundleRoot,status:'ready',channel:channel==='main'?'main':'release',pi_root:pi.root,gentle_root:shell.root,agent_home:home.dir,version:shell.version};
    } catch { report={status:'failed',reason:'No se pudo localizar la instalación terminada.'}; }
  }
  const temporary=new URL('../arise-result.tmp',import.meta.url);
  await writeFile(temporary,JSON.stringify(report),'utf8');
  await rename(temporary,destination);
}


export function withAriseReport(handlers, context) {
  let channel='release';
  return {
    ...handlers,
    collectPlan: async (selected) => { channel=selected; return handlers.collectPlan(selected); },
    runInstall: async (request, log) => {
      const result=await handlers.runInstall(request,log);
      await reportToArise(result,channel,{...context,...handlers.ariseContext?.(),request});
      return result;
    },
  };
}
