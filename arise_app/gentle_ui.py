"""Adapt Gentle 3.3 custom TUI panels to native RPC dialogs, preserving its logic."""
import hashlib
import json
import re
from pathlib import Path

PROFILES = '''
    if (process.env.ARISE_URL) {
        const actions = ["Aplicar perfil", "Crear perfil", "Guardar sesión en perfil", "Duplicar perfil", "Renombrar perfil", "Eliminar perfil", "Exportar perfil", "Importar perfil", "Cerrar"];
        const selected = await ctx.ui.select("Perfiles de Gentle · sesión actual", actions);
        if (!selected || selected === "Cerrar") return {type:"close"};
        const types = ["apply","create","update","duplicate","rename","delete","export","import"];
        const type = types[actions.indexOf(selected)];
        if (type === "create" || type === "import") return {type} as ProfilesPanelResult;
        const name = await ctx.ui.select("Elegir perfil", Object.keys(file.profiles));
        return name ? {type,name} as ProfilesPanelResult : {type:"close"};
    }
'''
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

def extension_for_rpc(gentle, cache):
    gentle=Path(gentle).resolve();source=gentle/'extensions/gentle-ai.ts'
    package=json.loads((gentle/'package.json').read_text(encoding='utf-8'))
    if package.get('name')!='gentle-pi' or package.get('version')!='3.3.0':return source
    original=source.read_text(encoding='utf-8');text=original
    patterns=[(r'(async function showProfilesPanel\([\s\S]*?\): Promise<ProfilesPanelResult> \{)',PROFILES),
              (r'(async function showSddModelPanel\([\s\S]*?\): Promise<ModelPanelResult> \{)',MODELS)]
    for pattern,body in patterns:
        text,count=re.subn(pattern,lambda match:match.group(1)+body,text,count=1)
        if count!=1:raise RuntimeError('La versión de Gentle no coincide con el adaptador de paneles nativos')
    # Resolve original assets and relative modules without modifying the installed package.
    text=re.sub(r'from\s+(["\'])(\.\.?/[^"\']+)\1',lambda match:'from '+json.dumps(str((source.parent/match.group(2)).resolve()).replace('\\','/')),text)
    text=text.replace('import.meta.url',json.dumps(source.as_uri()))
    digest=hashlib.sha256(text.encode()).hexdigest()[:20]
    target=Path(cache)/'gentle-rpc';target.mkdir(parents=True,exist_ok=True)
    path=target/f'gentle-ai-{digest}.ts'
    if not path.is_file():path.write_text(text,encoding='utf-8')
    return path
