import { spawn } from "node:child_process";

import { StringDecoder } from "node:string_decoder";
import { fileURLToPath } from "node:url";
import { PARAKEET_MODEL_MANIFEST, VOICE_TARGETS, voiceRuntimeManifest,                                                                      } from "./voice-artifacts.mjs";
import { readVoiceComponentStatus, resolveVoiceHome, voiceComponentPath } from "./voice-install.mjs";

// One dictation session (S1-S3): record from the default microphone until stop,
// then transcribe locally with the installed Parakeet model. Capture, the
// blocking model load and the decode all run in scripts/voice-worker.cjs, a
// separate Node process, so nothing native is ever loaded into Gentle AI.
// Importing this module or constructing a session does no IO; only start()
// reads the install and spawns the worker. The transcript is returned to the
// caller and never submitted or inserted anywhere by this module.

export const VOICE_WORKER_SCHEMA = "gentle.voice/v1";
export const VOICE_WORKER_URL = new URL("../scripts/voice-worker.cjs", import.meta.url);

export const VOICE_SESSION_DEFAULTS = {
	// The worker stops capturing by itself at this length and transcribes.
	maxRecordingMs: 120_000,
	// Covers the runtime checks and opening the microphone.
	startTimeoutMs: 120_000,
	// Covers what is left of the model digest check (~670 MB, verified while
	// recording), loading the recognizer and the decode.
	transcribeTimeoutMs: 120_000,
	// How long a stopping or cancelled worker may take to exit before it is killed.
	exitGraceMs: 2_000,
	numThreads: 2,
}         ;

const MAX_LINE = 64 * 1024;
const MAX_LINES = 16;
const MAX_TEXT = 16 * 1024;
const RECORDING_MARGIN_MS = 10_000;

const WORKER_ERROR_CODES = [
	"invalid-request",
	"node-version",
	"runtime-invalid",
	"model-invalid",
	"runtime-load",
	"model-load",
	"no-input-device",
	"unsupported-input",
	"capture",
	"empty-audio",
	"decode",
	"internal",
]         ;





// Fixed text only: no path, environment value or native error ever reaches it.
const MESSAGES                                        = {
	"invalid-state": "This voice session cannot do that in its current state.",
	unsupported: "Voice dictation has no pinned runtime for this platform.",
	"node-version": "Voice dictation needs Node 22 or newer.",
	"not-installed": "The voice runtime and model are not installed or cannot be read.",
	"invalid-request": "The voice worker rejected its request.",
	"runtime-invalid": "The installed voice runtime failed verification. Reinstall it.",
	"model-invalid": "The installed voice model failed verification. Reinstall it.",
	"runtime-load": "The voice runtime could not be loaded on this system.",
	"model-load": "The voice model could not be loaded.",
	"no-input-device": "No microphone was found.",
	"unsupported-input": "The default microphone uses an unsupported audio format.",
	capture: "Microphone capture failed.",
	"empty-audio": "No audio was recorded.",
	"no-speech": "No speech was recognized.",
	decode: "Transcription failed.",
	internal: "The voice worker failed.",
	timeout: "The voice session took too long and was stopped.",
	protocol: "The voice worker sent an invalid response and was stopped.",
	"worker-exited": "The voice worker stopped unexpectedly.",
	cancelled: "Voice dictation was cancelled.",
};

export class VoiceSessionError extends Error {
	         code                       ;

	constructor(code                       ) {
		super(MESSAGES[code]);
		this.name = "VoiceSessionError";
		this.code = code;
	}
}














































const hasExactKeys = (value                         , keys          ) => Object.keys(value).length === keys.length && keys.every((key) => Object.hasOwn(value, key));

