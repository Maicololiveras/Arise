// Pinned upstream extension; translate its TUI entry point to RPC dialogs.
import {createRequire} from 'node:module';
import {join} from 'node:path';
const root = process.env.ARISE_AGY_ROOT;
export default async function antigravity(pi) {
  if (!root) return;
  const require = createRequire(join(root, '../../@earendil-works/pi-coding-agent/package.json'));
  const {createJiti} = require('jiti');
  const jiti = createJiti(import.meta.url, {fsCache: false});
  const {default: upstream} = await jiti.import(join(root, 'src/entry.ts'));
  const adapter = new Proxy(pi, {
    get(target, property) {
      if (property === 'registerCommand') return (name, command) => {
        if (name !== 'agy') return target.registerCommand(name, command);
        target.registerCommand(name, {...command, handler: async (args, ctx) => {
          if ((args || '').trim()) return command.handler(args, ctx);
          const choices = ['doctor', 'auth', 'quota', 'auth-manual'];
          const choice = await ctx.ui.select('Antigravity', choices);
          if (choices.includes(choice)) return command.handler(choice, ctx);
        }});
      };
      const value = Reflect.get(target, property);
      return typeof value === 'function' ? value.bind(target) : value;
    },
  });
  await upstream(adapter);
  // Native agy tools do not necessarily pass through Pi's tool_call hook.
  // Recheck chat authority before each turn, including screenshot study turns.
  pi.on('before_agent_start', async () => {
    process.env.AGY_READONLY = 'true';
    if (process.env.ARISE_CODE_ENABLED !== '1' || !process.env.ARISE_URL) return;
    try {
      const response = await fetch(new URL('/api/status', process.env.ARISE_URL), {
        headers: {Authorization: `Bearer ${process.env.ARISE_TOKEN}`, "X-Arise-Conversation": process.env.ARISE_CONVERSATION || "", "X-Arise-Session": process.env.ARISE_SESSION_EPOCH || ""},
        signal: AbortSignal.timeout(5000),
      });
      if (!response.ok) return;
      const status = await response.json();
      if (status.capabilities?.local_execution_authorized && !status.study_read_only)
        process.env.AGY_READONLY = 'false';
    } catch { /* permission uncertainty refuses provider turns */ }
  });
}
