// Install the verified package-local native helper without modifying Pi settings.
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
const folder = resolve(process.argv[2]);
const {installGentleAi} = await import(pathToFileURL(resolve(folder,'scripts/gentle-ai-installer.mjs')).href);
const result = await installGentleAi();
console.log(JSON.stringify(result));
