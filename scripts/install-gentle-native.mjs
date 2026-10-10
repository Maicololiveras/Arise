// Preserve the official verified, atomic installer; retry Windows file locks only.
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
import { rename } from 'node:fs/promises';
import { setTimeout as delay } from 'node:timers/promises';
export async function renameWithRetry(from, to, options = {}) {
  const operation = options.operation ?? rename;
  const pause = options.pause ?? delay;
  const platform = options.platform ?? process.platform;
  for (let attempt = 0; ; attempt++) {
    try { return await operation(from, to); }
    catch (error) {
      if (platform !== 'win32' || !['EPERM', 'EACCES', 'EBUSY'].includes(error.code) || attempt >= 7) throw error;
      await pause(250 * (attempt + 1));
    }
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const folder = resolve(process.argv[2]);
  const { installGentleAi } = await import(pathToFileURL(resolve(folder, 'scripts/gentle-ai-installer.mjs')).href);
  const result = await installGentleAi({ rename: renameWithRetry });
  console.log(JSON.stringify(result));
}
