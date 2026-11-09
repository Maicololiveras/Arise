# Native accounts, fluent voice and desktop layout (QA 0.4.37)

## Connect an account without a terminal

Open **Settings > Agent > Connect account and choose model**. Select a provider
and its supported authentication method. ARISE uses Pi 1.5's native ModelRuntime
and Gentle's NaN registration, following Gentle Dot's account integration.
OAuth opens the provider's HTTPS page in the default browser; device codes,
manual callbacks and provider choices remain in the account dialog. API keys
are entered in a masked field. Select an available chat model after login.

Credentials are written by the SDK to the selected engine's `auth.json` using
its native storage format. Bundled mode uses ARISE's private agent directory.
ARISE does not copy global credentials automatically, place tokens in command
arguments, or emit account responses into chat/tool events. This storage is not
an additional encrypted vault. Environment-based credentials must be removed
at their source. Logout removes the provider's stored SDK credential.

Account routes require the native renderer's separate capability, not only the
agent bridge token. Login blocks new model connections and configuration
changes. Stop running tasks before changing accounts. Cancel/close terminates
the private helper; account windows expire after ten minutes. The dialog body
scrolls while its cancel/close controls remain reachable.

Chat subscription authentication and paid realtime voice credentials are
separate. Connecting ChatGPT does not supply an OpenAI API voice key.

## Gonzalo and fluent playback

The package includes the synthesis adapter, not a downloadable Gonzalo voice
model. `es-CO-GonzaloNeural` still requires Microsoft's online speech service.
Microsoft Embedded Speech distributes voice/model assets through its approved
access program; no public redistributable Gonzalo model is included here.
See [Embedded Speech](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/embedded-speech).

The pinned adapter is `msedge-tts` 2.1.1. It uses bounded connection/synthesis
timeouts, system certificate authorities and the configured HTTP/HTTPS proxy.
ARISE never disables TLS certificate verification. Proxy auto-configuration
scripts and interactive proxy authentication are not implemented.

Fluent playback splits the completed reply at sentence/word boundaries, starts
with a short chunk, and prepares one following chunk while playing the current
one. It is not live token streaming and does not promise a fixed latency.
Temporary audio is removed after playback. Cancellation stops synthesis,
conversion and queued audio. Failure after playback starts never repeats the
entire reply using another voice.

Settings provides an output-only voice test (no microphone or model request).
On Windows, an enabled fallback uses an installed system voice if Gonzalo fails
before playback. A visible notice explains the change; this is not Gonzalo and
uses the Windows default output. Disable fallback to require Gonzalo exclusively.

## Voice activation

Enable local wake listening explicitly in Voice settings and install the Vosk
activation model. Configure one to ten activation phrases, whether activation
opens the chat, and the local spoken acknowledgement. Listening remains off by
default. The daemon can listen while the renderer is running in the tray; a
closed renderer is not automatically launched by this change. Speech output
still requires working audio devices and a configured synthesis provider.

## Clear the desktop before tools act

By default, ScreenView/InputControl and desktop Forge calls ask the native UI
to hide the chat and dock the orb in the configured corner (bottom-right by
default). The orb is hidden during the individual operation, then reappears.
The tool waits for a private renderer acknowledgement before proceeding; a
missing acknowledgement fails the operation instead of capturing the overlay.
Headless operation does not wait for a renderer. Stop/status and speech-only
calls do not clear the desktop.

The orb can still be dragged. Automatic docking does not overwrite the saved
preferred position; a deliberate drag does. The chat remains hidden until the
user opens it. This does not grant desktop permissions or change approval rules.

## Validation and limits

Automated checks cover native SDK key storage/logout/model listing, simulated
OAuth interactions, private account-route authorization, scrollable account UI,
output-only playback, proxy/TLS error redaction, ordered speech preparation,
partial-playback failure, wake preferences and overlay acknowledgement ordering.
A real online Gonzalo request produced nonempty audio in the development
environment. Real account login, audible playback, hotword accuracy and physical
Windows desktop repaint timing still require QA on the target PC.
