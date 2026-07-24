#!/usr/bin/env python3
import sys
import json
import argparse
import traceback
import subprocess
import time
import requests
from ollama_client import OllamaClient
from tools import ToolRegistry
from ui import ChatUI
from logger import get_logger, configure_logging

log = get_logger("main")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="OllamaCode - Agentic Coding Assistant with Ollama"
    )
    parser.add_argument(
        "--model",
        default="huihui_ai/qwen3-abliterated:32b",
        help="Ollama model to use (default: huihui_ai/qwen3-abliterated:32b)"
    )
    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:11434",
        help="Ollama API endpoint (default: http://127.0.0.1:11434)"
    )
    parser.add_argument(
        "--base-dir",
        default=None,
        help="Base directory for file operations (default: ~/Documents)"
    )
    parser.add_argument(
        "--task",
        help="Initial task to execute (if provided, runs autonomously)"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=50,
        help="Maximum agentic loop iterations (default: 50)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Ollama request timeout in seconds (default: 300)"
    )
    parser.add_argument(
        "--allow-outside-base-dir",
        action="store_true",
        help="Allow file operations outside base_dir (default: False)"
    )
    parser.add_argument(
        "--blocked-commands",
        default="rm -rf /,sudo,chmod 777,dd if=,mkfs",
        help="Comma-separated shell commands blocked in run_command"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)"
    )
    parser.add_argument(
        "--log-console",
        action="store_true",
        help="Also log to stderr (default: file only)"
    )
    return parser.parse_args()


def execute_tool_calls(client, tool_registry, tool_calls, ui):
    for tool_call in tool_calls:
        func = tool_call.get("function", {})
        tool_name = func.get("name")
        arguments_json = func.get("arguments", "{}")
        try:
            arguments = json.loads(arguments_json) if isinstance(arguments_json, str) else arguments_json
        except json.JSONDecodeError:
            log.warning("Failed to parse arguments for tool %s: %s", tool_name, arguments_json)
            arguments = {}
        tool_call_id = tool_call.get("id") or f"call_{int(time.time() * 1000)}"
        log.info("Executing tool: %s args=%s", tool_name, arguments)
        ui.show_tool_start(tool_name)
        result = tool_registry.execute_tool(tool_name, arguments)
        log.debug("Tool %s result preview: %s", tool_name, result[:300] if result else "(empty)")
        client.add_tool_message(tool_call_id, result, tool_name)
        ui.show_tool_result(tool_name, result)


def run_agentic_loop(client, tool_registry, ui, max_iterations=50, initial_task=None):
    ui.clear()
    if not client.conversation_history:
        system_message = (
            "You are an autonomous coding assistant. When given a task, you should use the available tools to complete it. "
            "Always use tools when needed - don't just describe what you would do. "
            "Use tools like create_directory, write_file, run_command, etc. to actually perform actions. "
            "Break down complex tasks into steps and use tools for each step."
        )
        client.add_system_message(system_message)

    if initial_task:
        log.info("Starting autonomous task: %s", initial_task)
        ui.print(f"[bold cyan]🚀 Starting autonomous execution:[/bold cyan] {initial_task}")
        current_prompt = initial_task
    else:
        ui.print("[bold cyan]OllamaCode - Agentic Coding Assistant[/bold cyan]")
        ui.print("[dim]Type your task and press Enter. Type 'exit' or 'quit' to exit.[/dim]\n")
        ui.console.print("[bold]Task:[/bold] ", end="")
        current_prompt = input()
        if current_prompt.lower() in ('exit', 'quit', 'q'):
            return
        log.info("User task: %s", current_prompt)

    iteration = 0
    while iteration < max_iterations:
        iteration += 1
        log.info("Iteration %d/%d", iteration, max_iterations)
        tools = tool_registry.get_tool_definitions()
        ui.print(f"\n[dim]🤖 Assistant (iteration {iteration})...[/dim]\n")
        response_text = ""
        tool_calls_buffer = []
        try:
            prompt = current_prompt if iteration == 1 else ""
            chunk_count = 0
            for chunk in client.chat(prompt, tools=tools, stream=True):
                chunk_count += 1
                message = chunk.get("message", {})
                content_delta = message.get("content")
                if content_delta:
                    response_text += content_delta
                    sys.stdout.write(content_delta)
                    sys.stdout.flush()
                tool_calls = message.get("tool_calls")
                if tool_calls:
                    if isinstance(tool_calls, list):
                        for tool_call in tool_calls:
                            tool_id = tool_call.get("id")
                            if tool_id and not any(tc.get("id") == tool_id for tc in tool_calls_buffer):
                                tool_calls_buffer.append(tool_call)
                            elif not tool_id and tool_call not in tool_calls_buffer:
                                tool_calls_buffer.append(tool_call)
                    else:
                        if tool_calls not in tool_calls_buffer:
                            tool_calls_buffer.append(tool_calls)
                if chunk.get("done"):
                    break

            if chunk_count == 0:
                log.error("No chunks received from Ollama")
                ui.print("[bold red]❌ No chunks received from Ollama![/bold red]")
                ui.print("[yellow]This could mean:[/yellow]")
                ui.print("[dim]  - Ollama is not responding (try: ollama serve)[/dim]")
                ui.print(f"[dim]  - The model is not loaded (try: ollama pull {client.model})[/dim]")
                ui.print("[dim]  - Check stderr for detailed error messages[/dim]")
                if not check_ollama_running(client.base_url):
                    ui.print("[bold red]Ollama is not responding![/bold red]")
                break

            log.info("Iteration %d: response=%d chars, tool_calls=%d", iteration, len(response_text), len(tool_calls_buffer))
            client.add_assistant_message(response_text, tool_calls_buffer if tool_calls_buffer else None)

            if response_text:
                ui.print()
                ui.add_message("assistant", response_text)

            if tool_calls_buffer:
                ui.print(f"\n[bold yellow]🔧 Executing {len(tool_calls_buffer)} tool call(s)...[/bold yellow]\n")
                execute_tool_calls(client, tool_registry, tool_calls_buffer, ui)
                current_prompt = ""
                ui.refresh()
            else:
                if not response_text:
                    ui.print("[yellow]⚠️  No response or tool calls received from assistant[/yellow]")
                ui.print("\n[bold green]✅ Task completed![/bold green]")
                log.info("Task completed at iteration %d", iteration)
                break
        except KeyboardInterrupt:
            log.warning("Interrupted by user at iteration %d", iteration)
            ui.print("\n[yellow]⚠️  Interrupted by user[/yellow]")
            break
        except Exception as e:
            log.exception("Error in agentic loop at iteration %d: %s", iteration, e)
            ui.print(f"\n[bold red]❌ Error:[/bold red] {str(e)}")
            ui.print(f"[dim]{traceback.format_exc()}[/dim]")
            break

    if iteration == max_iterations:
        log.warning("Reached max_iterations=%d", max_iterations)
        ui.print(f"\n[yellow]⚠️  Reached maximum iterations ({max_iterations})[/yellow]")


