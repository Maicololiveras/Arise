# Antigravity in ARISE

ARISE 0.4.44 includes `@3d24rd0/pi-antigravity-bridge` 1.3.1 as a pinned dependency. The integration is disabled by default and uses ARISE's owned runtime; installing Gentle Shell globally is unnecessary.

## Connect from Settings

1. Open **Settings → Agent → Connect to Antigravity**. This enables the integration and saves the settings.
2. The bridge prepares Google's ACP server if needed (approximately 1.5 GB) and starts its own Google sign-in. Complete the browser flow. ARISE surfaces the bridge's sign-in instructions in its chat notifications.
3. Select **Connect and list models**, choose an `antigravity` model, and save.
4. Authorize local execution for this chat before requesting provider turns. This authorization does not remove individual tool approval dialogs.

Google account access and server availability are prerequisites. The bundled extension does not bundle Google's ACP server or an authenticated Google session. A completed command submission is not proof of successful sign-in. `/agy doctor` provides upstream diagnostics; `/agy` opens an RPC-compatible menu for diagnostics, authentication, quota and manual instructions.

The separate generic **Connect account** dialog lists Pi account providers; Antigravity authenticates through its own server and the dedicated button above. CLI-suffixed models additionally require Google's `agy` CLI. Existing external credentials are not copied into ARISE's private home.

## Authority and lifecycle

The adapter forces upstream approval gating and disables permission skipping. It refuses provider turns when local execution is disabled, while study mode is read-only, or when current chat authority cannot be verified. Independent `AskAntigravity` and upstream web delegation tools are disabled in this integration. Ordinary ARISE tools retain their permission checks.

Disabling the checkbox and saving disconnects Pi. The next session does not load the bridge; downloaded server files and sign-in state remain in the owned home. Nothing uninstalls or modifies a global Gentle Shell installation. ARISE's Stop and session shutdown remain the lifecycle controls.

## Verification limits

Automated tests load the actual pinned upstream extension using a synthetic Pi surface and isolated temporary home, verify provider registration and the RPC menu, and exercise denied, authorized, study and unavailable-permission states. They do not start Google's server, authenticate an account or claim live model access. A real Google sign-in, model response, tool approval/rejection and cancellation still require user acceptance on each target platform.

Upstream: https://github.com/3d24rd0/antigravity-bridge
