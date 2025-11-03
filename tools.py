"""Tool implementations for the agentic coding assistant."""
import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from duckduckgo_search import DDGS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


class ToolRegistry:
    """Registry and executor for all available tools."""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents"
        self.current_dir = self.base_dir
        self.browser: Optional[webdriver.Chrome] = None
        
    def _ensure_absolute_path(self, path: str) -> Path:
        """Convert relative path to absolute based on current_dir."""
        if os.path.isabs(path):
            return Path(path)
        return self.current_dir / path
    
    def read_file(self, filepath: str) -> str:
        """Read contents of a file."""
        try:
            full_path = self._ensure_absolute_path(filepath)
            if not full_path.exists():
                return f"Error: File '{filepath}' does not exist"
            if not full_path.is_file():
                return f"Error: '{filepath}' is not a file"
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"Successfully read file '{filepath}' ({len(content)} characters)\n\n{content}"
        except Exception as e:
            return f"Error reading file '{filepath}': {str(e)}"
    
    def write_file(self, filepath: str, content: str) -> str:
        """Write content to a file, creating parent directories if needed."""
        try:
            full_path = self._ensure_absolute_path(filepath)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote {len(content)} characters to '{filepath}'"
        except Exception as e:
            return f"Error writing file '{filepath}': {str(e)}"
    
    def create_directory(self, dirpath: str) -> str:
        """Create a directory and any necessary parent directories."""
        try:
            full_path = self._ensure_absolute_path(dirpath)
            full_path.mkdir(parents=True, exist_ok=True)
            return f"Successfully created directory '{dirpath}'"
        except Exception as e:
            return f"Error creating directory '{dirpath}': {str(e)}"
    
    def list_directory(self, dirpath: str = ".") -> str:
        """List contents of a directory."""
        try:
            full_path = self._ensure_absolute_path(dirpath)
            if not full_path.exists():
                return f"Error: Directory '{dirpath}' does not exist"
            if not full_path.is_dir():
                return f"Error: '{dirpath}' is not a directory"
            
            items = []
            for item in sorted(full_path.iterdir()):
                item_type = "DIR" if item.is_dir() else "FILE"
                size = f"{item.stat().st_size} bytes" if item.is_file() else ""
                items.append(f"{item_type:4}  {item.name}  {size}")
            
            return f"Contents of '{dirpath}':\n" + "\n".join(items) if items else f"Directory '{dirpath}' is empty"
        except Exception as e:
            return f"Error listing directory '{dirpath}': {str(e)}"
    
    def delete_file(self, filepath: str) -> str:
        """Delete a file."""
        try:
            full_path = self._ensure_absolute_path(filepath)
            if not full_path.exists():
                return f"Error: File '{filepath}' does not exist"
            if full_path.is_dir():
                return f"Error: '{filepath}' is a directory. Use delete_directory instead."
            
            full_path.unlink()
            return f"Successfully deleted file '{filepath}'"
        except Exception as e:
            return f"Error deleting file '{filepath}': {str(e)}"
    
    def delete_directory(self, dirpath: str, recursive: bool = False) -> str:
        """Delete a directory."""
        try:
            full_path = self._ensure_absolute_path(dirpath)
            if not full_path.exists():
                return f"Error: Directory '{dirpath}' does not exist"
            if not full_path.is_dir():
                return f"Error: '{dirpath}' is not a directory"
            
            if recursive:
                import shutil
                shutil.rmtree(full_path)
                return f"Successfully deleted directory '{dirpath}' and all contents"
            else:
                full_path.rmdir()
                return f"Successfully deleted empty directory '{dirpath}'"
        except Exception as e:
            return f"Error deleting directory '{dirpath}': {str(e)}"
    
    def run_command(self, command: str, cwd: Optional[str] = None) -> str:
        """Execute a shell command."""
        try:
            work_dir = str(self._ensure_absolute_path(cwd)) if cwd else str(self.current_dir)
            
            # Change directory if needed
            if command.strip().startswith("cd "):
                new_dir = command.strip()[3:].strip()
                if new_dir == "~":
                    new_dir = str(Path.home())
                elif not os.path.isabs(new_dir):
                    new_dir = str(self.current_dir / new_dir)
                else:
                    new_dir = os.path.expanduser(new_dir)
                
                if os.path.isdir(new_dir):
                    self.current_dir = Path(new_dir).resolve()
                    return f"Changed directory to: {self.current_dir}"
                else:
                    return f"Error: Directory '{new_dir}' does not exist"
            
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            output = result.stdout + result.stderr
            if result.returncode != 0:
                return f"Command exited with code {result.returncode}:\n{output}"
            return output if output else "Command executed successfully (no output)"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 60 seconds"
        except Exception as e:
            return f"Error executing command: {str(e)}"
    
    def web_search(self, query: str, max_results: int = 5) -> str:
        """Search the web using DuckDuckGo."""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                
                if not results:
                    return f"No results found for query: {query}"
                
                formatted_results = []
                for i, result in enumerate(results, 1):
                    formatted_results.append(
                        f"{i}. {result.get('title', 'No title')}\n"
                        f"   URL: {result.get('href', 'No URL')}\n"
                        f"   {result.get('body', 'No description')}"
                    )
                
                return f"Web search results for '{query}':\n\n" + "\n\n".join(formatted_results)
        except Exception as e:
            return f"Error performing web search: {str(e)}"
    
    def open_browser(self, headless: bool = False) -> str:
        """Open a Chrome browser instance."""
        try:
            if self.browser:
                return "Browser is already open"
            
            options = Options()
            if headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            
            self.browser = webdriver.Chrome(options=options)
            return "Browser opened successfully"
        except Exception as e:
            return f"Error opening browser: {str(e)}"
    
    def navigate_to(self, url: str) -> str:
        """Navigate browser to a URL."""
        try:
            if not self.browser:
                return "Error: Browser is not open. Call open_browser first."
            
            self.browser.get(url)
            time.sleep(2)  # Wait for page to load
            title = self.browser.title
            return f"Navigated to {url}\nPage title: {title}"
        except Exception as e:
            return f"Error navigating to URL: {str(e)}"
    
    def browser_click(self, selector: str, by: str = "css") -> str:
        """Click an element on the current page."""
        try:
            if not self.browser:
                return "Error: Browser is not open."
            
            by_method = By.CSS_SELECTOR if by == "css" else By.XPATH if by == "xpath" else By.ID
            element = WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((by_method, selector))
            )
            element.click()
            return f"Successfully clicked element: {selector}"
        except Exception as e:
            return f"Error clicking element: {str(e)}"
    
    def browser_type(self, selector: str, text: str, by: str = "css") -> str:
        """Type text into an input field."""
        try:
            if not self.browser:
                return "Error: Browser is not open."
            
            by_method = By.CSS_SELECTOR if by == "css" else By.XPATH if by == "xpath" else By.ID
            element = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((by_method, selector))
            )
            element.clear()
            element.send_keys(text)
            return f"Successfully typed text into {selector}"
        except Exception as e:
            return f"Error typing into element: {str(e)}"
    
    def browser_get_text(self, selector: str, by: str = "css") -> str:
        """Get text content from an element."""
        try:
            if not self.browser:
                return "Error: Browser is not open."
            
            by_method = By.CSS_SELECTOR if by == "css" else By.XPATH if by == "xpath" else By.ID
            element = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((by_method, selector))
            )
            text = element.text
            return f"Text from {selector}:\n{text}"
        except Exception as e:
            return f"Error getting text from element: {str(e)}"
    
    def browser_get_html(self) -> str:
        """Get HTML source of current page."""
        try:
            if not self.browser:
                return "Error: Browser is not open."
            
            html = self.browser.page_source
            return f"Page HTML ({len(html)} characters):\n{html[:5000]}..." if len(html) > 5000 else html
        except Exception as e:
            return f"Error getting page HTML: {str(e)}"
    
    def close_browser(self) -> str:
        """Close the browser."""
        try:
            if self.browser:
                self.browser.quit()
                self.browser = None
                return "Browser closed successfully"
            return "No browser to close"
        except Exception as e:
            return f"Error closing browser: {str(e)}"
    
    def get_tool_definitions(self) -> List[Dict]:
        """Get tool definitions for Ollama."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "Path to the file to read (relative or absolute)"}
                        },
                        "required": ["filepath"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file, creating parent directories if needed",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "Path to the file to write (relative or absolute)"},
                            "content": {"type": "string", "description": "Content to write to the file"}
                        },
                        "required": ["filepath", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_directory",
                    "description": "Create a directory and any necessary parent directories",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "dirpath": {"type": "string", "description": "Path to the directory to create (relative or absolute)"}
                        },
                        "required": ["dirpath"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "List contents of a directory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "dirpath": {"type": "string", "description": "Directory path (default: current directory)"}
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_file",
                    "description": "Delete a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "Path to the file to delete"}
                        },
                        "required": ["filepath"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_directory",
                    "description": "Delete a directory (optionally recursively)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "dirpath": {"type": "string", "description": "Path to the directory to delete"},
                            "recursive": {"type": "boolean", "description": "Whether to delete recursively (default: false)"}
                        },
                        "required": ["dirpath"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "run_command",
                    "description": "Execute a shell command (cd, ls, cat, git, npm, etc.). Note: cd changes the working directory for subsequent commands.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "The shell command to execute"},
                            "cwd": {"type": "string", "description": "Working directory (optional, defaults to current)"}
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web using DuckDuckGo",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "max_results": {"type": "integer", "description": "Maximum number of results (default: 5)"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "open_browser",
                    "description": "Open a Chrome browser instance",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "headless": {"type": "boolean", "description": "Run in headless mode (default: false)"}
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "navigate_to",
                    "description": "Navigate browser to a URL",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to navigate to"}
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "browser_click",
                    "description": "Click an element on the current page",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector, XPath, or ID"},
                            "by": {"type": "string", "description": "Selector type: 'css', 'xpath', or 'id' (default: 'css')"}
                        },
                        "required": ["selector"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "browser_type",
                    "description": "Type text into an input field",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector, XPath, or ID"},
                            "text": {"type": "string", "description": "Text to type"},
                            "by": {"type": "string", "description": "Selector type: 'css', 'xpath', or 'id' (default: 'css')"}
                        },
                        "required": ["selector", "text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "browser_get_text",
                    "description": "Get text content from an element",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector, XPath, or ID"},
                            "by": {"type": "string", "description": "Selector type: 'css', 'xpath', or 'id' (default: 'css')"}
                        },
                        "required": ["selector"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "browser_get_html",
                    "description": "Get HTML source of the current page",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "close_browser",
                    "description": "Close the browser",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
        ]
    
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool by name with given arguments."""
        method = getattr(self, tool_name, None)
        if not method:
            return f"Error: Unknown tool '{tool_name}'"
        
        try:
            return method(**arguments)
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"