// Accepts only the four known messages with exactly their fields.
function parseWorkerLine(line        )                            {
	let value         ;
	try {
		value = JSON.parse(line);
	} catch {
		return undefined;
	}
	if (typeof value !== "object" || value === null || Array.isArray(value)) return undefined;
	const record = value                           ;
	if (record.schema !== VOICE_WORKER_SCHEMA) return undefined;
	switch (record.type) {
		case "recording":
		case "transcribing":
			return hasExactKeys(record, ["schema", "type"]) ? { type: record.type } : undefined;
		case "result":
			if (!hasExactKeys(record, ["schema", "type", "text", "truncated"]) || typeof record.text !== "string" || record.text.length > MAX_TEXT || typeof record.truncated !== "boolean") return undefined;
			return { type: "result", text: record.text, truncated: record.truncated };
		case "error":
			if (!hasExactKeys(record, ["schema", "type", "code"]) || !WORKER_ERROR_CODES.includes(record.code                   )) return undefined;
			return { type: "error", code: record.code                    };
		default:
			return undefined;
	}
}

// The child environment is an allowlist: home, temp, locale and the audio
// session variables survive; credentials, NODE_OPTIONS, NODE_PATH, loader
// overrides and PATH are dropped.
const CHILD_ENV_KEYS = ["HOME", "USERPROFILE", "SystemRoot", "SYSTEMROOT", "windir", "TEMP", "TMP", "TMPDIR", "XDG_RUNTIME_DIR", "PULSE_SERVER", "PULSE_COOKIE", "LANG", "LC_ALL", "LC_CTYPE"];

function childEnv(source                   )                    {
	const env                    = {};
	for (const key of CHILD_ENV_KEYS) if (source[key] !== undefined) env[key] = source[key];
	env.NODE_NO_WARNINGS = "1";
	env.GENTLE_PI_AGENTS_CHILD = "1";
	return env;
}

function defaultSpawn(executable        , args          , options                         )                   {
	// SAFETY: ChildProcess provides stdin/stdout/stderr/kill/once compatible with the narrower VoiceWorkerChild; the cast only bridges that narrowing.
	return spawn(executable, args, { ...options, stdio: ["pipe", "pipe", "pipe"] })                               ;
}







function deferred   ()              {
	let resolve                     ;
	let reject                           ;
	const promise = new Promise   ((res, rej) => {
		resolve = res;
		reject = rej;
	});
	return { promise, resolve, reject };
}

const fail = (code                       ) => new VoiceSessionError(code);

function unref(handle                               )                                {
	(handle                          ).unref?.();
	return handle;
}

// Single use: idle -> starting -> recording -> transcribing -> finished. A
// successful start() resolves while the worker keeps recording; stop(),
// cancel() and a failed start() settle only after the worker process has
// closed, so a finished session never leaves a child behind.
export class VoiceSession {
	                 options                     ;
	        currentState                    = "idle";
	        child                              ;
	        outcome                                                                            ;
	                 recording = deferred      ();
	                 closed = deferred      ();
	        timer                                           ;
	        exitTimer                                           ;

	constructor(options                     ) {
		this.options = { ...options };
		// Settled by close; a session that never starts never awaits it.
		this.closed.promise.catch(() => {});
	}

	get state()                    {
		return this.currentState;
	}

	// Resolves once the microphone is recording.
	async start()                {
		if (this.currentState !== "idle") throw fail("invalid-state");
		this.setState("starting");
		let launch                                                    ;
		try {
			launch = await this.prepare();
		} catch (error) {
			this.outcome ??= { error: error instanceof VoiceSessionError ? error : fail("not-installed") };
			this.setState("finished");
			throw this.outcomeError();
		}
		if (this.outcome) throw this.outcomeError();
		this.launch(launch.root, launch.request);
		const exited = this.closed.promise.then(() => {
			throw this.outcomeError();
		});
		exited.catch(() => {});
		await Promise.race([this.recording.promise, exited]);
	}

	// Ends recording and resolves with the transcript, or rejects with
	// "empty-audio" or "no-speech" when nothing usable was said.
	async stop()                           {
		if (this.currentState === "idle" || this.currentState === "starting") throw fail("invalid-state");
		if (this.currentState === "recording" && !this.outcome) {
			this.send({ schema: VOICE_WORKER_SCHEMA, type: "stop" });
			this.enterTranscribing();
		}
		// A finished session answers with its outcome, such as a transcript the
		// recording limit produced before stop() was called.
		if (this.child) await this.closed.promise;
		if (this.outcome && "transcript" in this.outcome) return this.outcome.transcript;
		throw this.outcomeError();
	}

