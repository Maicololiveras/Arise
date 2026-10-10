"""Adapt verified Gentle TUI panels to native RPC dialogs, preserving its logic."""
import hashlib
import json
import re
from pathlib import Path

PROFILES = '''
    if (process.env.ARISE_URL) {
        const actions = ["Aplicar perfil", "Crear perfil", "Guardar sesión en perfil", "Duplicar perfil", "Renombrar perfil", "Eliminar perfil", "Exportar perfil", "Importar perfil", ...ARISE_PIN_ACTIONS, "Cerrar"];
        const selected = await ctx.ui.select("Perfiles de Gentle · sesión actual", actions);
        if (!selected || selected === "Cerrar") return {type:"close"};
        const types = ["apply","create","update","duplicate","rename","delete","export","import"];
        const type = types[actions.indexOf(selected)];
        if (type === "create" || type === "import") return {type} as ProfilesPanelResult;
        const name = await ctx.ui.select("Elegir perfil", Object.keys(file.profiles));
        if (selected.startsWith("Fijar perfil")) return name ? {type:"pin", name, source:selected.includes("repositorio") ? "repo" : "local"} as ProfilesPanelResult : {type:"close"};
        return name ? {type,name} as ProfilesPanelResult : {type:"close"};
    }
'''

PALETTE = '''
    if (process.env.ARISE_URL) {
        const commands = pi.getCommands().filter(c => c.name.startsWith("gentle:"));
        const options = commands.map(c => "/" + c.name);
        const selected = await ctx.ui.select("Comandos de Gentle · sesión actual", ["Cerrar", ...options]);
        if (selected && selected !== "Cerrar") pi.sendUserMessage(selected, {expandPromptTemplates:true});
        return;
    }
'''
CHANGES = '''
    if (process.env.ARISE_URL) {
        await deps.refresh();
        const entries = deps.worktrees().flatMap(tree => tree.model.files.map(file => ({root:tree.root, file})));
        const labels = entries.map((entry, index) => `${index+1}. ${entry.file.path} (${entry.file.status})`);
        const selected = await ctx.ui.select("Cambios capturados en la sesión", ["Cerrar", ...labels]);
        if (selected && selected !== "Cerrar") {
            const entry = entries[labels.indexOf(selected)];
            ctx.ui.notify(entry.file.path + "\\n" + deps.loadDiff(entry.root, entry.file), "info");
        }
        return;
    }
'''
AGENTS = '''
        if (process.env.ARISE_URL) {
            const tasks = store.list(ctx.sessionManager.getSessionId() ?? "");
            const labels = tasks.map((task,index) => `${index+1}. ${task.agent ?? task.id} · ${task.status}`);
            const selected = await ctx.ui.select("Agentes de Gentle · sesión actual", ["Cerrar", ...labels]);
            if (selected && selected !== "Cerrar") {
                const task = tasks[labels.indexOf(selected)];
                const thread = store.thread(task.id);
                ctx.ui.notify(JSON.stringify({task, thread:{...thread,items:thread.items.filter(item => item.kind !== "thinking")}}, null, 2), "info");
                if (isOwnedActive(task) && await ctx.ui.confirm("Detener agente", "¿Detener este agente y conservar su historial?")) await stopSelected(task,ctx);
            }
            return;
        }
'''
HISTORY = '''
    if (process.env.ARISE_URL) {
        const labels = records.map((record,index) => `${index+1}. ${record.text.slice(0,160).replaceAll("\\n", " ")}`);
        const selected = await ctx.ui.select("Historial de instrucciones", ["Cerrar", ...labels]);
        return selected && selected !== "Cerrar" ? records[labels.indexOf(selected)] : null;
    }
'''
STATS = '''
        if (process.env.ARISE_URL) {
            const range = await ctx.ui.select("Estadísticas de Gentle", ["Cerrar", "7d", "30d", "all"]);
            if (!range || range === "Cerrar") return;
            const scope = await ctx.ui.select("Alcance de estadísticas", ["project", "all"]);
            if (!scope) return;
            const sessions = await loader.load(sessionsRoots());
            const summary = aggregateStats(sessions, {range:range as any,scope:scope as any,cwd:ctx.sessionManager.getCwd(),now:now()});
            const current = currentSessionStats(ctx.sessionManager.getEntries(), {sessionId:ctx.sessionManager.getSessionId() ?? "",now:now()});
            ctx.ui.notify(JSON.stringify({summary,current},null,2), "info");
            return;
        }
'''
USAGE = '''async (ctx: ExtensionContext) => {
        if (process.env.ARISE_URL) {
            await refreshUsage(ctx, true);
            ctx.ui.notify(JSON.stringify({providers:usageScope,usage:usage.all(),unavailable:[...usageFailures.keys()]},null,2), "info");
            return;
        }
        return '''
