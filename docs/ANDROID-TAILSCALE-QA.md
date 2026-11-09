# Manual Android/Tailscale setup (superseded)

Historical engineering record. Version-specific results below are not current
installation instructions. Use [Windows setup](INSTALL-WINDOWS.md),
[owned runtime](owned-gentle-runtime.md) and [validation](VALIDATION.md).

Use [guided mobile setup](MOBILE-GUIDED-QA.md) for the current QR/authenticator
flow. The original manual procedure used these steps:

1. Verify PC chat independently of Tailscale.
2. Install Tailscale from its official distribution on Windows and Android,
   connect to the same tailnet and inspect `tailscale status`.
3. Obtain the PC's HTTPS `.ts.net` name from `tailscale status --json`.
4. Prepare the mobile server for the selected chat in ARISE. Use the exact
   `tailscale serve --bg http://127.0.0.1:PORT` command returned by ARISE.
   Never guess the daemon port or replace an unrelated Serve service.
5. Verify `tailscale serve status`, then pair the phone using a one-use,
   five-minute invitation. Keep the originating chat active and test both directions.
6. Revoke the device or stop mobile access from the PC when finished.

The old flow could change the port after restart; the guided flow now persists
it. Pairing does not grant local execution or desktop control and does not cancel
existing reminders when revoked.

iPad uses Tailscale and Safari; Android APK overlays/wake detection do not run on
iPad. Optional Porcupine wake detection requires the correct Android Spanish
models and an AccessKey, none of which is supplied. Hiding the panel does not
stop the optional detector; Mic OFF does.

Android 0.1.1 QA adopted the first frame of the desktop orb and bounded public
update metadata. Update checks do not send pairing tokens; APK installation
requires confirmation and Android authorization. Debug signing does not promise
in-place upgrades or absence of Play Protect warnings.
