# Optional remote access

For the supported Windows/Android QA flow use [guided mobile setup](MOBILE-GUIDED-QA.md).
The general gateway below is an advanced text gateway, not an automatic VPS or
Coolify deployment. It does not turn a Linux server into a Windows desktop.

The gateway exposes text conversation, status, stop and permitted review actions.
It listens on loopback. Never publish the internal daemon bridge or its descriptor.

```powershell
$env:ARISE_REMOTE_PASSWORD = 'choose-a-long-unique-password'
python -m arise_app.gateway --data-dir "$env:LOCALAPPDATA\ARISE-Orb" --public-origin https://arise.example.com --port 8766
```

Place a TLS reverse proxy on the same host, preserving the public Host:

```caddy
arise.example.com {
    reverse_proxy 127.0.0.1:8766
}
```

If the proxy is elsewhere, use an authenticated private tunnel to the gateway,
not the daemon's port. This network configuration is not deployed by ARISE.
Local development may use `http://127.0.0.1:8766`; public HTTP origins are rejected.
The password is independent of model accounts. Sessions expire after one hour
and login attempts are limited. TLS must be verified in the actual deployment.

A user service must use the intended working/data directory and protected
credentials. Do not copy Windows credential files to Linux. VPS/Coolify lifecycle,
installation and support are deferred to a future release.
