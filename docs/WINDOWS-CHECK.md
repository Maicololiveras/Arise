# Physical Windows acceptance checklist

Use a real desktop, microphone and test accounts. Docker and offscreen Qt do not
prove these behaviors. Record version, architecture, devices and exact results;
a user success report is not a blanket pass for every item or another platform.

- [ ] Install on a clean x64 PC without global Node/Python/Gentle.
- [ ] Start the integrated engine and verify actual Gentle commands and memory.
- [ ] Connect an account in Settings and choose an available model.
- [ ] Verify microphone/output selection and output-only speech preview.
- [ ] Test dictation separately: draft insertion, correction, cancellation and no automatic send.
- [ ] Test wake phrases, opt-in capture, mute and panel-opening preference.
- [ ] Test speech interruption with headphones; check feedback with speakers.
- [ ] Test Ctrl+Alt+A / Ctrl+Alt+Esc without shortcut conflicts.
- [ ] Check orb dragging, multiple monitors and 100/150/200% scaling.
- [ ] Hide/reopen chat during work without duplicating the session.
- [ ] Verify real MCP catalogs and a visible InputControl indicator.
- [ ] Capture Notepad, authorize control, type harmless text, verify and stop.
- [ ] Confirm overlay clearing and no capture/control after revocation.
- [ ] Test delegated questions, replies, steering, explicit completion and cancellation.
- [ ] Check long approval/settings dialogs with response buttons still visible.
- [ ] Test Gmail only with a test account: draft, reject, approve once, verify externally.
- [ ] Interrupt network delivery; inspect the external result before retrying.
- [ ] Restart during work; confirm interrupted tasks are not replayed.
- [ ] Upgrade over a running installation and retain chats, models and memory.
- [ ] Test optional autostart and uninstall without claiming removal of retained data.

No acoustic echo cancellation is implemented. Authenticode signing requires a
distributor certificate; unsigned builds must not be presented as signed.
For ARM64 use the separate [native acceptance gates](NATIVE-DISTRIBUTIONS.md).
