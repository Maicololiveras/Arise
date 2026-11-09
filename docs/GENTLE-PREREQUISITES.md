# External Gentle prerequisites on Windows

Historical engineering record. Version-specific results below are not current
installation instructions. Use [Windows setup](INSTALL-WINDOWS.md),
[owned runtime](owned-gentle-runtime.md) and [validation](VALIDATION.md).

The integrated ARISE engine now ships its own native runtime. The following
applies to advanced external setup and historical installer recovery, not to
normal first-run account login.

Git for Windows supplies Git/Bash for shell tasks; GitHub CLI does not. External
bootstrap may require Node, npm/pnpm, Go and Windows tar. Use the requirements
of the exact selected installer rather than an unpinned global upgrade.
The ARISE build uses Node 24.21.0, npm 11.19.0 and Go 1.25.14.

Inspect before installing:

```powershell
Get-Command git, node, npm.cmd, go -ErrorAction SilentlyContinue
& "$env:SystemRoot\System32\tar.exe" --version
```

Where absent, use the official Git/Go installers or WinGet packages `Git.Git`
and `GoLang.Go`. Reopen the terminal or refresh the process environment, then
verify actual executables and versions. Do not overwrite a global pnpm major
needed by another project or relax directory ACLs to bypass verification.

Historical ARISE 0.4.9 prepared private npm/pnpm under
`%USERPROFILE%\ARISE-Gentle-Prerequisites`, validated existing permissions and
prepared Git/Bash/Go before the official wizard. Later upstream installers own
more of their prerequisite acquisition. Cancellation, missing WinGet or failed
downloads must stop readiness rather than report success.

[Git installation](https://git-scm.com/install/windows) ·
[Go installation](https://go.dev/doc/install) ·
[npm recovery](GENTLE-NPM-RECOVERY.md)
