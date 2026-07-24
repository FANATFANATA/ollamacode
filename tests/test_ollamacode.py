import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def registry(tmp_path):
    from tools import ToolRegistry
    return ToolRegistry(base_dir=str(tmp_path), blocked_commands=["rm -rf /", "sudo", "mkfs"])


@pytest.fixture
def client():
    from ollama_client import OllamaClient
    return OllamaClient(base_url="http://127.0.0.1:99999", model="test-model", timeout=5)


@pytest.fixture
def ui():
    from ui import ChatUI
    return ChatUI()


def test_write_and_read_file(registry):
    result = registry.write_file("test.txt", "hello world")
    assert "Successfully wrote" in result
    result = registry.read_file("test.txt")
    assert "hello world" in result


def test_write_file_creates_parent_dirs(registry):
    result = registry.write_file("sub/dir/file.txt", "nested")
    assert "Successfully wrote" in result
    result = registry.read_file("sub/dir/file.txt")
    assert "nested" in result


def test_read_nonexistent_file(registry):
    result = registry.read_file("nope.txt")
    assert "does not exist" in result


def test_create_and_list_directory(registry):
    registry.create_directory("mydir")
    registry.write_file("mydir/a.txt", "a")
    registry.write_file("mydir/b.txt", "b")
    result = registry.list_directory("mydir")
    assert "a.txt" in result
    assert "b.txt" in result


def test_list_empty_directory(registry):
    registry.create_directory("emptydir")
    result = registry.list_directory("emptydir")
    assert "empty" in result.lower()


def test_delete_file(registry):
    registry.write_file("todelete.txt", "x")
    result = registry.delete_file("todelete.txt")
    assert "Successfully deleted" in result
    result = registry.read_file("todelete.txt")
    assert "does not exist" in result


def test_delete_file_nonexistent(registry):
    result = registry.delete_file("ghost.txt")
    assert "does not exist" in result


def test_delete_directory_non_recursive(registry):
    registry.create_directory("d")
    result = registry.delete_directory("d")
    assert "Successfully deleted" in result


def test_delete_directory_recursive(registry):
    registry.create_directory("d")
    registry.write_file("d/file.txt", "data")
    result = registry.delete_directory("d", recursive=True)
    assert "Successfully deleted" in result


def test_path_traversal_blocked(registry):
    result = registry.write_file("../../escape.txt", "evil")
    assert "outside base_dir" in result or "Error" in result


def test_path_traversal_read_blocked(registry):
    result = registry.read_file("/etc/passwd")
    assert "outside base_dir" in result or "Error" in result


def test_blocked_command(registry):
    result = registry.run_command("rm -rf /")
    assert "blocked" in result.lower()


def test_blocked_sudo(registry):
    result = registry.run_command("sudo rm something")
    assert "blocked" in result.lower()


def test_run_command_echo(registry):
    result = registry.run_command("echo test123")
    assert "test123" in result


def test_run_command_timeout(registry):
    result = registry.run_command("sleep 5", timeout=1)
    assert "timed out" in result.lower()


def test_cd_changes_directory(registry):
    registry.create_directory("newdir")
    result = registry.run_command("cd newdir")
    assert "Changed directory" in result
    assert registry.current_dir.name == "newdir"


def test_cd_blocked_outside_base(registry):
    result = registry.run_command("cd /")
    assert "outside base_dir" in result or "Error" in result


def test_invalid_selector_raises(registry):
    result = registry.browser_click("div", by="invalid")
    assert "Error" in result


def test_execute_tool_unknown(registry):
    result = registry.execute_tool("nonexistent_tool", {})
    assert "Unknown tool" in result


def test_execute_tool_private_blocked(registry):
    result = registry.execute_tool("_validate_path", {"path": "."})
    assert "Unknown tool" in result


def test_execute_tool_filters_unknown_args(registry):
    result = registry.execute_tool("write_file", {"filepath": "x.txt", "content": "data", "bogus_arg": "junk"})
    assert "Successfully wrote" in result


def test_tool_definitions_structure(registry):
    defs = registry.get_tool_definitions()
    assert isinstance(defs, list)
    assert len(defs) >= 14
    for d in defs:
        assert d["type"] == "function"
        assert "name" in d["function"]
        assert "parameters" in d["function"]


def test_client_init_defaults(client):
    assert client.base_url == "http://127.0.0.1:99999"
    assert client.model == "test-model"
    assert client.timeout == 5
    assert client.conversation_history == []


def test_client_add_system_message(client):
    client.add_system_message("be helpful")
    assert len(client.conversation_history) == 1
    assert client.conversation_history[0]["role"] == "system"


def test_client_add_user_message(client):
    client.add_user_message("hello")
    assert client.conversation_history[-1] == {"role": "user", "content": "hello"}


def test_client_add_assistant_message_with_tool_calls(client):
    tool_calls = [{"id": "call_1", "function": {"name": "test", "arguments": "{}"}}]
    client.add_assistant_message("text", tool_calls=tool_calls)
    msg = client.conversation_history[-1]
    assert msg["role"] == "assistant"
    assert msg["tool_calls"] == tool_calls


def test_client_add_tool_message_generates_id(client):
    client.add_tool_message("", "result", "test_tool")
    msg = client.conversation_history[-1]
    assert msg["role"] == "tool"
    assert msg["tool_call_id"].startswith("call_")
    assert msg["name"] == "test_tool"


def test_client_history_trim(client):
    client.max_history = 5
    for i in range(10):
        client.add_user_message(f"msg-{i}")
    assert len(client.conversation_history) <= 5


def test_ui_add_message(ui):
    ui.add_message("user", "hello")
    assert len(ui.messages) == 1
    assert ui.messages[0] == {"role": "user", "content": "hello"}


def test_ui_truncate_short():
    from ui import ChatUI
    u = ChatUI()
    assert u._truncate("short", 100) == "short"


def test_ui_truncate_long():
    from ui import ChatUI
    u = ChatUI()
    result = u._truncate("a" * 200, 100)
    assert result.endswith("...")
    assert len(result) == 103


def test_ui_render_user_message():
    from ui import ChatUI
    u = ChatUI()
    out = u.render_message({"role": "user", "content": "hi"})
    assert "You:" in out
    assert "hi" in out


def test_ui_render_assistant_message():
    from ui import ChatUI
    u = ChatUI()
    out = u.render_message({"role": "assistant", "content": "response"})
    assert "Assistant:" in out


def test_ui_render_tool_message_truncated():
    from ui import ChatUI
    u = ChatUI()
    long_content = "x" * 500
    out = u.render_message({"role": "tool", "name": "test", "content": long_content})
    assert "..." in out
    assert "test" in out


def test_logger_get_logger():
    from logger import get_logger
    log = get_logger("test")
    assert log.name == "ollamacode.test"


def test_logger_configure_idempotent():
    from logger import configure_logging, _configured
    import logger as L
    initial = L._configured
    configure_logging()
    assert L._configured == initial
