import json
import time
import requests
from typing import List, Dict, Optional, Iterator
from logger import get_logger

log = get_logger("ollama_client")


class OllamaClient:
    def __init__(self, base_url="http://127.0.0.1:11434", model="huihui_ai/qwen3-abliterated:32b", timeout=300, max_history=100):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.max_history = max_history
        self.conversation_history: List[Dict] = []
        log.info("OllamaClient initialized: base_url=%s model=%s timeout=%s", self.base_url, self.model, self.timeout)

    def _trim_history(self):
        if len(self.conversation_history) > self.max_history:
            keep = self.conversation_history[-self.max_history:]
            if keep and keep[0].get("role") == "tool":
                keep = keep[1:]
            self.conversation_history = keep
            log.debug("History trimmed to %d messages", len(self.conversation_history))

    def add_system_message(self, content: str):
        self.conversation_history.append({"role": "system", "content": content})
        self._trim_history()

    def add_user_message(self, content: str):
        self.conversation_history.append({"role": "user", "content": content})
        self._trim_history()

    def add_assistant_message(self, content: str, tool_calls: Optional[List[Dict]] = None):
        msg = {"role": "assistant", "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.conversation_history.append(msg)
        self._trim_history()

    def add_tool_message(self, tool_call_id: str, content: str, name: str):
        if not tool_call_id:
            tool_call_id = f"call_{int(time.time() * 1000)}"
        self.conversation_history.append({
            "role": "tool",
            "content": content,
            "tool_call_id": tool_call_id,
            "name": name
        })
        self._trim_history()

    def chat(self, message="", tools=None, stream=True) -> Iterator[Dict]:
        if message:
            self.add_user_message(message)
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": self.conversation_history,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
        log.debug("POST %s | messages=%d tools=%s", url, len(self.conversation_history), bool(tools))
        try:
            with requests.post(url, json=payload, stream=True, timeout=self.timeout) as response:
                response.raise_for_status()
                for line_bytes in response.iter_lines(decode_unicode=False):
                    if not line_bytes:
                        continue
                    try:
                        line_str = line_bytes.decode('utf-8').strip()
                        if not line_str:
                            continue
                        try:
                            data = json.loads(line_str)
                            yield data
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            log.warning("JSON decode error on line: %s", line_str[:200])
                            continue
                    except UnicodeDecodeError:
                        log.warning("Unicode decode error on a line, skipping")
                        continue
        except requests.exceptions.ConnectionError as e:
            log.error("Connection error to %s: %s", url, e)
            raise ConnectionError(f"Failed to connect to Ollama at {url}. Is Ollama running? (ollama serve): {e}")
        except requests.exceptions.RequestException as e:
            log.error("Request error to %s: %s", url, e)
            raise RuntimeError(f"Failed to connect to Ollama at {url}: {e}")
