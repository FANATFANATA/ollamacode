#!/usr/bin/env python3
"""Main entry point for OllamaCode - Agentic Coding Assistant."""
import sys
import json
import argparse
import traceback
import subprocess
import time
import requests
from pathlib import Path
from ollama_client import OllamaClient
from tools import ToolRegistry
from ui import ChatUI


def parse_arguments():
    """Parse command line arguments."""
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
    return parser.parse_args()


def execute_tool_calls(client: OllamaClient, tool_registry: ToolRegistry, tool_calls: list, ui: ChatUI):
    """Execute tool calls and add results to conversation."""
    for tool_call in tool_calls:
        func = tool_call.get("function", {})
        tool_name = func.get("name")
        arguments_json = func.get("arguments", "{}")
        
        try:
            arguments = json.loads(arguments_json) if isinstance(arguments_json, str) else arguments_json
        except json.JSONDecodeError:
            arguments = {}
        
        # Execute tool
        ui.print(f"[yellow]🔧 Executing: {tool_name}[/yellow]")
        result = tool_registry.execute_tool(tool_name, arguments)
        
        # Add tool result to conversation
        client.add_tool_message(
            tool_call.get("id", ""),
            result,
            tool_name
        )
        
        # Show result preview
        preview_lines = result.split('\n')[:2]
        if len(result.split('\n')) > 2:
            preview_lines.append("...")
        ui.print(f"[dim]{' '.join(preview_lines)}[/dim]")
        ui.add_message("tool", {"role": "tool", "name": tool_name, "content": result})


def run_agentic_loop(client: OllamaClient, tool_registry: ToolRegistry, ui: ChatUI, initial_task: str = None):
    """Run the autonomous agentic loop."""
    ui.clear()
    
    # Add system message to encourage tool use (only on first iteration)
    if not client.conversation_history:
        system_message = """You are an autonomous coding assistant. When given a task, you should use the available tools to complete it. 
Always use tools when needed - don't just describe what you would do. Use tools like create_directory, write_file, run_command, etc. to actually perform actions.
Break down complex tasks into steps and use tools for each step."""
        client.conversation_history.append({"role": "system", "content": system_message})
    
    if initial_task:
        # Autonomous mode - execute the task
        ui.print(f"[bold cyan]🚀 Starting autonomous execution:[/bold cyan] {initial_task}")
        ui.add_message("user", initial_task)
        current_prompt = initial_task
    else:
        # Interactive mode
        ui.print("[bold cyan]OllamaCode - Agentic Coding Assistant[/bold cyan]")
        ui.print("[dim]Type your task and press Enter. Type 'exit' or 'quit' to exit.[/dim]\n")
        ui.console.print("[bold]Task:[/bold] ", end="")
        current_prompt = input()
        
        if current_prompt.lower() in ['exit', 'quit', 'q']:
            return
        
        ui.add_message("user", current_prompt)
    
    max_iterations = 50  # Prevent infinite loops
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        # Get tool definitions
        tools = tool_registry.get_tool_definitions()
        
        # Stream response from Ollama
        ui.print(f"\n[dim]🤖 Assistant (iteration {iteration})...[/dim]\n")
        response_text = ""
        tool_calls_buffer = []
        final_message = None
        
        try:
            # On first iteration, use the user's prompt. On subsequent iterations, use empty string
            # since the conversation history already contains everything
            prompt = current_prompt if iteration == 1 else ""
            
            chunk_count = 0
            for chunk in client.chat(prompt, tools=tools, stream=True):
                chunk_count += 1
                message = chunk.get("message", {})
                
                # Handle content
                content_delta = message.get("content")
                if content_delta:
                    response_text += content_delta
                    # Use sys.stdout for real-time streaming (Rich doesn't support flush)
                    sys.stdout.write(content_delta)
                    sys.stdout.flush()
                
                # Handle tool calls (can come in chunks or all at once)
                # Tool calls can be a list or a single dict
                tool_calls = message.get("tool_calls")
                if tool_calls:
                    if isinstance(tool_calls, list):
                        for tool_call in tool_calls:
                            # Check if we already have this tool call (by ID)
                            tool_id = tool_call.get("id")
                            if tool_id and not any(tc.get("id") == tool_id for tc in tool_calls_buffer):
                                tool_calls_buffer.append(tool_call)
                            elif not tool_id:
                                tool_calls_buffer.append(tool_call)
                    else:
                        # Single tool call
                        if tool_calls not in tool_calls_buffer:
                            tool_calls_buffer.append(tool_calls)
                
                # Store final message for tool call extraction
                if chunk.get("done"):
                    final_message = message
                    break
            
            if chunk_count == 0:
                ui.print("[bold red]❌ No chunks received from Ollama![/bold red]")
                ui.print("[yellow]This could mean:[/yellow]")
                ui.print("[dim]  - Ollama is not responding (try: ollama serve)[/dim]")
                ui.print("[dim]  - The model is not loaded (try: ollama pull {client.model})[/dim]")
                ui.print("[dim]  - Check stderr for detailed error messages[/dim]")
                # Check Ollama one more time
                if not check_ollama_running():
                    ui.print("[bold red]Ollama is not responding![/bold red]")
                break
            
            # Check final message for tool calls that might have come at the end
            if final_message:
                final_tool_calls = final_message.get("tool_calls")
                if final_tool_calls:
                    if isinstance(final_tool_calls, list):
                        for tool_call in final_tool_calls:
                            tool_id = tool_call.get("id")
                            if tool_id and not any(tc.get("id") == tool_id for tc in tool_calls_buffer):
                                tool_calls_buffer.append(tool_call)
                            elif not tool_id and tool_call not in tool_calls_buffer:
                                tool_calls_buffer.append(tool_call)
                    else:
                        if final_tool_calls not in tool_calls_buffer:
                            tool_calls_buffer.append(final_tool_calls)
            
            # Add complete response to UI
            if response_text:
                ui.print()  # New line after streaming
                ui.add_message("assistant", response_text)
            
            # Execute tool calls if any
            if tool_calls_buffer:
                ui.print(f"\n[bold yellow]🔧 Executing {len(tool_calls_buffer)} tool call(s)...[/bold yellow]\n")
                execute_tool_calls(client, tool_registry, tool_calls_buffer, ui)
                
                # Continue conversation with tool results
                # Send a continuation message to let the model process tool results
                current_prompt = "Based on the tool results, please continue with the next step to complete the task."
                ui.refresh()
            else:
                # No more tool calls - task complete
                if not response_text:
                    ui.print("[yellow]⚠️  No response or tool calls received from assistant[/yellow]")
                ui.print("\n[bold green]✅ Task completed![/bold green]")
                break
                
        except KeyboardInterrupt:
            ui.print("\n[yellow]⚠️  Interrupted by user[/yellow]")
            break
        except Exception as e:
            import traceback
            ui.print(f"\n[bold red]❌ Error:[/bold red] {str(e)}")
            ui.print(f"[dim]{traceback.format_exc()}[/dim]")
            break
    
    if iteration >= max_iterations:
        ui.print(f"\n[yellow]⚠️  Reached maximum iterations ({max_iterations})[/yellow]")


