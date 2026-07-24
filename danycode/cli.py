from __future__ import annotations

import asyncio
import os

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from danycode.agent import Agent
from danycode.client import OllamaClient
from danycode.config import Config
from danycode.session import Session

app = typer.Typer(
    name="danycode", help="Ollama CLI coding assistant", invoke_without_command=True
)
console = Console()


def _build_config(
    model: str | None,
    host: str | None,
    temperature: float | None,
    top_p: float | None,
    top_k: int | None,
    min_p: float | None,
    num_ctx: int | None,
    num_predict: int | None,
    seed: int | None,
    think: str | None,
    keep_alive: str | None,
    system_prompt: str | None,
    mode: str | None,
) -> Config:
    overrides = {
        "model": model,
        "host": host,
        "temperature": temperature,
        "top_p": top_p,
        "top_k": top_k,
        "min_p": min_p,
        "num_ctx": num_ctx,
        "num_predict": num_predict,
        "seed": seed,
        "think": think,
        "keep_alive": keep_alive,
        "system_prompt": system_prompt,
        "mode": mode,
    }
    return Config.load(overrides)


def _check_ollama(config: Config) -> None:
    client = OllamaClient(config)
    ok = asyncio.run(client.health())
    if not ok:
        console.print(f"[bold red]Ollama is not reachable at {config.host}[/bold red]")
        console.print("Start it with: [dim]ollama serve[/dim]")
        raise typer.Exit(1)


def _auto_select_model(config: Config) -> None:
    client = OllamaClient(config)
    models = asyncio.run(client.list_models())
    if not models:
        console.print(
            "[bold red]No models available. Pull one: ollama pull qwen3:8b[/bold red]"
        )
        raise typer.Exit(1)
    lightest = min(models, key=lambda m: m.get("size", float("inf")))
    config.model = lightest["name"]
    console.print(f"[dim]Auto-selected lightest model: {config.model}[/dim]")


def _print_models(config: Config) -> list[dict]:
    client = OllamaClient(config)
    models = asyncio.run(client.list_models())
    if not models:
        console.print("[dim]No models found.[/dim]")
        return []
    table = Table(title="Available Models")
    table.add_column("#", style="dim", width=4)
    table.add_column("Name", style="cyan")
    table.add_column("Params", style="green")
    table.add_column("Quant", style="yellow")
    table.add_column("Family", style="dim")
    table.add_column("Size", style="dim")
    for i, m in enumerate(models, 1):
        details = m.get("details", {})
        name = m.get("name", "?")
        params = details.get("parameter_size", "-")
        quant = details.get("quantization_level", "-")
        family = details.get("family", "-")
        size_bytes = m.get("size", 0)
        size = f"{size_bytes / 1e9:.1f} GB" if size_bytes else "-"
        table.add_row(str(i), name, params, quant, family, size)
    console.print(table)
    return models


def _print_running(config: Config) -> None:
    client = OllamaClient(config)
    models = asyncio.run(client.list_running())
    if not models:
        console.print("[dim]No running models.[/dim]")
        return
    table = Table(title="Running Models")
    table.add_column("Name", style="cyan")
    table.add_column("VRAM", style="green")
    table.add_column("Context", style="yellow")
    table.add_column("Expires", style="dim")
    for m in models:
        name = m.get("name", "?")
        vram = m.get("size_vram", 0)
        vram_str = f"{vram / 1e9:.1f} GB" if vram else "-"
        ctx = str(m.get("context_length", "-"))
        expires = m.get("expires_at", "")[:19]
        table.add_row(name, vram_str, ctx, expires)
    console.print(table)


def _show_model_info(config: Config, name: str) -> None:
    client = OllamaClient(config)
    try:
        info = asyncio.run(client.show_model(name))
    except Exception:
        return
    details = info.get("details", {})
    caps = info.get("capabilities", [])
    params = info.get("parameters", "")
    console.print(f"  [dim]Family:[/dim] {details.get('family', '-')}")
    console.print(f"  [dim]Params:[/dim] {details.get('parameter_size', '-')}")
    console.print(f"  [dim]Quant:[/dim] {details.get('quantization_level', '-')}")
    console.print(f"  [dim]Format:[/dim] {details.get('format', '-')}")
    if caps:
        console.print(f"  [dim]Capabilities:[/dim] {', '.join(caps)}")
    if params:
        console.print(f"  [dim]Parameters:[/dim] {params.strip()}")


def _select_model(config: Config) -> None:
    models = _print_models(config)
    if not models:
        return
    try:
        choice = Prompt.ask(f"Select model [1-{len(models)}]", default="")
    except (EOFError, KeyboardInterrupt):
        return
    if not choice.strip():
        return
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(models):
            config.model = models[idx]["name"]
            console.print(f"[green]Model set to:[/green] {config.model}")
            _show_model_info(config, config.model)
        else:
            console.print("[red]Invalid number.[/red]")
    except ValueError:
        console.print("[red]Enter a number.[/red]")


