"""Ollama client with native tool calling support."""
import json
import sys
import requests
from typing import List, Dict, Optional, Callable, Iterator
import time


class OllamaClient:
    """Client for interacting with Ollama API with tool calling."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "huihui_ai/qwen3-abliterated:32b"):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.conversation_history: List[Dict] = []
        
    def chat(
        self, 
        message: str = "", 
        tools: Optional[List[Dict]] = None,
        stream: bool = True
    ) -> Iterator[Dict]:
        """Send a chat message and stream responses."""
        # Only add user message to history if provided (for first iteration)
        if message:
            self.conversation_history.append({"role": "user", "content": message})
        
        # Prepare request
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": self.conversation_history,
            "stream": stream,
        }
        
        if tools:
            payload["tools"] = tools
            
        # Make streaming request
        try:
            with requests.post(url, json=payload, stream=True, timeout=300) as response:
                response.raise_for_status()
                
                # Ollama sends each JSON object on a separate line
                # iter_lines() already splits on newlines, so each line is a complete JSON object
                for line_bytes in response.iter_lines(decode_unicode=False):
                    if not line_bytes:
                        continue
                    
                    try:
                        # Decode the line
                        line_str = line_bytes.decode('utf-8').strip()
                        if not line_str:
                            continue
                        
                        # Each line should be a complete JSON object
                        try:
                            data = json.loads(line_str)
                            yield data
                            
                            if data.get("done"):
                                # Add assistant response to history
                                if data.get("message"):
                                    self.conversation_history.append(data["message"])
                                break
                        except json.JSONDecodeError:
                            # Log JSON decode errors but continue
                            continue
                            
                    except UnicodeDecodeError:
                        continue
                        
        except requests.exceptions.ConnectionError as e:
            raise Exception(f"Failed to connect to Ollama at {url}. Is Ollama running? (ollama serve): {e}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to connect to Ollama at {url}: {e}")
    
    def add_assistant_message(self, content: str, tool_calls: Optional[List[Dict]] = None):
        """Add an assistant message to conversation history."""
        msg = {"role": "assistant", "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.conversation_history.append(msg)
    
    def add_tool_message(self, tool_call_id: str, content: str, name: str):
        """Add a tool response to conversation history."""
        self.conversation_history.append({
            "role": "tool",
            "content": content,
            "tool_call_id": tool_call_id,
            "name": name
        })

