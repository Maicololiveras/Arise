"""Explicit outbound destinations. Secrets remain in the PC's DPAPI vault.

No inbound service message is treated as permission to execute local commands.
Transport failures are ambiguous: callers must not automatically retry sends.
"""
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from .storage import Vault


class ConnectionError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def request_json(url, payload, token=None, form=False):
    data = urllib.parse.urlencode(payload).encode() if form else json.dumps(payload).encode()
    headers = {"Content-Type": "application/x-www-form-urlencoded" if form else "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=20) as response:
            raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                raise ConnectionError("Respuesta demasiado grande; comprueba el servicio.")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        # Never expose a URL containing a Telegram token or raw provider response.
        if form:
            try:
                value = json.loads(error.read(10000))
                return {"error": str(value.get("error", "oauth_error"))[:80]}
            except (ValueError, OSError):
                pass
        raise ConnectionError(f"El proveedor respondió HTTP {error.code}. Revisa el destino antes de repetir.") from None
    except (OSError, ValueError):
        raise ConnectionError("Entrega sin confirmar. No se reintentará automáticamente.") from None


class Connections:
    providers = ("telegram", "whatsapp", "outlook", "teams")

    def __init__(self, root, request=request_json, vault=None):
        self.vault = vault or Vault(root, "connections")
        self.request = request
        self.lock = threading.RLock()
        self.pending = {}

    def status(self):
        with self.lock:
            saved = self.vault.read() or {}
            return [{"provider": p, "configured": bool(saved.get(p)),
                     "verified": False, "direction": "outbound"} for p in self.providers]

    def save_token(self, provider, token, **options):
        if provider not in ("telegram", "whatsapp") or not isinstance(token, str) or not 10 <= len(token) <= 4096:
            raise ValueError("Proveedor o token inválido.")
        if provider == "telegram" and not re.fullmatch(r"\d+:[A-Za-z0-9_-]+", token):
            raise ValueError("Token de bot Telegram inválido.")
        if provider == "whatsapp":
            if not re.fullmatch(r"\d+", str(options.get("phone_id", ""))) or not re.fullmatch(r"v\d+\.\d+", str(options.get("api_version", ""))):
                raise ValueError("WhatsApp requiere phone_id y versión de Graph API explícita.")
            if not re.fullmatch(r"[a-z0-9_]{1,512}", str(options.get('template', ''))) or not re.fullmatch(r"[a-z]{2}(?:_[A-Z]{2})?", str(options.get('language', ''))):
                raise ValueError('Indica una plantilla aprobada con una variable de cuerpo y su idioma exacto.')
        with self.lock:
            saved = self.vault.read() or {}
            saved[provider] = {"access_token": token, **{k: options[k] for k in ("phone_id", "api_version", "template", "language") if k in options}}
            self.vault.write(saved)

    def disconnect(self, provider):
        with self.lock:
            saved = self.vault.read() or {}
            saved.pop(provider, None)
            self.pending.pop(provider, None)
            self.vault.write(saved)

    def oauth_start(self, provider, client_id):
        if provider not in ("outlook", "teams") or not re.fullmatch(r"[0-9a-fA-F-]{36}", client_id):
            raise ValueError("Se necesita un Application (client) ID de Microsoft Entra.")
        tenant = "organizations" if provider == "teams" else "common"
        scope = "offline_access " + ("ChatMessage.Send" if provider == "teams" else "Mail.Send")
        value = self.request(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/devicecode",
                             {"client_id": client_id, "scope": scope}, form=True)
        if "device_code" not in value:
            raise ConnectionError("Microsoft no inició la conexión. Revisa la app pública y las políticas del tenant.")
        with self.lock:
            self.pending[provider] = {**value, "client_id": client_id, "tenant": tenant,
                                      "deadline": time.time() + value["expires_in"], "next_poll": time.time() + value.get("interval", 5)}
        return {k: value[k] for k in ("user_code", "verification_uri", "expires_in")}

    def oauth_poll(self, provider):
        with self.lock:
            value = self.pending.get(provider)
            if not value or time.time() >= value["deadline"]:
                self.pending.pop(provider, None)
                raise ConnectionError("La conexión expiró; inicia sesión de nuevo.")
            if time.time() < value["next_poll"]:
                return {"status": "pending"}
            result = self.request(f"https://login.microsoftonline.com/{value['tenant']}/oauth2/v2.0/token",
                                  {"client_id": value["client_id"], "device_code": value["device_code"],
                                   "grant_type": "urn:ietf:params:oauth:grant-type:device_code"}, form=True)
            error = result.get("error")
            if error in ("authorization_pending", "slow_down"):
                value["interval"] = value.get("interval", 5) + (5 if error == "slow_down" else 0)
                value["next_poll"] = time.time() + value["interval"]
                return {"status": "pending"}
            if error or "access_token" not in result:
                self.pending.pop(provider, None)
                raise ConnectionError("Microsoft rechazó la conexión; revisa consentimiento y políticas.")
            saved = self.vault.read() or {}
            saved[provider] = {**result, "client_id": value["client_id"], "tenant": value["tenant"],
                               "expires_at": time.time() + result.get("expires_in", 3600)}
            self.vault.write(saved)
            self.pending.pop(provider, None)
            return {"status": "connected"}

    def _account(self, provider):
        saved = self.vault.read() or {}
        account = saved.get(provider)
        if not account:
            raise ConnectionError("Conector no configurado.")
        if provider in ("outlook", "teams") and time.time() >= account.get("expires_at", 0) - 60:
            if not account.get("refresh_token"):
                raise ConnectionError("Vuelve a conectar tu cuenta Microsoft.")
            fresh = self.request(f"https://login.microsoftonline.com/{account['tenant']}/oauth2/v2.0/token",
                                 {"client_id": account["client_id"], "refresh_token": account["refresh_token"],
                                  "grant_type": "refresh_token"}, form=True)
            if "access_token" not in fresh:
                raise ConnectionError("No se pudo renovar Microsoft; vuelve a conectar.")
            account.update(fresh, expires_at=time.time() + fresh.get("expires_in", 3600))
            self.vault.write(saved)
        return account

    def send(self, provider, destination, text):
        if provider not in self.providers or not isinstance(text, str) or not 0 < len(text) <= 3500:
            raise ValueError("Proveedor o mensaje inválido (máximo 3500 caracteres).")
        with self.lock:
            account = self._account(provider)
            token = account["access_token"]
            if provider == "telegram":
                if not re.fullmatch(r"-?\d+", destination): raise ValueError("Usa el ID exacto del chat Telegram.")
                result = self.request(f"https://api.telegram.org/bot{token}/sendMessage", {"chat_id": destination, "text": text})
                if result.get("ok") is not True: raise ConnectionError("Telegram no confirmó el envío.")
            elif provider == "outlook":
                if not re.fullmatch(r"[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+", destination): raise ValueError("Correo inválido.")
                self.request("https://graph.microsoft.com/v1.0/me/sendMail", {"message": {
                    "subject": "ARISE · Recordatorio", "body": {"contentType": "Text", "content": text},
                    "toRecipients": [{"emailAddress": {"address": destination}}]}}, token=token)
            elif provider == "teams":
                chat = urllib.parse.quote(destination, safe="")
                if not destination or len(destination) > 300: raise ValueError("Chat Teams inválido.")
                self.request(f"https://graph.microsoft.com/v1.0/chats/{chat}/messages",
                             {"body": {"contentType": "text", "content": text}}, token=token)
            else:
                if not re.fullmatch(r"\d{8,15}", destination): raise ValueError('Usa el número internacional sin +.')
                if not account.get('template'): raise ConnectionError('Falta la plantilla aprobada de WhatsApp.')
                self.request(f"https://graph.facebook.com/{account['api_version']}/{account['phone_id']}/messages",
                             {'messaging_product':'whatsapp', 'to':destination, 'type':'template', 'template':{
                                 'name':account['template'], 'language':{'code':account['language']},
                                 'components':[{'type':'body','parameters':[{'type':'text','text':text}]}]}}, token=token)
        return {"status": "accepted_by_provider"}
