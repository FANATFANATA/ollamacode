"""Terminal UI for the agentic coding assistant."""
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich import box
from typing import List, Optional
import time


class ChatUI:
    """Terminal chat interface for the agent."""
    
    def __init__(self):
        self.console = Console()
        self.messages: List[dict] = []
        self.current_response = ""
        
    def add_message(self, role: str, content: str):
        """Add a message to the chat."""
        self.messages.append({"role": role, "content": content})
        
    def update_response(self, text: str):
        """Update the current streaming response."""
        self.current_response = text
        
    def clear_response(self):
        """Clear the current response."""
        self.current_response = ""
        
    def render_message(self, message: dict) -> str:
        """Render a single message."""
        role = message.get("role", "unknown")
        content = message.get("content", "")
        
        # Handle different content types
        if not isinstance(content, str):
            content = str(content)
        
        if role == "user":
            return f"[bold blue]You:[/bold blue] {content}"
        elif role == "assistant":
            return f"[bold green]Assistant:[/bold green]\n{content}"
        elif role == "tool":
            # Truncate content for display
            content_str = content[:200] + "..." if len(content) > 200 else content
            return f"[dim]Tool ({message.get('name', 'unknown')}): {content_str}[/dim]"
        else:
            return f"[{role}]: {content}"
    
    def render_chat(self) -> Panel:
        """Render the entire chat."""
        content_lines = []
        
        # Render all messages
        for msg in self.messages:
            content_lines.append(self.render_message(msg))
            content_lines.append("")  # Empty line between messages
        
        # Add current streaming response
        if self.current_response:
            content_lines.append(f"[bold green]Assistant:[/bold green]")
            content_lines.append(self.current_response)
        
        content = "\n".join(content_lines)
        return Panel(
            content,
            title="[bold cyan]OllamaCode - Agentic Coding Assistant[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED
        )
    
    def print(self, *args, **kwargs):
        """Print to console."""
        self.console.print(*args, **kwargs)
    
    def clear(self):
        """Clear the console."""
        self.console.clear()
        
    def refresh(self):
        """Refresh the display."""
        chat_panel = self.render_chat()
        self.console.clear()
        self.console.print(chat_panel)
        
    def show_thinking(self, message: str = "Thinking..."):
        """Show thinking indicator."""
        self.console.print(f"[dim italic]{message}[/dim italic]")
        
    def show_tool_execution(self, tool_name: str, result: str):
        """Show tool execution result."""
        self.console.print(f"[yellow]🔧 Executing: {tool_name}[/yellow]")
        # Show first few lines of result
        preview = result.split('\n')[:3]
        if len(result.split('\n')) > 3:
            preview.append("...")
        self.console.print(f"[dim]{' '.join(preview)}[/dim]")

