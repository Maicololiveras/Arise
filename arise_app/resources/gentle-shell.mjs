#!/usr/bin/env node
// ARISE's invisible Gentle Shell entry point. Run Pi in this same process so
// suspend/stop never leaves a detached child. Runtime supplies Gentle extensions.
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
const [cli, ...args] = process.argv.slice(2);
if (!cli) throw new Error('gentle-shell requires the configured Pi CLI path');
process.argv = [process.execPath, resolve(cli), ...args];
await import(pathToFileURL(resolve(cli)).href);
