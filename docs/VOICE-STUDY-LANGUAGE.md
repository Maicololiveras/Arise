# Voice controls, study assistance and interface language

Implementation: **0.4.42 QA**. Public downloads are listed in the generated release tables. Verified QA builds publish to Preview and update its feed on main; Stable application code and its feed are unchanged.

## Voice controls

ARISE must already be listening, or be activated with a configured wake phrase. These exact commands accept an optional `Ari` or `ARISE` prefix and punctuation. They do not depend on a local model deciding which tool to call.

| Intent | Spanish | English | Effect |
| --- | --- | --- | --- |
| Interrupt speech | `Deja de hablar` | `Stop speaking` | Interrupt playback; retain the task and listening session. |
| End voice | `Deja de escuchar` | `Stop listening` | End the voice conversation and mute the microphone, including wake listening. Tasks continue. |
| Cancel work | `Cancela la tarea` | `Cancel task` | Cancel work and revoke hands/eyes. |
| Exit ARISE | `Ari, apágate` | `Ari, shut down` | Mute voice, stop work, close the renderer and resident process. This does not shut down the PC. |
| Open study setup | `Modo estudio` | `Study mode` | Open visible study options and consent; do not start capture automatically. |
| Study lifecycle | `Pausa el estudio`, `Reanuda el estudio`, `Termina el estudio` | `Pause study`, `Resume study`, `End study` | Control the current chat's study session. |

The chat panel has a separate **End voice conversation** button. **Start voice conversation** explicitly unmutes the microphone. The existing global Stop remains independent. Draft dictation still writes into the input for review; it does not execute spoken controls.

Local controls bypass the dialogue worker queue. Cloud voice controls depend on completed provider transcripts; Gemini fragments are collected until completion. Recognition quality, speaker echo and provider transcription latency still require physical acceptance. A phrase embedded in a longer task request is not treated as a control.

## Study and quiz assistance

1. Share the relevant material in the current chat and connect ScreenView in Tools.
2. Open **Study / quiz mode** from the chat menu, or ask by voice to open it.
3. Add a topic/reference summary, choose 10–300 seconds (default 30), and explicitly allow periodic screen observation.
4. Start the session. The application takes one still screenshot, clears its overlays using the existing desktop handshake, and asks the selected model to explain the visible question and reasoning using the current chat's material.
5. After the answer, the panel is shown again. The next interval begins after the previous turn finishes. Busy tasks are not overlapped.
6. Use **Pause**, **Resume** or **Finish** in the visible study strip. Global Stop, switching chats or closing ARISE ends the scheduler. A capture already in progress may finish, but its result cannot start another model turn after cancellation.

Study model turns cannot call ARISE tools, shell commands or delegated agents. The host supplies the screenshot and the Pi tool-call guard rejects tool execution during those turns. ARISE does not click or submit answers, manipulate monitoring software, or guarantee an assessment result. Use assistance only where permitted.

Screenshots are sent to the selected chat model and saved as chat attachments. Share only a screen appropriate for that provider. No hidden background study session survives a restart. Native Core builds require a separately configured compatible ScreenView server.

## Live language switching

Select **Español / English** at the top of Settings. Existing ARISE controls, settings tabs, menu labels, standard dialogs, tooltips and accessible labels update immediately. The preference is saved separately from other unsubmitted settings. New dialogs use the same language.

Drafts, history messages, file paths, credentials, model IDs and externally supplied agent choices are not translated or rewritten. Raw provider/tool diagnostics remain verbatim for troubleshooting. The next model turn receives the selected response-language instruction; changing language does not interrupt a running task. New voice sessions use the selected language instruction. Whisper transcription follows the selected language; the bundled Spanish Vosk wake/recognition model remains Spanish. Gonzalo remains a Colombian Spanish voice; changing interface language does not silently replace the selected voice or install an English speech model.

The phone web app also has an **Español / English** button. It initially follows the PC's setting after pairing, unless the browser has its own saved language preference. Only that preference is stored locally; chat and pairing secrets are not cached.

## Guided phone setup

Connections → Phone now guides Android, iPhone and iPad through Tailscale, authenticator enrollment, private connection preparation and home-screen installation. **Check phone setup readiness** reads PC status without modifying Serve, enrolling accounts, or claiming to verify the phone remotely.

Tailscale sign-in on both devices, provider MFA and the authenticator confirmation remain user actions. ARISE preserves existing network services and never enables public Funnel as a shortcut. See the README installation steps for each phone platform.

## Acceptance still required

- Physical microphones/speakers: interrupt a long reply, end listening, restart voice and exit ARISE.
- Real desktop: capture without overlays, read the answer, pause during capture, switch chats and confirm no further capture.
- iPhone/iPad Safari and Android Chrome: pair, install, switch languages, dictate, stop and revoke.
- Real cloud voice accounts: finalized transcripts, provider errors and interrupted replies.
- README demonstration video: pending a supplied recording. VPS/Coolify and native store publication remain deferred.