def check_ollama_running(endpoint: str = "http://127.0.0.1:11434") -> bool:
    """Check if Ollama is running."""
    try:
        response = requests.get(f"{endpoint}/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False


def start_ollama(ui: ChatUI):
    """Start Ollama if it's not running."""
    if check_ollama_running():
        return True
    
    ui.print("[yellow]⚠️  Ollama is not running. Starting Ollama...[/yellow]")
    
    try:
        # Try to start Ollama in the background
        # Check if ollama command exists
        result = subprocess.run(
            ["which", "ollama"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            ui.print("[bold red]❌ Error: 'ollama' command not found![/bold red]")
            ui.print("[dim]Please install Ollama from https://ollama.ai[/dim]")
            return False
        
        ollama_path = result.stdout.strip()
        
        # Start Ollama in background
        ui.print("[dim]Starting Ollama server...[/dim]")
        process = subprocess.Popen(
            [ollama_path, "serve"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )
        
        # Wait for Ollama to start (up to 10 seconds)
        ui.print("[dim]Waiting for Ollama to be ready...[/dim]")
        for i in range(20):  # 20 * 0.5 = 10 seconds
            time.sleep(0.5)
            if check_ollama_running():
                ui.print("[green]✅ Ollama is now running![/green]\n")
                return True
            if i % 4 == 0:  # Show progress every 2 seconds
                ui.print("[dim].", end="", flush=True)
        
        ui.print()
        ui.print("[yellow]⚠️  Ollama started but may not be ready yet. Continuing anyway...[/yellow]\n")
        return True
        
    except Exception as e:
        ui.print(f"[bold red]❌ Error starting Ollama: {e}[/bold red]")
        ui.print("[dim]Please start Ollama manually: ollama serve[/dim]")
        return False


def main():
    """Main function."""
    args = parse_arguments()
    
    # Initialize UI first
    ui = ChatUI()
    
    # Check and start Ollama if needed
    ui.print("[dim]Checking Ollama connection...[/dim]")
    if not check_ollama_running(args.endpoint):
        if not start_ollama(ui):
            ui.print("[bold red]❌ Cannot continue without Ollama. Exiting.[/bold red]")
            sys.exit(1)
        # Double-check after starting
        if not check_ollama_running(args.endpoint):
            ui.print("[bold red]❌ Ollama started but not responding. Please check manually.[/bold red]")
            sys.exit(1)
    else:
        ui.print("[green]✅ Ollama is running[/green]\n")
    
    # Initialize components
    client = OllamaClient(base_url=args.endpoint, model=args.model)
    tool_registry = ToolRegistry(base_dir=args.base_dir)
    
    try:
        if args.task:
            # Autonomous mode
            run_agentic_loop(client, tool_registry, ui, initial_task=args.task)
        else:
            # Interactive mode
            while True:
                run_agentic_loop(client, tool_registry, ui)
                ui.print("\n[dim]Press Enter to continue or type 'exit' to quit...[/dim]")
                user_input = input()
                if user_input.lower() in ['exit', 'quit', 'q']:
                    break
                ui.clear()
    except KeyboardInterrupt:
        ui.print("\n[yellow]👋 Goodbye![/yellow]")
    finally:
        # Cleanup
        tool_registry.close_browser()


if __name__ == "__main__":
    main()