	// Discards the session: any transcript, including one that arrives late, is
	// dropped. Resolves after the worker has exited.
	async cancel()                {
		if (!this.child) {
			if (this.currentState !== "finished") {
				this.outcome ??= { error: fail("cancelled") };
				this.setState("finished");
			}
			return;
		}
		this.outcome = { error: fail("cancelled") };
		this.send({ schema: VOICE_WORKER_SCHEMA, type: "cancel" });
		this.endWorker(this.options.exitGraceMs ?? VOICE_SESSION_DEFAULTS.exitGraceMs);
		await this.closed.promise;
	}

	dispose()                {
		return this.cancel();
	}

	        setState(state                   )       {
		if (this.currentState === state) return;
		this.currentState = state;
		this.options.onStateChange?.(state);
	}

	        outcomeError()                    {
		return this.outcome && "error" in this.outcome ? this.outcome.error : fail("worker-exited");
	}

	        async prepare()                                                              {
		const { target } = this.options;
		if (!VOICE_TARGETS.includes(target)) throw fail("unsupported");
		if (Number((this.options.nodeVersion ?? process.versions.node).split(".")[0]) < 22) throw fail("node-version");
		const model = this.options.manifests?.model ?? PARAKEET_MODEL_MANIFEST;
		const runtime = this.options.manifests?.runtime ?? voiceRuntimeManifest(target);
		if (runtime.target !== target) throw fail("unsupported");
		const voiceHome = this.options.voiceHome ?? resolveVoiceHome(this.options.env);
		const statuses = await Promise.all([
			readVoiceComponentStatus({ voiceHome, kind: "runtime", manifest: runtime }),
			readVoiceComponentStatus({ voiceHome, kind: "model", manifest: model }),
		]);
		if (statuses.some((status) => status.state !== "installed")) throw fail("not-installed");
		const pick = (prefix        ) => {
			const file = model.files.find((candidate) => candidate.name.startsWith(prefix));
			if (!file) throw fail("model-invalid");
			return { name: file.name, size: file.size, sha256: file.sha256 };
		};
		const root = voiceComponentPath(voiceHome, "runtime", runtime);
		const request = {
			schema: VOICE_WORKER_SCHEMA,
			type: "start",
			target,
			maxRecordingMs: this.options.maxRecordingMs ?? VOICE_SESSION_DEFAULTS.maxRecordingMs,
			numThreads: VOICE_SESSION_DEFAULTS.numThreads,
			runtime: { root, files: runtime.packages.flatMap((pkg) => pkg.requiredFiles.map((file) => `node_modules/${pkg.name}/${file}`)) },
			model: {
				root: voiceComponentPath(voiceHome, "model", model),
				files: { encoder: pick("encoder."), decoder: pick("decoder."), joiner: pick("joiner."), tokens: pick("tokens.") },
			},
		};
		return { root, request };
	}

