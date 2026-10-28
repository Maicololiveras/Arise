import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const root=resolve(process.argv[2]);
const {resolveGentleAiBinary}=await import(pathToFileURL(resolve(root,'runtime/gentle-ai-binary.mjs')).href);
console.log(JSON.stringify({path:resolveGentleAiBinary(root)}));
