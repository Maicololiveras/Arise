import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renameWithRetry } from './install-gentle-native.mjs';
test('Windows transient lock retries the same atomic rename', async () => {
  const calls = []; let attempts = 0;
  await renameWithRetry('staging', 'live', { platform: 'win32', pause: async () => {}, operation: async (...paths) => {
    calls.push(paths); if (++attempts < 3) throw Object.assign(new Error('locked'), {code:'EPERM'});
  }});
  assert.deepEqual(calls, Array(3).fill(['staging', 'live']));
});
test('Permanent lock is bounded and unrelated errors fail immediately', async () => {
  for (const [platform, code, expected] of [['win32','EPERM',8],['win32','ENOENT',1],['linux','EPERM',1]]) {
    let attempts = 0; const failure = Object.assign(new Error('failure'), {code});
    await assert.rejects(renameWithRetry('a','b',{platform,pause:async()=>{},operation:async()=>{attempts++;throw failure;}}), error=>error===failure);
    assert.equal(attempts, expected);
  }
});
