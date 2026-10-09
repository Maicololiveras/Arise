import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from arise_app.processes import McpClient
root=Path(sys.argv[1]).resolve()/'bundle'
manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8-sig'))
report=[]
for name,spec in manifest.get('mcp',{}).items():
 command=[str(root/value[8:]) if value.startswith('@bundle/') else value for value in spec['command']]
 client=McpClient(command,cwd=str(root))
 try:
  if not client.tools:raise RuntimeError(name+' has an empty MCP catalog')
  report.append({'server':name,'tools':len(client.tools),'initialize':'passed','executed_device_actions':False})
 finally:client.close()
Path('artifacts').mkdir(exist_ok=True)
Path('artifacts/bundled-mcp.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
