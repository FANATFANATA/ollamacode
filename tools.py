import os
import shutil
import subprocess
import time
import inspect
from pathlib import Path
from typing import Dict, Any, Optional, List
from duckduckgo_search import DDGS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from logger import get_logger

try:
    from webdriver_manager.chrome import ChromeDriverManager
    _HAS_WDM = True
except ImportError:
    _HAS_WDM = False

log = get_logger("tools")

_VALID_SELECTORS = {"css", "xpath", "id"}
_BY_MAP = {"css": By.CSS_SELECTOR, "xpath": By.XPATH, "id": By.ID}
_FORBIDDEN_TOOL_NAMES = {"execute_tool", "get_tool_definitions"}


class ToolRegistry:
    def __init__(self, base_dir=None, allow_outside_base_dir=False, blocked_commands=None):
        self.base_dir = Path(base_dir).resolve() if base_dir else (Path.home() / "Documents").resolve()
        self.current_dir = self.base_dir
        self.allow_outside_base_dir = allow_outside_base_dir
        self.blocked_commands = [c.lower() for c in (blocked_commands or [])]
        self.browser: Optional[webdriver.Chrome] = None
        log.info("ToolRegistry init: base_dir=%s allow_outside=%s blocked=%s",
                 self.base_dir, self.allow_outside_base_dir, len(self.blocked_commands))

    def _ensure_absolute_path(self, path: str) -> Path:
        if os.path.isabs(path):
            return Path(path).resolve()
        return (self.current_dir / path).resolve()

    def _validate_path(self, path: str) -> Path:
        full_path = self._ensure_absolute_path(path)
        if self.allow_outside_base_dir:
            return full_path
        try:
            full_path.relative_to(self.base_dir)
        except ValueError:
            log.warning("Path blocked (outside base_dir): %s", path)
            raise PermissionError(f"Path '{path}' is outside base_dir '{self.base_dir}'")
        return full_path

    def _is_command_blocked(self, command: str) -> bool:
        lowered = command.lower()
        for blocked in self.blocked_commands:
            if blocked in lowered:
                return True
        return False

    def _resolve_by(self, by: str):
        if by not in _VALID_SELECTORS:
            raise ValueError(f"Invalid selector type '{by}'. Must be one of: {sorted(_VALID_SELECTORS)}")
        return _BY_MAP[by]

    def read_file(self, filepath: str) -> str:
        try:
            full_path = self._validate_path(filepath)
            if not full_path.exists():
                return f"Error: File '{filepath}' does not exist"
            if not full_path.is_file():
                return f"Error: '{filepath}' is not a file"
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            log.info("read_file: %s (%d chars)", filepath, len(content))
            return f"Successfully read file '{filepath}' ({len(content)} characters)\n\n{content}"
        except PermissionError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            log.exception("read_file error: %s", e)
            return f"Error reading file '{filepath}': {str(e)}"

    def write_file(self, filepath: str, content: str) -> str:
        try:
            full_path = self._validate_path(filepath)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            log.info("write_file: %s (%d chars)", filepath, len(content))
            return f"Successfully wrote {len(content)} characters to '{filepath}'"
        except PermissionError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            log.exception("write_file error: %s", e)
            return f"Error writing file '{filepath}': {str(e)}"

    def create_directory(self, dirpath: str) -> str:
        try:
            full_path = self._validate_path(dirpath)
            full_path.mkdir(parents=True, exist_ok=True)
            log.info("create_directory: %s", dirpath)
            return f"Successfully created directory '{dirpath}'"
        except PermissionError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            log.exception("create_directory error: %s", e)
            return f"Error creating directory '{dirpath}': {str(e)}"

    def list_directory(self, dirpath: str = ".") -> str:
        try:
            full_path = self._validate_path(dirpath)
            if not full_path.exists():
                return f"Error: Directory '{dirpath}' does not exist"
            if not full_path.is_dir():
                return f"Error: '{dirpath}' is not a directory"
            items = []
            for item in sorted(full_path.iterdir()):
                item_type = "DIR" if item.is_dir() else "FILE"
                size = f"{item.stat().st_size} bytes" if item.is_file() else ""
                items.append(f"{item_type:4}  {item.name}  {size}")
            if not items:
                return f"Directory '{dirpath}' is empty"
            log.info("list_directory: %s (%d items)", dirpath, len(items))
            return f"Contents of '{dirpath}':\n" + "\n".join(items)
        except PermissionError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            log.exception("list_directory error: %s", e)
            return f"Error listing directory '{dirpath}': {str(e)}"

    def delete_file(self, filepath: str) -> str:
        try:
            full_path = self._validate_path(filepath)
            if not full_path.exists():
                return f"Error: File '{filepath}' does not exist"
            if full_path.is_dir():
                return f"Error: '{filepath}' is a directory. Use delete_directory instead."
            full_path.unlink()
            log.info("delete_file: %s", filepath)
            return f"Successfully deleted file '{filepath}'"
        except PermissionError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            log.exception("delete_file error: %s", e)
            return f"Error deleting file '{filepath}': {str(e)}"

    def delete_directory(self, dirpath: str, recursive: bool = False) -> str:
        try:
            full_path = self._validate_path(dirpath)
            if not full_path.exists():
                return f"Error: Directory '{dirpath}' does not exist"
            if not full_path.is_dir():
                return f"Error: '{dirpath}' is not a directory"
            if recursive:
                shutil.rmtree(full_path)
                log.info("delete_directory (recursive): %s", dirpath)
                return f"Successfully deleted directory '{dirpath}' and all contents"
            full_path.rmdir()
            log.info("delete_directory: %s", dirpath)
            return f"Successfully deleted empty directory '{dirpath}'"
        except PermissionError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            log.exception("delete_directory error: %s", e)
            return f"Error deleting directory '{dirpath}': {str(e)}"

    def run_command(self, command: str, cwd: Optional[str] = None, timeout: int = 60) -> str:
        try:
            if self._is_command_blocked(command):
                log.warning("Blocked command: %s", command)
                return f"Error: Command blocked by security policy: {command}"
            if cwd:
                try:
                    work_dir = str(self._validate_path(cwd))
                except PermissionError as e:
                    return f"Error: {str(e)}"
            else:
                work_dir = str(self.current_dir)
            stripped = command.strip()
            if stripped.startswith("cd "):
                new_dir = stripped[3:].strip()
                if new_dir == "~":
                    new_dir = str(Path.home())
                elif not os.path.isabs(new_dir):
                    new_dir = str(self.current_dir / new_dir)
                else:
                    new_dir = os.path.expanduser(new_dir)
                if not os.path.isdir(new_dir):
                    return f"Error: Directory '{new_dir}' does not exist"
                new_path = Path(new_dir).resolve()
                if not self.allow_outside_base_dir:
                    try:
                        new_path.relative_to(self.base_dir)
                    except ValueError:
                        log.warning("cd blocked (outside base_dir): %s", new_dir)
                        return f"Error: Directory '{new_dir}' is outside base_dir '{self.base_dir}'"
                self.current_dir = new_path
                log.info("cd -> %s", self.current_dir)
                return f"Changed directory to: {self.current_dir}"
            log.info("run_command: %s (cwd=%s timeout=%d)", command, work_dir, timeout)
            result = subprocess.run(
                command,
                shell=True,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            output = result.stdout + result.stderr
            if result.returncode != 0:
                log.warning("command exit=%d: %s", result.returncode, command)
                return f"Command exited with code {result.returncode}:\n{output}"
            return output if output else "Command executed successfully (no output)"
        except subprocess.TimeoutExpired:
            log.warning("command timeout (%ds): %s", timeout, command)
            return f"Error: Command timed out after {timeout} seconds"
        except PermissionError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            log.exception("run_command error: %s", e)
            return f"Error executing command: {str(e)}"

    def web_search(self, query: str, max_results: int = 5, retries: int = 3) -> str:
        last_error = None
        log.info("web_search: query=%s max_results=%d retries=%d", query, max_results, retries)
        for attempt in range(retries):
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
                last_error = e
                log.warning("web_search attempt %d failed: %s", attempt + 1, e)
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        log.error("web_search exhausted retries: %s", last_error)
        return f"Error performing web search after {retries} attempts: {str(last_error)}"

    def open_browser(self, headless: bool = False) -> str:
        try:
            if self.browser:
                return "Browser is already open"
            options = Options()
            if headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            if _HAS_WDM:
                try:
                    service = Service(ChromeDriverManager().install())
                    self.browser = webdriver.Chrome(service=service, options=options)
                    log.info("Browser opened via webdriver-manager (headless=%s)", headless)
                    return "Browser opened successfully"
                except Exception as e:
                    log.warning("webdriver-manager failed, fallback to system chromedriver: %s", e)
            self.browser = webdriver.Chrome(options=options)
            log.info("Browser opened via system chromedriver (headless=%s)", headless)
            return "Browser opened successfully"
        except Exception as e:
            log.exception("open_browser error: %s", e)
            return f"Error opening browser: {str(e)}"

    def navigate_to(self, url: str) -> str:
        try:
            if not self.browser:
                return "Error: Browser is not open. Call open_browser first."
            self.browser.get(url)
            time.sleep(2)
            title = self.browser.title
            log.info("navigate_to: %s (title=%s)", url, title)
            return f"Navigated to {url}\nPage title: {title}"
        except Exception as e:
            log.exception("navigate_to error: %s", e)
            return f"Error navigating to URL: {str(e)}"

    def browser_click(self, selector: str, by: str = "css") -> str:
        try:
            if not self.browser:
                return "Error: Browser is not open."
            by_method = self._resolve_by(by)
            element = WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((by_method, selector))
            )
            element.click()
            log.info("browser_click: %s (by=%s)", selector, by)
            return f"Successfully clicked element: {selector}"
        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            log.exception("browser_click error: %s", e)
            return f"Error clicking element: {str(e)}"

    def browser_type(self, selector: str, text: str, by: str = "css") -> str:
        try:
            if not self.browser:
                return "Error: Browser is not open."
            by_method = self._resolve_by(by)
            element = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((by_method, selector))
            )
            element.clear()
            element.send_keys(text)
            log.info("browser_type: %s (len=%d)", selector, len(text))
            return f"Successfully typed text into {selector}"
        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            log.exception("browser_type error: %s", e)
            return f"Error typing into element: {str(e)}"

    def browser_get_text(self, selector: str, by: str = "css") -> str:
        try:
            if not self.browser:
                return "Error: Browser is not open."
            by_method = self._resolve_by(by)
            element = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((by_method, selector))
            )
            text = element.text
            log.info("browser_get_text: %s (len=%d)", selector, len(text))
            return f"Text from {selector}:\n{text}"
        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            log.exception("browser_get_text error: %s", e)
            return f"Error getting text from element: {str(e)}"

    def browser_get_html(self, max_length: int = 5000) -> str:
        try:
            if not self.browser:
                return "Error: Browser is not open."
            html = self.browser.page_source
            if len(html) > max_length:
                log.info("browser_get_html: %d chars (truncated to %d)", len(html), max_length)
                return f"Page HTML ({len(html)} characters, truncated to {max_length}):\n{html[:max_length]}..."
            log.info("browser_get_html: %d chars", len(html))
            return f"Page HTML ({len(html)} characters):\n{html}"
        except Exception as e:
            log.exception("browser_get_html error: %s", e)
            return f"Error getting page HTML: {str(e)}"

    def close_browser(self) -> str:
        try:
            if self.browser:
                self.browser.quit()
                self.browser = None
                log.info("Browser closed")
                return "Browser closed successfully"
            return "No browser to close"
        except Exception as e:
            log.exception("close_browser error: %s", e)
            return f"Error closing browser: {str(e)}"

    def get_tool_definitions(self) -> List[Dict]:
        return [
            {"type": "function", "function": {"name": "read_file", "description": "Read the contents of a file", "parameters": {"type": "object", "properties": {"filepath": {"type": "string", "description": "Path to the file to read (relative or absolute)"}}, "required": ["filepath"]}}},
            {"type": "function", "function": {"name": "write_file", "description": "Write content to a file, creating parent directories if needed", "parameters": {"type": "object", "properties": {"filepath": {"type": "string", "description": "Path to the file to write (relative or absolute)"}, "content": {"type": "string", "description": "Content to write to the file"}}, "required": ["filepath", "content"]}}},
            {"type": "function", "function": {"name": "create_directory", "description": "Create a directory and any necessary parent directories", "parameters": {"type": "object", "properties": {"dirpath": {"type": "string", "description": "Path to the directory to create (relative or absolute)"}}, "required": ["dirpath"]}}},
            {"type": "function", "function": {"name": "list_directory", "description": "List contents of a directory", "parameters": {"type": "object", "properties": {"dirpath": {"type": "string", "description": "Directory path (default: current directory)"}}, "required": []}}},
            {"type": "function", "function": {"name": "delete_file", "description": "Delete a file", "parameters": {"type": "object", "properties": {"filepath": {"type": "string", "description": "Path to the file to delete"}}, "required": ["filepath"]}}},
            {"type": "function", "function": {"name": "delete_directory", "description": "Delete a directory (optionally recursively)", "parameters": {"type": "object", "properties": {"dirpath": {"type": "string", "description": "Path to the directory to delete"}, "recursive": {"type": "boolean", "description": "Whether to delete recursively (default: false)"}}, "required": ["dirpath"]}}},
            {"type": "function", "function": {"name": "run_command", "description": "Execute a shell command. cd changes the working directory for subsequent commands.", "parameters": {"type": "object", "properties": {"command": {"type": "string", "description": "The shell command to execute"}, "cwd": {"type": "string", "description": "Working directory (optional, defaults to current)"}, "timeout": {"type": "integer", "description": "Timeout in seconds (default: 60)"}}, "required": ["command"]}}},
            {"type": "function", "function": {"name": "web_search", "description": "Search the web using DuckDuckGo", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}, "max_results": {"type": "integer", "description": "Maximum number of results (default: 5)"}, "retries": {"type": "integer", "description": "Number of retry attempts (default: 3)"}}, "required": ["query"]}}},
            {"type": "function", "function": {"name": "open_browser", "description": "Open a Chrome browser instance", "parameters": {"type": "object", "properties": {"headless": {"type": "boolean", "description": "Run in headless mode (default: false)"}}, "required": []}}},
            {"type": "function", "function": {"name": "navigate_to", "description": "Navigate browser to a URL", "parameters": {"type": "object", "properties": {"url": {"type": "string", "description": "URL to navigate to"}}, "required": ["url"]}}},
            {"type": "function", "function": {"name": "browser_click", "description": "Click an element on the current page", "parameters": {"type": "object", "properties": {"selector": {"type": "string", "description": "CSS selector, XPath, or ID"}, "by": {"type": "string", "description": "Selector type: 'css', 'xpath', or 'id' (default: 'css')"}}, "required": ["selector"]}}},
            {"type": "function", "function": {"name": "browser_type", "description": "Type text into an input field", "parameters": {"type": "object", "properties": {"selector": {"type": "string", "description": "CSS selector, XPath, or ID"}, "text": {"type": "string", "description": "Text to type"}, "by": {"type": "string", "description": "Selector type: 'css', 'xpath', or 'id' (default: 'css')"}}, "required": ["selector", "text"]}}},
            {"type": "function", "function": {"name": "browser_get_text", "description": "Get text content from an element", "parameters": {"type": "object", "properties": {"selector": {"type": "string", "description": "CSS selector, XPath, or ID"}, "by": {"type": "string", "description": "Selector type: 'css', 'xpath', or 'id' (default: 'css')"}}, "required": ["selector"]}}},
            {"type": "function", "function": {"name": "browser_get_html", "description": "Get HTML source of the current page", "parameters": {"type": "object", "properties": {"max_length": {"type": "integer", "description": "Maximum HTML length to return (default: 5000)"}}, "required": []}}},
            {"type": "function", "function": {"name": "close_browser", "description": "Close the browser", "parameters": {"type": "object", "properties": {}, "required": []}}},
        ]

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        if not isinstance(tool_name, str) or not tool_name or tool_name.startswith('_') or tool_name in _FORBIDDEN_TOOL_NAMES:
            log.warning("execute_tool blocked: %s", tool_name)
            return f"Error: Unknown tool '{tool_name}'"
        method = getattr(self, tool_name, None)
        if not method or not callable(method):
            log.warning("execute_tool unknown tool: %s", tool_name)
            return f"Error: Unknown tool '{tool_name}'"
        try:
            sig = inspect.signature(method)
            valid_params = set(sig.parameters.keys())
            filtered_args = {k: v for k, v in arguments.items() if k in valid_params}
            return method(**filtered_args)
        except Exception as e:
            log.exception("execute_tool '%s' error: %s", tool_name, e)
            return f"Error executing tool '{tool_name}': {str(e)}"
