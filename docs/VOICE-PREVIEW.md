# Desktop and voice Preview 0.4.48
The current chat shows a bounded plain-text tail while Pi generates. On completion the canonical Markdown reply appears once in history. Desktop RPC discovery runs only when the extension advertises its command. Runtime capabilities report confirmed methods and the initial snapshot sequence. The adapter does not write permissions or profiles.

In Settings → Voice conversation enable the features independently:
- Add up to 240 characters of project vocabulary for local Whisper or faster-whisper. Vosk does not support this option. Select Spanish for Spanish-only conversations.
- Enable conservative wake-name normalization to turn “oye a raíz” into “oye ARISE”. Ordinary uses of “a raíz” stay intact. No LLM guesses names or numbers. A correction event retains the original and corrected words.
- Enable sentence playback to hear complete sentences from Gentle before a local voice reply finishes. Gonzalo and the existing interruption controls remain available. Partial text is never executed as an instruction.
- Enable private server transcription only after configuring the host below. It sends completed microphone turns, not continuous audio, and falls back to the existing local recognizer on failure. Manual draft dictation remains local.

## Private speech on Coolify
1. Create a Docker Compose resource using [the CPU template](../deploy/speaches/compose.yaml). Set a unique SPEACHES_API_KEY secret. Pin SPEACHES_IMAGE to a tested digest before production.
2. Route a private HTTPS hostname to container port 8000 and restrict access to your private network. The first startup downloads the multilingual small model into a persistent volume.
3. On the ARISE host, set ARISE_STT_URL to the full HTTPS URL ending in /v1/audio/transcriptions and ARISE_STT_TOKEN to the same secret. Restart the resident host to inherit these variables. Enable the private server checkbox only on devices authorized to send audio.
4. Test a short Spanish phrase, then disconnect the server and repeat. Verify local fallback and a single submitted turn. Compare stage timings, recognition errors, false triggers and time to first speech before promoting.

This is an opt-in integration, not a hosted service. No VPS provisioning or live microphone benchmark is implied. Cross-chat scheduling, reminders and JARVIS task supervision remain future work.
