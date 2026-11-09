# Android companion QA: wake phrase and overlay

Status: implementation on `qa-connections-companion`, not main. This is a separate
Android APK, not part of the Windows installer. No iPad background listener is
implemented. Target device: Xiaomi Redmi 13C; its Android/MIUI/HyperOS version has
not yet been provided or tested.

## What is implemented

- Native Android app (minimum Android 8, target Android 15), permission setup,
  microphone foreground service and a persistent notification with Stop.
- Explicit special-access prompt for **Display over other apps**, followed by
  `Settings.canDrawOverlays` verification. Granting it does not start recording.
- Microphone and notification permission prompts, followed by an explicit
  **Activate listening** action while the activity is visible. Revocation stops
  listening; restoration does not restart it. No boot receiver or sticky service.
- A configurable Porcupine detector running locally. A detection opens a compact
  bottom panel and orb. Expand uses 85% of screen height; compact uses 48%; the
  message document scrolls internally. Hide preserves the panel/draft and the
  detector, while Mic OFF destroys the panel and closes the microphone.
- Screen-off hides the panel. Wake callbacks do not show messages while locked.
  The panel uses FLAG_SECURE to exclude it from screenshots/recents capture.
- The existing restricted companion web UI inside a WebView: one-use pairing,
  chat-scoped HttpOnly cookie, renewal, history, sending and PC stop. No native
  JavaScript bridge, foreign navigation, file/content URLs, third-party cookies,
  cleartext traffic, ignored TLS errors or web microphone permission.
- Origin is constrained to an exact HTTPS Tailscale `.ts.net` host. Tailscale on
  both devices and the PC's private Serve endpoint remain prerequisites.
- Wake detection only opens the conversation. It does not authorize PC actions,
  send a command, grant hands/eyes, or change the selected chat. Use the keyboard
  (including its dictation) to compose; continuous post-wake voice conversation
  is not implemented in this APK.

## Detector provisioning — required, not bundled

This implementation uses `ai.picovoice:porcupine-android:4.0.2` behind the native
service. It does **not** include a trained `oye ARISE` model or a shared key.
Porcupine requires a Picovoice AccessKey and a custom keyword model. Licensing,
usage limits and possible license validation are separate from ARISE. No account,
subscription or purchase is created automatically. Do not claim this SDK is a
fully open-source, account-free wake engine. No fallback phrase or cloud speech
recognizer is substituted if setup fails.

1. In Picovoice Console, generate **oye ARISE**, language **Spanish**, platform
   **Android**, with a model version compatible with the pinned SDK.
2. Export the `.ppn` keyword and matching Spanish `.pv` language model.
3. In ARISE Companion QA, enter the AccessKey (encrypted with Android Keystore)
   and import both files using the system file picker. Imports are size limited
   to 32 MiB and copied into app-private storage; external filenames are not used.
4. Grant overlay, microphone and notifications, then explicitly activate.
5. If model/key/permissions fail, show the failure and keep listening off.

Recognition accuracy, pronunciation, battery use and successful key activation
remain unverified until these actual assets and a device are available. The
native setup can be installed/tested and manual chat used without a detector key.
The Android orb vector reuses the palette and ring geometry of `assets/icon.svg`;
the application label explicitly identifies it as QA.

## Pairing and use

1. On PC: ARISE settings > Connections > Mobile, start the restricted endpoint
   using the exact HTTPS Tailscale origin and follow the displayed Serve command.
2. On phone: connect Tailscale to the authorized tailnet; enter that origin in
   ARISE Companion QA. **Save connection and pair chat** stops any current wake
   service before changing its origin.
3. Generate a pairing code on the PC for the selected chat and enter it on phone.
4. Return to the setup screen, configure detector and permissions, activate.
5. Say the phrase while the phone is unlocked. The orb and bottom panel appear.
   Confirm transcription before sending. The PC must have that chat selected
   to accept messages or a stop. Otherwise it returns the existing 409 warning.
6. **Detener** inside the chat sends the existing scoped PC stop. **Mic OFF** or
   the notification Stop only stops phone listening, not background PC tasks.
7. Token expiry requires pairing again if the app was suspended too long. The
   web UI now restores the pairing form after a 401 and avoids overlapping polls.

Android decides whether overlays can appear over particular sensitive apps.
Do not bypass those restrictions. An OEM may stop the service; no invisible
restart is attempted. No battery-optimization exemption or Accessibility Service
is requested. Notifications must be enabled for this QA listener.

## Build and checks

JDK 17, Android SDK platform/build tools 35 and Gradle 8.13:

```sh
cd mobile/android
gradle testDebugUnitTest lintDebug assembleDebug
```

APK: `app/build/outputs/apk/debug/app-debug.apk`. This is a debug-signed QA build,
not a production release. The `Android companion QA` workflow builds it on QA
branches and uploads an artifact with test/lint reports. No main publish occurs.

Automated state tests cover each missing permission/model, wake/expand/hide,
stop without automatic resume, recreation, lock-screen guard and origin escape
attempts. These tests do not exercise real audio, special-access system screens,
WebView cookies or WindowManager on a physical phone.

Required device acceptance before promoting:

- Deny overlay/microphone/notifications independently; activate stays blocked.
- Grant via Android special-access page; verify grant alone never records.
- Import real phrase and Spanish model, activate; confirm visible mic indicator
  and notification, say phrase, verify actual panel appearance.
- Repeat with music/TV/background conversation: measure false accepts/rejects.
- Hide, speak again; expand/reduce; rotate screen, keyboard, small font/large
  font; scroll messages; retain unsent draft and read position.
- Lock screen while panel open: no history visible. Unlock does not automatically
  show it. Check an incoming phone call and denied/revoked audio permission.
- Stop from notification and panel; no later callback reopens microphone/panel.
- Switch PC chat, revoke phone, expire token, disconnect Tailscale, sleep/wake;
  no cross-chat messages, automatic resend or local permission escalation.
- Confirm task results and PC emergency stop independently of phone microphone.
- At least 30–60 min screen-off battery/temperature test on Redmi 13C, with the
  actual Android version and power-management settings recorded.

## Official references

- https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start
- https://developer.android.com/reference/android/provider/Settings#ACTION_MANAGE_OVERLAY_PERMISSION
- https://developer.android.com/about/versions/14/changes/fgs-types-required
- https://picovoice.ai/quick-start/wake-word-android/
- https://github.com/Picovoice/porcupine/tree/master/binding/android

## Verification record (2026-10-22)

- Clean local `testDebugUnitTest lintDebug assembleDebug`: PASS; APK generated.
- Five Android state/origin unit tests: PASS.
- Existing Python companion/connection tests: 14 PASS.
- Node companion client regression checks (401 recovery, no overlapping polls,
  draft preservation, no retry after ambiguous send): PASS.
- Lint: no errors. Remaining warnings concern deliberate JavaScript for the
  restricted companion WebView and Spanish UI strings not yet extracted for
  translation. No warning baseline suppresses errors.
- Physical microphone, actual custom wake model/license, Redmi overlay/battery,
  live Tailscale pairing and PC task execution from this APK: NOT VERIFIED.