MODELS = '''
    if (process.env.ARISE_URL) {
        const draft = cloneModelConfig(config);
        const agents = modelAssignmentNames(ctx.cwd);
        const models = (await getPiModelOptions(ctx)).filter(id => id.includes("/"));
        while (true) {
            const agent = await ctx.ui.select("Modelos de Gentle · sesión actual", ["Guardar", "Cancelar", "Todos los agentes", ...agents]);
            if (!agent || agent === "Cancelar") return {type:"cancel"};
            if (agent === "Guardar") return {type:"save",config:draft};
            const model = await ctx.ui.select("Elegir modelo", ["Heredar", "Modelo personalizado", ...models]);
            if (!model) continue;
            let id = model === "Modelo personalizado" ? await ctx.ui.input("Modelo (proveedor/modelo)") : model;
            if (!id) continue;
            if (id !== "Heredar" && !normalizeModelId(id)) {ctx.ui.notify("Modelo inválido", "warning");continue;}
            const thinking = await ctx.ui.select("Esfuerzo", ["Heredar", "off", "minimal", "low", "medium", "high", "xhigh"]);
            if (!thinking) continue;
            for (const name of agent === "Todos los agentes" ? agents : [agent]) {
                const entry = {...(draft[name] || {})};
                if (id === "Heredar") delete entry.model; else entry.model = id;
                if (thinking === "Heredar") delete entry.thinking; else entry.thinking = thinking;
                draft[name] = entry;
            }
        }
    }
'''

def extension_for_rpc(gentle, cache, source=None):
    gentle=Path(gentle).resolve();source=Path(source or gentle/'extensions/gentle-ai.ts')
    package=json.loads((gentle/'package.json').read_text(encoding='utf-8'))
    if package.get('name')!='gentle-pi' or package.get('version') not in ('3.3.0', '4.0.0'):return source
    original=source.read_text(encoding='utf-8');text=original;patterns=[]
    if source.name == 'gentle-ai.ts':
        profiles = PROFILES.replace('ARISE_PIN_ACTIONS', '["Fijar perfil en este clon", "Fijar perfil en el repositorio"]' if package['version']=='4.0.0' else '[]')
        patterns=[(r'(async function showProfilesPanel\([\s\S]*?\): Promise<ProfilesPanelResult> \{)',profiles),
                  (r'(async function showSddModelPanel\([\s\S]*?\): Promise<ModelPanelResult> \{)',MODELS)]
    elif package['version'] == '4.0.0' and source.name == 'gentle-shell.ts':
        patterns=[(r'(async function showCommandPalette\([^\n]+\): Promise<void> \{)',PALETTE),
                  (r'(async function showChangesOverlay\([^\n]+\): Promise<void> \{)',CHANGES)]
        text,count=re.subn(r'const openUsage = \(ctx: ExtensionContext\) =>', 'const openUsage = '+USAGE, text, count=1)
        if count != 1: raise RuntimeError('El panel de uso de Gentle cambió; revisa el adaptador.')
        text,count=re.subn(r'(\n\tpi.registerCommand\(USAGE_COMMAND_NAME,)', '\n\t};\\1', text, count=1)
        if count != 1: raise RuntimeError('No se pudo adaptar el panel de uso de Gentle.')
    elif package['version'] == '4.0.0' and source.name in ('gentle-agents.ts','gentle-stats.ts'):
        patterns=[(r'(const openOverlay = async \(ctx: ExtensionContext\) => \{)', AGENTS if source.name=='gentle-agents.ts' else STATS)]
        if source.name=='gentle-stats.ts': text=text.replace('createStatsLoader, currentSessionStats,', 'aggregateStats, createStatsLoader, currentSessionStats,')
    elif package['version'] == '4.0.0' and source.name == 'index.ts' and source.parent.name == 'history':
        patterns=[(r'(async function runPromptHistorySelection\([\s\S]*?\): Promise<PromptRecord \| null> \{)', HISTORY)]
    else: return source
    for pattern,body in patterns:
        text,count=re.subn(pattern,lambda match:match.group(1)+body,text,count=1)
        if count!=1:raise RuntimeError('La versión de Gentle no coincide con el adaptador de paneles nativos')
    # Resolve original assets and relative modules without modifying the installed package.
    text=re.sub(r'from\s+(["\'])(\.\.?/[^"\']+)\1',lambda match:'from '+json.dumps(str((source.parent/match.group(2)).resolve()).replace('\\','/')),text)
    text=text.replace('import.meta.url',json.dumps(source.as_uri()))
    digest=hashlib.sha256(text.encode()).hexdigest()[:20]
    target=Path(cache)/'gentle-rpc';target.mkdir(parents=True,exist_ok=True)
    path=target/f'{source.stem}-{digest}.ts'
    if not path.is_file():path.write_text(text,encoding='utf-8')
    return path
