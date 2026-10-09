import os
from .storage import Vault

ENV = {"openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}

class Credentials:
    def __init__(self, root):
        self.vault = Vault(root, "providers")
        self.session = {}

    def get(self, provider):
        if provider in self.session:
            return self.session[provider]
        value = os.getenv(ENV.get(provider, ""), "")
        if value:
            return value
        saved = self.vault.read() or {}
        return saved.get(provider, "")

    def save(self, provider, value, persist=True):
        if provider not in (*ENV, "github-updates") or not isinstance(value, str) or len(value) > 4096:
            raise ValueError("Proveedor o clave inválidos")
        if persist:
            data = self.vault.read() or {}
            if value:
                data[provider] = value.strip()
            else:
                data.pop(provider, None)
            self.vault.write(data)
        self.session[provider] = value.strip()

    def environment(self):
        return {variable: self.get(provider) for provider, variable in ENV.items() if self.get(provider)}
