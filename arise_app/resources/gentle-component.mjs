// Render a Gentle component through the current Pi RPC session. Its own
// handlers still own navigation, confirmations and the value returned to Pi.
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { join } from 'node:path';
import { randomUUID } from 'node:crypto';

export function componentHost(ctx, root) {
  if (ctx.mode !== 'rpc' || !process.env.ARISE_URL) return ctx.ui.custom.bind(ctx.ui);
  return async factory => {
    const require = createRequire(join(root, 'package.json'));
    const { getKeybindings } = await import(pathToFileURL(require.resolve('@earendil-works/pi-tui')).href);
    const id = randomUUID();
    let view, result, closed = false, pending = false, frame = '';
    const abort = new AbortController();
    const repaint = () => {
      if (!view || closed || pending) return;
      pending = true;
      queueMicrotask(() => {
        pending = false;
        if (closed) return;
        frame = view.render(82).slice(0, 80).join('\n').slice(0, 64000);
        ctx.ui.setWidget('arise-component:' + id, [frame]);
      });
    };
    const tui = {terminal: {columns: 82, rows: 28}, requestRender: repaint};
    const finish = value => { result = value; closed = true; abort.abort(); };
    try {
      view = await factory(tui, ctx.ui.theme, getKeybindings(), finish);
      if ('focused' in view) view.focused = true;
      while (!closed) {
        frame = view.render(82).slice(0, 80).join('\n').slice(0, 64000);
        const key = await ctx.ui.input('arise-component:' + id, frame, {signal: abort.signal});
        if (closed || key === undefined) break;
        await view.handleInput?.(key);
      }
      return result;
    } finally {
      closed = true;
      view?.dispose?.();
      ctx.ui.setWidget('arise-component:' + id, []);
    }
  };
}
