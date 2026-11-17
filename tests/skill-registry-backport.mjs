import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {join,resolve} from 'node:path';
import {mkdtemp,mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {execFileSync} from 'node:child_process';
const packageRoot=resolve(process.argv[2]);
const require=createRequire(join(packageRoot,'../@earendil-works/pi-coding-agent/package.json'));
const {createJiti}=require('jiti');
const registry=await createJiti(import.meta.url,{fsCache:false}).import(join(packageRoot,'extensions/skill-registry.ts'));
const root=await mkdtemp(join(tmpdir(),'arise-registry-'));
const previous=process.env.PATH;
try {
  // A real repository protects tracked registry bytes, even on forced automatic regeneration.
  execFileSync('git',['init',root]);
  await mkdir(join(root,'.atl'));
  await writeFile(join(root,'.atl/skill-registry.md'),'user-owned registry\n');
  execFileSync('git',['add','.atl/skill-registry.md'],{cwd:root});
  assert.match(await registry.automaticWriteWarning(root,['.atl/skill-registry.md']),/tracked targets/);
  await registry.__testing.regenerateRegistry(root,true);
  assert.equal(await readFile(join(root,'.atl/skill-registry.md'),'utf8'),'user-owned registry\n');
  // Missing Git may never turn a repository into permission to overwrite.
  process.env.PATH='';
  await assert.rejects(registry.automaticWriteWarning(root,['.atl/skill-registry.md']),/Cannot verify Git/);
  const child=join(root,'nested');await mkdir(child);
  await assert.rejects(registry.automaticWriteWarning(child,['.atl/skill-registry.md']),/Cannot verify Git/);
  // Upstream 4.8 requires working Git to positively verify a non-Git workspace.
  await rm(join(root,'.git'),{recursive:true,force:true});
  await assert.rejects(registry.automaticWriteWarning(root,['.atl/skill-registry.md']),/Cannot verify Git/);
  process.env.PATH=previous;
  assert.equal(await registry.automaticWriteWarning(root,['.atl/skill-registry.md']),undefined);
  const skills=join(root,'.agents/skills/demo');await mkdir(skills,{recursive:true});
  await writeFile(join(skills,'SKILL.md'),'---\nname: demo\ndescription: Synthetic local skill\n---\nTest only.\n');
  await registry.__testing.regenerateRegistry(root,true);
  const first=await readFile(join(root,'.atl/skill-registry.md'),'utf8');
  assert.match(first,/demo/);
  const second=await registry.__testing.regenerateRegistry(root,true);
  assert.equal(await readFile(join(root,'.atl/skill-registry.md'),'utf8'),first);
  assert.equal(second.regenerated,false);
  console.log('Registry backport: tracked protection, missing Git, ancestor metadata, disk-only idempotence passed');
} finally {process.env.PATH=previous;registry.__testing.closeSkillRegistryWatchers();await rm(root,{recursive:true,force:true});}
