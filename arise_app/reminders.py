"""PC-owned durable reminders with chat-scoped, explicitly authorized delivery."""
from datetime import datetime
import json
import threading
import time
import uuid

TOOLS = [
    {"name": "reminders.create", "description": "Programa un recordatorio en este PC. Solicita confirmación visible del texto, hora y destino. No ejecuta código. El PC y ARISE deben estar encendidos.",
     "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}, "at": {"type": "string", "description": "ISO 8601 con zona, por ejemplo 2026-10-23T09:00:00-05:00"}, "every_seconds": {"type": "integer", "minimum": 60}, "provider": {"enum": ["chat", "telegram", "whatsapp", "outlook", "teams"]}, "destination": {"type": "string"}}, "required": ["text", "at"], "additionalProperties": False}},
    {"name": "reminders.list", "description": "Lista los recordatorios de este chat y su estado de entrega.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "reminders.cancel", "description": "Cancela futuras ocurrencias de un recordatorio de este chat.", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
]


class Reminders:
    def __init__(self, runtime):
        self.runtime = runtime
        self.storage = runtime.storage
        self.stop_event = threading.Event()
        self.thread = None
        self.delivery_lock = threading.RLock()
        with self.storage.lock, self.storage.db:
            self.storage.db.executescript('''
                CREATE TABLE IF NOT EXISTS reminders(id TEXT PRIMARY KEY,chat TEXT,payload TEXT,due REAL,status TEXT);
                CREATE TABLE IF NOT EXISTS reminder_deliveries(id TEXT PRIMARY KEY,reminder TEXT,chat TEXT,status TEXT);
            ''')
            # A crash after a network write is ambiguous. Never retry it blindly.
            rows = self.storage.db.execute("SELECT id,chat FROM reminder_deliveries WHERE status='sending'").fetchall()
            for row in rows:
                if self.stop_event.is_set(): break
                self.storage.db.execute("UPDATE reminder_deliveries SET status='unknown' WHERE id=?", (row['id'],))
                self._message(row['chat'], "ARISE reinició durante una entrega. Comprueba el canal antes de reenviar.")

    def _message(self, chat, text):
        # Same transaction as the occurrence marker: restart cannot duplicate fallback.
        self.storage.db.execute("INSERT INTO messages(id,conversation,role,text,created,images) VALUES(?,?,?,?,?,?)",
                                (uuid.uuid4().hex, chat, "assistant", text, time.time(), '[]'))

    def create(self, chat, args):
        text = args.get("text")
        if not isinstance(text, str) or not 0 < len(text.strip()) <= 3500: raise ValueError("Recordatorio vacío o demasiado largo.")
        when = datetime.fromisoformat(args.get("at", ""))
        if when.tzinfo is None or when.timestamp() <= time.time(): raise ValueError("Elige una fecha futura con zona horaria explícita.")
        every = args.get("every_seconds", 0)
        if type(every) is not int or (every != 0 and not 60 <= every <= 366*86400): raise ValueError("Intervalo inválido.")
        provider = args.get("provider", "chat")
        destination = args.get("destination", "")
        if provider not in ("chat", *self.runtime.connections.providers): raise ValueError("Canal desconocido.")
        if not isinstance(destination, str) or len(destination) > 320 or (provider != "chat" and not destination.strip()): raise ValueError("Especifica el destinatario exacto.")
        generation = self.runtime.stop_generation
        self.runtime.ask_approval("Programar recordatorio", f"{text}\nFecha: {when.isoformat()}\nCada: {every or 'una vez'} segundos\nDestino: {provider} {destination}\nSi falla, conservar en este chat. El PC debe estar encendido.")
        with self.runtime.transition_lock, self.storage.lock, self.storage.db:
            if self.runtime.conversation != chat or self.runtime.stop_generation != generation: raise ValueError("Cambió el chat o se detuvo la operación.")
            identity = uuid.uuid4().hex
            payload = dict(text=text, at=when.isoformat(), every_seconds=every, provider=provider, destination=destination)
            self.storage.db.execute("INSERT INTO reminders VALUES(?,?,?,?,?)", (identity, chat, json.dumps(payload), when.timestamp(), "scheduled"))
        return {"id": identity, "status": "scheduled", **payload}

    def list(self, chat):
        with self.storage.lock:
            return [{"id": r['id'], "status": r['status'], "due": r['due'], **json.loads(r['payload'])} for r in self.storage.db.execute("SELECT * FROM reminders WHERE chat=? ORDER BY due", (chat,))]

    def cancel(self, chat, identity):
        with self.delivery_lock, self.storage.lock, self.storage.db:
            count = self.storage.db.execute("UPDATE reminders SET status='cancelled' WHERE id=? AND chat=?", (identity, chat)).rowcount
            if not count: raise ValueError("Recordatorio ajeno o inexistente.")
        return {"id": identity, "status": "cancelled"}

    def tick(self, now=None):
        now = time.time() if now is None else now
        with self.delivery_lock:
            with self.storage.lock:
                rows = self.storage.db.execute("SELECT * FROM reminders WHERE status='scheduled' AND due<=? ORDER BY due LIMIT 25", (now,)).fetchall()
            for row in rows:
                payload = json.loads(row['payload'])
                occurrence = row['id'] + ':' + str(row['due'])
                with self.storage.lock, self.storage.db:
                    inserted = self.storage.db.execute("INSERT OR IGNORE INTO reminder_deliveries VALUES(?,?,?,?)", (occurrence, row['id'], row['chat'], 'sending')).rowcount
                    interval = payload['every_seconds']
                    # Coalesce missed intervals after sleep; don't flood the user.
                    if interval:
                        next_due = row['due'] + (int((now-row['due'])//interval)+1)*interval
                        self.storage.db.execute("UPDATE reminders SET due=? WHERE id=?", (next_due, row['id']))
                    else:
                        self.storage.db.execute("UPDATE reminders SET status='finished' WHERE id=?", (row['id'],))
                    if inserted:
                        self._message(row['chat'], 'Recordatorio · ' + payload['text'])
                if not inserted: continue
                status = 'chat'
                if payload['provider'] != 'chat':
                    try:
                        self.runtime.connections.send(payload['provider'], payload['destination'], payload['text'])
                        status = 'accepted_by_provider'
                    except Exception:
                        status = 'unknown'
                        with self.storage.lock, self.storage.db:
                            self._message(row['chat'], 'Entrega externa no confirmada. El recordatorio queda aquí; no se reenviará automáticamente.')
                with self.storage.lock, self.storage.db:
                    self.storage.db.execute("UPDATE reminder_deliveries SET status=? WHERE id=?", (status, occurrence))
                # Do not inject an inactive chat's message into the visible chat.
                if self.runtime.conversation == row['chat']:
                    self.runtime.emit('notice', {'text': 'Recordatorio · ' + payload['text'], 'conversation': row['chat']})

    def start(self):
        if self.thread: return
        def run():
            while not self.stop_event.wait(1):
                try: self.tick()
                except Exception:
                    self.runtime.emit('error', {'text': 'No se pudo procesar un recordatorio; revisa su estado.'})
        self.thread = threading.Thread(target=run, daemon=True, name='arise-reminders')
        self.thread.start()

    def close(self):
        self.stop_event.set()
        if self.thread: self.thread.join(timeout=25)
