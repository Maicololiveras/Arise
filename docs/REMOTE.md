# Acceso remoto opcional

El gateway proporciona conversación por texto, estado, detener y revisión de envío. La voz sigue en el daemon del equipo anfitrión. No ofrece audio del navegador ni convierte un VPS Linux en un escritorio Windows.

En el equipo que ejecuta el daemon:

```powershell
$env:ARISE_REMOTE_PASSWORD = 'elige-una-clave-larga-y-unica'
python -m arise_app.gateway --data-dir "$env:LOCALAPPDATA\ARISE-Orb" --public-origin https://arise.example.com --port 8766
```

El gateway escucha únicamente en 127.0.0.1. Coloca Caddy u otro proxy con TLS delante; conserva el Host público. Ejemplo de Caddy cuando proxy y gateway están en el mismo equipo:

```caddy
arise.example.com {
    reverse_proxy 127.0.0.1:8766
}
```

Para un proxy en VPS y un agente Windows en casa, conecta ambos por una red privada y crea un túnel autenticado. Configura el proxy contra el extremo de ese túnel, no contra el puerto interno del daemon. La configuración depende de tu red y no está desplegada automáticamente por este repositorio.

En desarrollo se puede usar `--public-origin http://127.0.0.1:8766` desde el mismo equipo. Los orígenes públicos HTTP se rechazan. La contraseña es independiente de las cuentas de modelos. El gateway admite una sesión de una hora y limita intentos de acceso. La autenticación y CSRF se prueban con HTTP local; la configuración TLS real debe comprobarse en su despliegue.

Para mantenerlo activo en VPS, usa un servicio de usuario/systemd con WorkingDirectory del checkout, el mismo data-dir y EnvironmentFile protegido. No publiques el descriptor daemon.json ni copies credenciales Windows a un servidor Linux.
