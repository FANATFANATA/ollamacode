from rich.console import Console
from rich.panel import Panel
from rich import box
from typing import List
from logger import get_logger

log = get_logger("ui")


class ChatUI:
    def __init__(self):
        self.console = Console()
        self.messages: List[dict] = []
        self.current_response = ""

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def update_response(self, text: str):
        self.current_response = text

    def clear_response(self):
        self.current_response = ""

    def _truncate(self, content: str, max_len: int) -> str:
        if len(content) <= max_len:
            return content
        return content[:max_len] + "..."

    def render_message(self, message: dict) -> str:
        role = message.get("role", "unknown")
        content = message.get("content", "")
        if not isinstance(content, str):
            content = str(content)
        if role == "user":
            return f"[bold blue]You:[/bold blue] {content}"
        elif role == "assistant":
            return f"[bold green]Assistant:[/bold green]\n{content}"
        elif role == "tool":
            content_str = self._truncate(content, 200)
            return f"[dim]Tool ({message.get('name', 'unknown')}): {content_str}[/dim]"
        return f"[{role}]: {content}"

    def render_chat(self) -> Panel:
        content_lines = []
        for msg in self.messages:
            content_lines.append(self.render_message(msg))
            content_lines.append("")
        if self.current_response:
            content_lines.append("[bold green]Assistant:[/bold green]")
            content_lines.append(self.current_response)
        content = "\n".join(content_lines)
        return Panel(
            content,
            title="[bold cyan]OllamaCode - Agentic Coding Assistant[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED
        )

    def print(self, *args, **kwargs):
        self.console.print(*args, **kwargs)

    def clear(self):
        self.console.clear()

    def refresh(self):
        chat_panel = self.render_chat()
        self.console.clear()
        self.console.print(chat_panel)

    def show_thinking(self, message: str = "Thinking..."):
        self.console.print(f"[dim italic]{message}[/dim italic]")

    def show_tool_start(self, tool_name: str):
        log.debug("tool start: %s", tool_name)
        self.console.print(f"[yellow]🔧 Executing: {tool_name}[/yellow]")

    def show_tool_result(self, tool_name: str, result: str):
        if not result:
            return
        lines = result.split('\n')
        preview = lines[:3]
        if len(lines) > 3:
            preview.append("...")
        self.console.print(f"[dim]{chr(10).join(preview)}[/dim]")
