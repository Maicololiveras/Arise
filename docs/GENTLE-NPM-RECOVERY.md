# Gentle Shell installation or recovery with npm (Windows)

This is an alternative installation path, not a replacement for ARISE's bundled
runtime or the official Gentle bootstrap. The npm package is **`gentle-pi`**;
its launcher command is **`gentle-shell`**.

## Requirements and evidence

The inspected `gentle-pi@4.5.0` package declares Node **>=22.19.0** and an
optional Pi peer dependency **>=1.2.0**. Optional means npm need not install Pi;
opening the launcher and verifying ARISE RPC remain separate checks. Use a Node
installation with npm available, and Git for Windows/Bash for Pi's shell tools.

ARISE's bundled profile uses Node 24.21.0, npm 11.19.0, Gentle 4.7.0 and Pi 1.5.0.
Those bundle pins do not certify every global npm installation. No npm-specific
minimum or clean Windows global-install compatibility matrix has been validated
for this alternative path. Record the actual versions when testing it.

Existing evidence: a user reported that the npm installation below allowed
`gentle-shell` to open. Automated discovery tests cover an npm package layout,
launcher-resolved agent home and Pi's `dist/bundle/cli.js` entry without executing
Pi. They use fixtures; they are not an end-to-end Windows installation test.

## 1. Install the package

Close ARISE and open PowerShell. First inspect the commands that will run:

```powershell
Get-Command node, npm.cmd -ErrorAction Stop | Select-Object Name, Source
node --version
npm.cmd --version
git --version
```

Install the package as a separate command. This changes your global npm
installation and may run the package's installation scripts:

```powershell
npm.cmd install --global gentle-pi
```

`npm i -g gentle-pi` is the equivalent npm shorthand. The unpinned command tracks
the registry's current default version; do not assume it installs 4.5.0. Record
what was actually installed:

```powershell
npm.cmd list --global gentle-pi --depth=0
npm.cmd root --global
Get-Command gentle-shell -All | Select-Object Name, Source
```

Do not repair permission errors by disabling protections or changing directory
ACLs indiscriminately. Preserve the first installation error and its exit code.

## 2. Open the launcher separately

```powershell
gentle-shell
```

If PowerShell blocks a `.ps1` shim, run `gentle-shell.cmd` instead; do not change
the execution policy just to bypass the shim. Complete authentication locally if
requested. Never paste credentials or authentication files into issue reports.
Exit the launcher before checking ARISE. Opening the launcher proves only that
step, not that ARISE has selected the same Node, Pi or agent home.

## 3. Detect and verify from ARISE

1. Reopen ARISE so it receives the updated environment.
2. In Settings, explicitly select **External installation (advanced)**, then use **Detect Pi and Gentle Shell**, inspect the detected paths,
   and save. The Gentle folder must contain its `package.json` and `extensions`;
   the launcher/shim directory and the agent home are different locations.
3. Confirm the agent home matches the environment reported by the launcher.
   Do not substitute a different user's paths or overwrite authentication data.
4. Test a chat and check that the real RPC connection, active Pi version and
   Gentle extensions are reported. A detected folder is not an RPC success.
5. Test dictation, Engram and desktop control independently; their failures are
   not fixed merely because Gentle opens.

If detection fails, report sanitized command paths, package/Node/npm versions,
the failed stage and exit code. Keep installation, launcher opening, discovery,
and RPC results as separate PASS/FAIL/BLOCKED entries.

`gentle-shell --link` is not part of this procedure: its behavior and necessity
have not been verified here. This guide does not claim to repair ACLs,
Antigravity, microphone drivers or unrelated installation errors.
