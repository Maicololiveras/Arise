# Managed tool updates

Packaged Windows ARISE checks its managed tools at startup, including the first launch after an application update. ScreenView, InputControl and Forge use the public manifests on the `herramientas` branch. A changed release tag or SHA-256 triggers an update even when the semantic version is unchanged. Transcription compares the private repository's default-branch commit when GitHub access is already configured; it does not request new credentials automatically.

Each enabled component is handled independently:

1. Identify the active ARISE-owned runtime and read its installation metadata.
2. Compare it with the validated published manifest or private source commit.
3. Download into a new runtime directory. Public packages require the expected origin, size, SHA-256 and safe ZIP contents.
4. Save the new runtime's provenance, close the old MCP process and select the new command.
5. Require a nonempty MCP tool catalog. If activation fails, close the new process and restore the previous configuration. The previous files remain available for reconnection.

The next startup reads the new active runtime's metadata and skips an unchanged package. The aggregate `tools/installed.json` marker is informational, not the source of version decisions.

Disabled tools and working custom MCP commands outside ARISE's managed runtime directories are left alone. A missing or invalid provenance record is reported rather than guessed; use Settings → Tools → Download / repair for that component. Missing enabled tools still use the existing installation flow.

An active task, screen-control session or voice session defers the automatic pass until a subsequent startup. Offline checks, unpublished packages and failed updates preserve the previous configuration and do not prevent other components from being checked. `ARISE_SKIP_NETWORK_SETUP` continues to suppress automatic startup network setup.

This updates tool distributions already published by their repositories. Merging an ARISE update does not itself publish a pending InputControl fix. Custom MCPs, Gentle Shell, Engram and model downloads have separate installation/update mechanisms and are outside this MCP update pass. Public tools currently share the `herramientas` distribution across ARISE app channels.

Catalog verification confirms MCP startup, not the success of every desktop operation. InputControl still requires its visible safety indicator before granting control; an automatic update never starts a control session or grants additional permissions.

## Tests

```sh
python -m pytest tests/test_tool_updates.py tests/test_tool_setup.py tests/test_selective_downloads.py tests/test_downloads.py tests/test_updates.py -q
```
