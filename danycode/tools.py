from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file at the given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file, creating it if it does not exist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit a file by replacing an exact search string with a replacement string. The search string must be unique in the file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to edit"},
                    "search": {"type": "string", "description": "Exact string to find"},
                    "replace": {"type": "string", "description": "Replacement string"},
                },
                "required": ["path", "search", "replace"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories at the given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Search for a regex pattern in files using grep.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory or file to search in",
                    },
                    "include": {
                        "type": "string",
                        "description": "File glob filter, e.g. *.py",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command and return stdout, stderr, return code and current working directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_user",
            "description": "Ask the user a question and wait for their response.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Question to ask the user",
                    }
                },
                "required": ["question"],
            },
        },
    },
]


def execute_tool(name: str, arguments: dict, ask_fn=None) -> str:
    if name == "read_file":
        return _read_file(arguments["path"])
    elif name == "write_file":
        return _write_file(arguments["path"], arguments["content"])
    elif name == "edit_file":
        return _edit_file(arguments["path"], arguments["search"], arguments["replace"])
    elif name == "list_dir":
        return _list_dir(arguments["path"])
    elif name == "search":
        return _search(
            arguments["pattern"], arguments.get("path", "."), arguments.get("include")
        )
    elif name == "run_command":
        return _run_command(arguments["command"])
    elif name == "ask_user":
        if ask_fn:
            return ask_fn(arguments.get("question", ""))
        return json.dumps({"error": "No ask function provided"})
    return json.dumps({"error": f"Unknown tool: {name}"})


def _read_file(path: str) -> str:
    try:
        p = Path(path)
        if not p.exists():
            return json.dumps({"error": f"File not found: {path}"})
        content = p.read_text(encoding="utf-8")
        return json.dumps({"content": content})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _write_file(path: str, content: str) -> str:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return json.dumps({"status": "ok", "path": str(p.resolve())})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _edit_file(path: str, search: str, replace: str) -> str:
    try:
        p = Path(path)
        if not p.exists():
            return json.dumps({"error": f"File not found: {path}"})
        content = p.read_text(encoding="utf-8")
        if search not in content:
            return json.dumps({"error": "Search string not found in file"})
        count = content.count(search)
        if count > 1:
            return json.dumps(
                {"error": f"Search string found {count} times, must be unique"}
            )
        new_content = content.replace(search, replace, 1)
        p.write_text(new_content, encoding="utf-8")
        return json.dumps({"status": "ok", "path": str(p.resolve())})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _list_dir(path: str) -> str:
    try:
        p = Path(path)
        if not p.exists():
            return json.dumps({"error": f"Path not found: {path}"})
        entries = []
        for item in sorted(p.iterdir()):
            entry_type = "dir" if item.is_dir() else "file"
            entries.append({"name": item.name, "type": entry_type})
        return json.dumps({"entries": entries, "cwd": os.getcwd()})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _search(pattern: str, path: str, include: str | None) -> str:
    try:
        cmd = ["grep", "-rn", "--color=never"]
        if include:
            cmd.extend(["--include", include])
        cmd.extend([pattern, path])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout.strip()
        if not output:
            return json.dumps({"results": []})
        lines = output.split("\n")[:100]
        return json.dumps({"results": lines})
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Search timed out"})
    except FileNotFoundError:
        try:
            cmd = ["findstr", "/s", "/n", pattern, path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            output = result.stdout.strip()
            if not output:
                return json.dumps({"results": []})
            lines = output.split("\n")[:100]
            return json.dumps({"results": lines})
        except Exception as e:
            return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _run_command(command: str) -> str:
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=120
        )
        return json.dumps(
            {
                "stdout": result.stdout[-10000:],
                "stderr": result.stderr[-5000:],
                "returncode": result.returncode,
                "cwd": os.getcwd(),
            }
        )
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Command timed out (120s)"})
    except Exception as e:
        return json.dumps({"error": str(e)})