def check_ollama_running(endpoint="http://127.0.0.1:11434"):
    try:
        response = requests.get(f"{endpoint}/api/tags", timeout=2)
        return response.status_code == 200
    except requests.RequestException as e:
        log.debug("Ollama check failed: %s", e)
        return False


def start_ollama(ui, endpoint):
    if check_ollama_running(endpoint):
        return True
    log.info("Ollama not running, attempting to start")
    ui.print("[yellow]⚠️  Ollama is not running. Starting Ollama...[/yellow]")
    try:
        result = subprocess.run(
            ["which", "ollama"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            log.error("'ollama' command not found")
            ui.print("[bold red]❌ Error: 'ollama' command not found![/bold red]")
            ui.print("[dim]Please install Ollama from https://ollama.ai[/dim]")
            return False
        ollama_path = result.stdout.strip()
        ui.print("[dim]Starting Ollama server...[/dim]")
        subprocess.Popen(
            [ollama_path, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        ui.print("[dim]Waiting for Ollama to be ready...[/dim]")
        for i in range(20):
            time.sleep(0.5)
            if check_ollama_running(endpoint):
                log.info("Ollama started successfully")
                ui.print("[green]✅ Ollama is now running![/green]\n")
                return True
            if i % 4 == 0:
                ui.print("[dim].", end="", flush=True)
        ui.print()
        log.warning("Ollama not ready after 10s, continuing anyway")
        ui.print("[yellow]⚠️  Ollama started but may not be ready yet. Continuing anyway...[/yellow]\n")
        return True
    except Exception as e:
        log.exception("Error starting Ollama: %s", e)
        ui.print(f"[bold red]❌ Error starting Ollama: {e}[/bold red]")
        ui.print("[dim]Please start Ollama manually: ollama serve[/dim]")
        return False


def main():
    args = parse_arguments()
    configure_logging(
        level=getattr(logging, args.log_level),
        enable_file=True,
        enable_console=args.log_console
    )
    log.info("Starting OllamaCode | model=%s endpoint=%s base_dir=%s",
             args.model, args.endpoint, args.base_dir or "~/Documents")
    ui = ChatUI()
    ui.print("[dim]Checking Ollama connection...[/dim]")
    if not check_ollama_running(args.endpoint):
        if not start_ollama(ui, args.endpoint):
            log.critical("Cannot start Ollama, exiting")
            ui.print("[bold red]❌ Cannot continue without Ollama. Exiting.[/bold red]")
            sys.exit(1)
        if not check_ollama_running(args.endpoint):
            ui.print("[bold red]❌ Ollama started but not responding. Please check manually.[/bold red]")
            sys.exit(1)
    else:
        ui.print("[green]✅ Ollama is running[/green]\n")

    client = OllamaClient(base_url=args.endpoint, model=args.model, timeout=args.timeout)
    tool_registry = ToolRegistry(
        base_dir=args.base_dir,
        allow_outside_base_dir=args.allow_outside_base_dir,
        blocked_commands=[c.strip() for c in args.blocked_commands.split(',') if c.strip()]
    )

    try:
        if args.task:
            run_agentic_loop(client, tool_registry, ui, max_iterations=args.max_iterations, initial_task=args.task)
        else:
            while True:
                run_agentic_loop(client, tool_registry, ui, max_iterations=args.max_iterations)
                ui.print("\n[dim]Press Enter to continue or type 'exit' to quit...[/dim]")
                user_input = input()
                if user_input.lower() in ('exit', 'quit', 'q'):
                    break
                ui.clear()
    except KeyboardInterrupt:
        ui.print("\n[yellow]👋 Goodbye![/yellow]")
    finally:
        tool_registry.close_browser()
        log.info("OllamaCode shutdown complete")


if __name__ == "__main__":
    main()
