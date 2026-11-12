"""Local open-weight reader through Ollama, with the same interface as LLMLinker.run().

Used to check that LongMemEval findings are not specific to Claude readers. Responses are
schema-constrained JSON (Ollama `format`), decoded greedily, and cached on disk.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor

OLLAMA = "http://localhost:11434/api/chat"


class OllamaReader:
    def __init__(self, model: str, cache_path: str, workers: int = 2):
        self.model, self.cache_path, self.workers = model, cache_path, workers
        self.cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
        self.lock = threading.Lock()
        self.usage = {"input_tokens": 0, "output_tokens": 0, "calls": 0, "refusals": 0}

    def _key(self, prompt: str, system: str) -> str:
        return hashlib.sha256(f"ollama|{self.model}|{system}|{prompt}".encode()).hexdigest()

    def _call(self, prompt: str, system: str, schema: dict) -> dict:
        key = self._key(prompt, system)
        if key in self.cache:
            return self.cache[key]
        body = json.dumps({"model": self.model, "stream": False, "format": schema,
                           "options": {"temperature": 0, "num_ctx": 16384},
                           "messages": [{"role": "system", "content": system},
                                        {"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
        r = json.load(urllib.request.urlopen(req, timeout=600))
        try:
            result = json.loads(r["message"]["content"])
        except json.JSONDecodeError:
            result = {"answer": r["message"]["content"]}
        with self.lock:
            self.usage["calls"] += 1
            self.usage["input_tokens"] += r.get("prompt_eval_count", 0)
            self.usage["output_tokens"] += r.get("eval_count", 0)
            self.cache[key] = result
            if self.usage["calls"] % 25 == 0:
                self._save()
        return result

    def _save(self):
        if not self.usage["calls"]:
            return
        tmp = f"{self.cache_path}.{os.getpid()}.tmp"
        json.dump(self.cache, open(tmp, "w"))
        os.replace(tmp, self.cache_path)

    def run(self, prompts: list[str], system: str, schema: dict) -> list[dict]:
        uniq = list(dict.fromkeys(prompts))
        try:
            with ThreadPoolExecutor(self.workers) as ex:
                res = dict(zip(uniq, ex.map(lambda p: self._call(p, system, schema), uniq)))
        finally:
            with self.lock:
                self._save()
        return [res[p] for p in prompts]
