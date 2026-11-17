# Assistant evolution: responsiveness, tools and voice

## Implemented in this revision

The owned engine pins Gentle Shell 4.8.0, Pi 1.5.2, Gentle AI 4.5.0,
Engram 3.7.2 and gentle-engram 0.8.0. Installer archives retain their
platform-specific SHA-256 validation. The 4.7 registry backport is not applied
to 4.8. Git must be available to verify automatic registry writes; an unknown Git state is not treated as permission to overwrite. Installed extensions retain their own tool definitions and permissions.

The bundled `pi-web-access` 0.48.0 package is registered in the private agent
home, alongside memory. It provides web search and page extraction. Provider
availability, credentials, rate limits and connectivity still apply. Search
queries go to the selected search provider; do not send confidential documents
without authorization. Results are untrusted evidence, not instructions.

A submitted chat message is stored and displayed before cold engine startup.
Startup failure leaves the user's message visible with the error; it does not
silently resubmit it. This removes a UI delay, not model inference latency.
The live process continues to be reused for subsequent turns.

Whisper transcription now has a separate `speech_language` setting: `auto`,
`es`, `en` or `pt`. Auto passes `None` to the recognizer for language detection.
It does not switch the installed Vosk model: Vosk wake recognition and the light
voice profile remain constrained by that model's vocabulary. The Parakeet chat
dictation path is separate and unchanged.

Wake matching accepts punctuation and accents and, only after configured
`oye/hey/hola/ok arise` greetings, common recognizer variants `a raíz`, `arais`
and `araiz`. Bare “a raíz…” does not activate the assistant. The remaining
request preserves its spelling and capitalization. These aliases are text
matching improvements, not proof of acoustic recognition quality.

## JARVIS as a product reference

JARVIS is a fictional integrated assistant, not a published implementation or
performance specification. The useful design target is continuous context,
short spoken responses, interruption, tool execution and clear status.
Translate that inspiration into measurable behavior:

| Behavior | Verification |
| --- | --- |
| Immediate acknowledgement | User message visible before a cold-start handshake |
| Useful tools | Real engine exposes search, file and authorized shell tools |
| Context continuity | Restore the same chat and memory; never mix other chats |
| Interruptibility | Stop cancels the current task and audio independently |
| Voice robustness | Recorded Spanish/English/Portuguese corpus, including names and negative wake examples |
| Low latency | Measure input-to-display, engine-ready, first-token and first-audio separately; report cold/warm p50 and p95 |

The next acoustic validation requires recordings from real microphones. Do not
claim perfect recognition, a measured speedup or a target latency based only on
unit tests. Do not globally rewrite “a raíz” in user documents or dictation.

## Sources reviewed

- [Gentle Shell 4.8.0 release](https://github.com/Gentleman-Programming/gentle-shell/releases/tag/v4.8.0): desktop RPC, tool/context changes and pinned runtime.
- [Pi Web Access](https://www.npmjs.com/package/pi-web-access): installed 0.48.0 README and package metadata.
- [Whisper transcription](https://github.com/openai/whisper/blob/main/whisper/transcribe.py): automatic language detection.
- [Faster Whisper transcription](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py): language selection and vocabulary hints.
- [J.A.R.V.I.S. overview](https://en.wikipedia.org/wiki/J.A.R.V.I.S.): fictional reference, not an engineering source.