def _handle_set(config: Config, args: str) -> None:
    parts = args.split(maxsplit=1)
    if len(parts) != 2:
        console.print("[dim]Usage: /set <param> <value>[/dim]")
        console.print(
            f"[dim]Params: {', '.join(Config.load().__dataclass_fields__.keys())}[/dim]"
        )
        return
    key, value = parts[0], parts[1]
    err = config.update(key, value)
    if err:
        console.print(f"[red]{err}[/red]")
    else:
        console.print(f"[green]{key}[/green] = {getattr(config, key)}")


def _print_config(config: Config) -> None:
    table = Table(title="Current Config")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")
    for key, val in config.display():
        table.add_row(key, val)
    console.print(table)


def _print_version(config: Config) -> None:
    client = OllamaClient(config)
    try:
        ver = asyncio.run(client.version())
        console.print(f"Ollama version: [green]{ver}[/green]")
    except Exception:
        console.print("[red]Failed to get version.[/red]")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    prompt: str = typer.Argument(None, help="One-shot prompt. Omit for REPL."),
    session_name: str = typer.Option(
        "default", "--session", "-s", help="Session name."
    ),
    model: str = typer.Option(None, "--model", "-m", help="Model name."),
    host: str = typer.Option(None, "--host", help="Ollama API base URL."),
    temperature: float = typer.Option(None, "--temperature", "-t"),
    top_p: float = typer.Option(None, "--top-p"),
    top_k: int = typer.Option(None, "--top-k"),
    min_p: float = typer.Option(None, "--min-p"),
    num_ctx: int = typer.Option(None, "--num-ctx"),
    num_predict: int = typer.Option(None, "--num-predict"),
    seed: int = typer.Option(None, "--seed"),
    think: str = typer.Option(None, "--think", help="false/true/high/medium/low/max."),
    keep_alive: str = typer.Option(None, "--keep-alive"),
    system_prompt: str = typer.Option(None, "--system", help="System prompt."),
    mode: str = typer.Option(None, "--mode", help="yolo or ask."),
    new: bool = typer.Option(False, "--new", "-n", help="Start fresh session."),
):
    if ctx.invoked_subcommand is not None:
        return

    config = _build_config(
        model,
        host,
        temperature,
        top_p,
        top_k,
        min_p,
        num_ctx,
        num_predict,
        seed,
        think,
        keep_alive,
        system_prompt,
        mode,
    )
    config.ensure_dirs()
    _check_ollama(config)

    if not config.model:
        _auto_select_model(config)

    session = Session(session_name)
    if new:
        session.clear()

    agent = Agent(config, session)

    if prompt:
        asyncio.run(agent.run(prompt))
        return

    os.system("cls" if os.name == "nt" else "clear")

    console.print(
        Panel(
            f"[bold]DanyCode[/bold] | model: {config.model} | mode: {config.mode} | session: {session_name}\n"
            f"[dim]/quit /clear /sessions /models /model /ps /config /set <k> <v> /save /version[/dim]\n"
            f"[dim]// at start of message sends it to model as-is[/dim]",
            border_style="green",
        )
    )

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]You[/bold green]")
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        stripped = user_input.strip()

        if stripped.startswith("//"):
            asyncio.run(agent.run(stripped[1:]))
            continue

        if stripped.startswith("/"):
            cmd = stripped.split()[0]
            if cmd == "/quit":
                break
            elif cmd == "/clear":
                session.clear()
                agent._ensure_system_prompt()
                console.print("[dim]Session cleared.[/dim]")
            elif cmd == "/sessions":
                all_sessions = Session.list_sessions()
                console.print(
                    f"Sessions: {', '.join(all_sessions) if all_sessions else 'none'}"
                )
            elif cmd == "/models":
                _print_models(config)
            elif cmd == "/model":
                _select_model(config)
            elif cmd == "/ps":
                _print_running(config)
            elif cmd == "/config":
                _print_config(config)
            elif cmd == "/set":
                _handle_set(config, stripped[5:])
            elif cmd == "/save":
                config.save()
                console.print("[green]Config saved.[/green]")
            elif cmd == "/version":
                _print_version(config)
            else:
                console.print(f"[red]Unknown command: {cmd}[/red]")
            continue

        if not stripped:
            continue

        asyncio.run(agent.run(stripped))


@app.command()
def models(
    host: str = typer.Option(None, "--host", help="Ollama API base URL."),
):
    config = _build_config(
        None, host, None, None, None, None, None, None, None, None, None, None, None
    )
    _check_ollama(config)
    _print_models(config)


@app.command()
def sessions():
    all_sessions = Session.list_sessions()
    if all_sessions:
        for s in all_sessions:
            console.print(f"  {s}")
    else:
        console.print("No sessions found.")


if __name__ == "__main__":
    app()
