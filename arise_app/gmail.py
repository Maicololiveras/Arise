"""Gmail desktop OAuth with PKCE, user-scoped token vault and no send tool."""
from __future__ import annotations
import base64
import hashlib
import json
import secrets
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from .storage import Vault

SCOPES = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.compose"


def remote_json(url, body=None, headers=None, form=False):
    data = None if body is None else (urllib.parse.urlencode(body).encode() if form else json.dumps(body).encode())
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded" if form else "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.load(response)


class Gmail:
    def __init__(self, storage, emit):
        self.storage, self.emit = storage, emit
        self.vault = Vault(storage.root)
        self.lock = threading.Lock()
        self.connecting = False

    def client(self):
        path = self.storage.config.get("gmail_client_file", "")
        if not path:
            raise RuntimeError("Configura la ruta del JSON OAuth de tipo Desktop de Google.")
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        if "installed" not in data:
            raise ValueError("El JSON debe ser de una aplicación de escritorio.")
        return data["installed"]

    def connect(self):
        with self.lock:
            if self.connecting:
                raise RuntimeError("Ya hay una conexión de Gmail en curso.")
            self.connecting = True
        try:
            client = self.client()
            from .storage import protect
            protect(b"ARISE credential check")  # fail before opening OAuth outside Windows
        except Exception:
            self.connecting = False
            raise
        threading.Thread(target=self._authorize, args=(client,), daemon=True).start()

    def _authorize(self, client):
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        result = {}

        class Callback(BaseHTTPRequestHandler):
            def do_GET(self):
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                valid = query.get("state", [""])[0] == state and urllib.parse.urlparse(self.path).path == "/callback"
                if valid:
                    result.update({"code": query.get("code", [""])[0], "error": query.get("error", [""])[0]})
                self.send_response(200 if valid else 400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(("Vuelve a ARISE para comprobar la conexión." if valid else "Solicitud inválida.").encode())
            def log_message(self, *_):
                pass

        server = None
        try:
            server = HTTPServer(("127.0.0.1", 0), Callback)
            server.timeout = 1
            redirect = f"http://127.0.0.1:{server.server_port}/callback"
            query = urllib.parse.urlencode({"client_id": client["client_id"], "redirect_uri": redirect,
                "response_type": "code", "scope": SCOPES, "access_type": "offline", "prompt": "consent",
                "state": state, "code_challenge": challenge, "code_challenge_method": "S256"})
            webbrowser.open("https://accounts.google.com/o/oauth2/v2/auth?" + query)
            deadline = time.monotonic() + 180
            while not result and time.monotonic() < deadline:
                server.handle_request()
            if not result.get("code"):
                raise RuntimeError("Google no autorizó la conexión o se agotó el tiempo.")
            tokens = remote_json("https://oauth2.googleapis.com/token", {
                "client_id": client["client_id"], "client_secret": client.get("client_secret", ""),
                "redirect_uri": redirect, "code": result["code"], "code_verifier": verifier,
                "grant_type": "authorization_code"}, form=True)
            if not tokens.get("refresh_token"):
                raise RuntimeError("Google no devolvió una credencial renovable; vuelve a conectar.")
            tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600)
            self.vault.write(tokens)
            self.emit("notice", {"text": "Gmail conectado. Búsqueda, lectura y borradores disponibles."})
        except Exception as error:
            self.emit("error", {"text": f"Gmail: {type(error).__name__}. Revisa el JSON OAuth y la autorización de Google."})
        finally:
            if server:
                server.server_close()
            self.connecting = False

    def access_token(self):
        with self.lock:
            tokens = self.vault.read()
            if not tokens:
                raise RuntimeError("Gmail no está conectado.")
            if tokens.get("expires_at", 0) < time.time() + 60:
                client = self.client()
                update = remote_json("https://oauth2.googleapis.com/token", {
                    "client_id": client["client_id"], "client_secret": client.get("client_secret", ""),
                    "refresh_token": tokens["refresh_token"], "grant_type": "refresh_token"}, form=True)
                tokens.update(update)
                tokens["expires_at"] = time.time() + update.get("expires_in", 3600)
                self.vault.write(tokens)
            return tokens["access_token"]

    def request(self, path, body=None):
        return remote_json("https://gmail.googleapis.com/gmail/v1/users/me/" + path, body,
            {"Authorization": "Bearer " + self.access_token()})

    def search(self, query="", limit=10):
        listing = self.request("messages?" + urllib.parse.urlencode({"q": query, "maxResults": max(1, min(int(limit), 20))}))
        output = []
        for item in listing.get("messages", []):
            message = self.request("messages/" + urllib.parse.quote(item["id"], safe="") + "?format=metadata")
            headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}
            output.append({"id": item["id"], "from": headers.get("from"), "subject": headers.get("subject"),
                "date": headers.get("date"), "snippet": message.get("snippet", "")})
        return {"messages": output, "untrusted_content": True}

    def read(self, message_id):
        result = self.request("messages/" + urllib.parse.quote(message_id, safe="") + "?format=full")
        payload = result.get("payload", {})
        plain = []
        def collect(part):
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                data = part["body"]["data"]
                plain.append(base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace"))
            for child in part.get("parts", []):
                collect(child)
        collect(payload)
        return {"id": result["id"], "headers": payload.get("headers", []),
            "text": "\n".join(plain)[:20000] or result.get("snippet", ""), "untrusted_content": True}

    def draft(self, to, subject, body, attachments=()):
        if not to or "\n" in to or "\r" in to:
            raise ValueError("Destinatario inválido.")
        message = EmailMessage()
        message["To"], message["Subject"] = to, subject
        message.set_content(body)
        for filename, data, mime in attachments:
            maintype, subtype = mime.split("/", 1)
            message.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        result = self.request("drafts", {"message": {"raw": raw}})
        return {"draft_id": result["id"], "sent": False}

    def draft_preview(self, draft_id):
        result = self.request("drafts/" + urllib.parse.quote(draft_id, safe="") + "?format=full")
        message = result.get("message", {})
        headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}
        return {"draft_id": draft_id, "to": headers.get("to", ""), "subject": headers.get("subject", ""),
            "snippet": message.get("snippet", ""), "notice": "Revisa el borrador completo en Gmail antes de enviarlo."}

    def mark_send_attempt(self, draft_id):
        with self.storage.lock, self.storage.db:
            self.storage.db.execute("CREATE TABLE IF NOT EXISTS gmail_send_attempts(draft_id TEXT PRIMARY KEY,created REAL)")
            cursor = self.storage.db.execute("INSERT OR IGNORE INTO gmail_send_attempts VALUES(?,?)", (draft_id, time.time()))
            return cursor.rowcount == 1

    def send_draft(self, draft_id):
        result = self.request("drafts/send", {"id": draft_id})
        return {"message_id": result["id"], "sent": True}