	        launch(root        , request                         )       {
		const workerPath = this.options.workerPath ?? fileURLToPath(VOICE_WORKER_URL);
		// The worker runs from the runtime directory, never the user's project.
		const child = (this.options.spawn ?? defaultSpawn)(process.execPath, [workerPath], {
			cwd: root,
			shell: false,
			windowsHide: true,
			detached: false,
			stdio: ["pipe", "pipe", "pipe"],
			env: childEnv(this.options.env ?? process.env),
		});
		this.child = child;
		let buffered = "";
		let lines = 0;
		// Pipe chunks can end inside a multibyte character; the decoder holds the
		// partial bytes until the rest arrives.
		const decoder = new StringDecoder("utf8");
		const onStdout = (chunk         ) => {
			buffered += typeof chunk === "string" ? chunk : decoder.write(chunk          );
			let newline        ;
			while ((newline = buffered.indexOf("\n")) !== -1) {
				const line = buffered.slice(0, newline);
				buffered = buffered.slice(newline + 1);
				const message = ++lines <= MAX_LINES && line.length <= MAX_LINE ? parseWorkerLine(line) : undefined;
				if (message) this.onMessage(message);
				else this.abort("protocol");
			}
			if (buffered.length > MAX_LINE) this.abort("protocol");
		};
		// stderr is drained so the worker never blocks on it, and then dropped:
		// native libraries may print paths or device names there.
		const onStderr = () => {};
		child.stdout?.on("data", onStdout);
		child.stderr?.on("data", onStderr);
		child.stdin?.on("error", () => {});
		child.once("error", () => {
			/* Node emits close after spawn errors; keep waiting */
		});
		child.once("close", () => {
			child.stdout?.removeListener("data", onStdout);
			child.stderr?.removeListener("data", onStderr);
			this.clearTimers();
			this.outcome ??= { error: fail("worker-exited") };
			this.child = undefined;
			this.setState("finished");
			this.closed.resolve();
		});
		this.send(request);
		this.arm(this.options.startTimeoutMs ?? VOICE_SESSION_DEFAULTS.startTimeoutMs);
	}

	        onMessage(message               )       {
		if (this.outcome) return;
		switch (message.type) {
			case "recording":
				if (this.currentState !== "starting") return this.abort("protocol");
				this.setState("recording");
				this.arm((this.options.maxRecordingMs ?? VOICE_SESSION_DEFAULTS.maxRecordingMs) + RECORDING_MARGIN_MS);
				this.recording.resolve();
				return;
			case "transcribing":
				// Sent after stop(), or on its own when the recording limit is reached.
				if (this.currentState === "recording") this.enterTranscribing();
				else if (this.currentState !== "transcribing") this.abort("protocol");
				return;
			case "result":
				if (this.currentState !== "transcribing") return this.abort("protocol");
				this.outcome = message.text.trim() ? { transcript: { text: message.text.trim(), truncated: message.truncated } } : { error: fail("no-speech") };
				this.endWorker(this.options.exitGraceMs ?? VOICE_SESSION_DEFAULTS.exitGraceMs);
				return;
			case "error":
				this.outcome = { error: fail(message.code) };
				this.endWorker(this.options.exitGraceMs ?? VOICE_SESSION_DEFAULTS.exitGraceMs);
		}
	}

	        enterTranscribing()       {
		this.setState("transcribing");
		this.arm(this.options.transcribeTimeoutMs ?? VOICE_SESSION_DEFAULTS.transcribeTimeoutMs);
	}

	// Records a failure and kills the worker at once.
	        abort(code                       )       {
		if (this.outcome) return;
		this.outcome = { error: fail(code) };
		this.kill();
	}

	// The worker exits by itself after its final message or a cancel; it is
	// killed only if it is still running after the grace period.
	        endWorker(graceMs        )       {
		this.clearTimers();
		this.child?.stdin?.end();
		this.exitTimer = unref(setTimeout(() => this.kill(), graceMs));
	}

	        arm(ms        )       {
		if (this.timer) clearTimeout(this.timer);
		this.timer = unref(
			setTimeout(() => {
				this.outcome = { error: fail("timeout") };
				this.kill();
			}, ms),
		);
	}

	        clearTimers()       {
		if (this.timer) clearTimeout(this.timer);
		if (this.exitTimer) clearTimeout(this.exitTimer);
		this.timer = this.exitTimer = undefined;
	}

	        kill()       {
		this.clearTimers();
		try {
			this.child?.kill("SIGKILL");
		} catch {
			// close still follows; keep waiting for it.
		}
	}

	        send(message                         )       {
		try {
			this.child?.stdin?.write(`${JSON.stringify(message)}\n`);
		} catch {
			// A worker that cannot be written to is gone; close settles the session.
		}
	}
}

export function createVoiceSession(options                     )               {
	return new VoiceSession(options);
}
