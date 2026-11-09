# Gentle commands in ARISE

The integrated runtime pins Gentle Shell 4.7.0 and Pi 1.5.0. ARISE discovers
commands from the actual session rather than claiming support from a static
list. Unknown slash commands are rejected instead of being sent to the model.

| Command family | Native interaction |
| --- | --- |
| Profiles/models | Upstream selections, edit/save/cancel and scope rules |
| Commands | Searchable palette of registered commands |
| Agents | Public task history and explicit cancellation of owned work |
| Stats/usage | Available upstream measurements; errors remain visible |
| Changes | Session-tracked files and diffs, without attributing external changes |
| Status/doctor | Project state and diagnostics |
| Persona/review/telemetry/install | Upstream handlers and permissions |
| History | Restore an instruction into the draft without sending |
| Customize | Open ARISE settings; no implied YOLO permission |
| TUI appearance/Vim | Retain terminal-specific scope, not the Qt editor/orb |

RPC select/input/confirm/editor prompts use native dialogs. Long content scrolls
while response buttons remain reachable. Adapters retain upstream validation;
unsupported forks are not silently rewritten as compatible packages. Agent
views exclude private reasoning. Model selection does not change voice providers.

Gentle profiles retain their upstream global/repository scope. ARISE session
preferences and local-execution authorization are per chat. Command registration
is not proof of provider access, installed native helpers or successful operation.

Integration tests exercise real Pi/Gentle with a local fixture provider: resume,
profiles/models, command discovery, dialogs, delegation and cancellation. They do
not authorize destructive commands against real user projects.
