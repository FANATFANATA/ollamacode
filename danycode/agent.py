from __future__ import annotations

import json
import os
import platform

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from danycode.client import OllamaClient
from danycode.config import Config
from danycode.session import Session
from danycode.tools import execute_tool, get_shell_name

console = Console()

MAX_ITERATIONS = 25
REPEAT_THRESHOLD = 3


class Agent:
    def __init__(self, config: Config, session: Session):
        self.config = config
        self.session = session
        self.client = OllamaClient(config)
        self._ensure_system_prompt()

    def _ensure_system_prompt(self) -> None:
        if not self.session.messages or self.session.messages[0]["role"] != "system":
            shell_name = get_shell_name()
            env = f"{platform.system()} | {shell_name} | {os.getcwd()}"
            full_prompt = f"{env}\n{self.config.system_prompt}"
            self.session.messages.insert(
                0,
                {
                    "role": "system",
                    "content": full_prompt,
                },
            )
            self.session.save()

    def _ask_user(self, question: str) -> str:
        console.print(Panel(question, title="Assistant asks", border_style="yellow"))
        try:
            return input("Your answer: ")
        except (EOFError, KeyboardInterrupt):
            return ""

    async def run(self, user_input: str) -> None:
        self.session.add({"role": "user", "content": user_input})
        await self._loop()

    async def _loop(self) -> None:
        iterations = 0
        recent_sigs: list[str] = []

        while True:
            iterations += 1
            if iterations > MAX_ITERATIONS:
                console.print("\n[bold red]Max tool iterations reached.[/bold red]")
                break

            messages = self.session.messages
            assistant_msg = await self._get_response(messages)

            if assistant_msg.get("tool_calls"):
                self.session.add(assistant_msg)

                for tc in assistant_msg["tool_calls"]:
                    fn_name = tc["function"]["name"]
                    fn_args = tc["function"]["arguments"]

                    sig = json.dumps({"n": fn_name, "a": fn_args}, sort_keys=True)
                    recent_sigs.append(sig)
                    if len(recent_sigs) > REPEAT_THRESHOLD:
                        recent_sigs.pop(0)
                    if (
                        len(recent_sigs) == REPEAT_THRESHOLD
                        and len(set(recent_sigs)) == 1
                    ):
                        console.print(
                            "\n[bold red]Repeated identical tool call. Stopping.[/bold red]"
                        )
                        self.session.add(
                            {
                                "role": "tool",
                                "content": json.dumps(
                                    {
                                        "error": "Repeated identical tool call detected. Stopping."
                                    }
                                ),
                            }
                        )
                        return

                    console.print(
                        Panel(
                            f"[bold]{fn_name}[/bold]\n{json.dumps(fn_args, indent=2, ensure_ascii=False)}",
                            title="Tool call",
                            border_style="cyan",
                        )
                    )

                    if self.config.mode == "ask" and fn_name != "ask_user":
                        try:
                            answer = input("Execute? [Y/n]: ").strip().lower()
                        except (EOFError, KeyboardInterrupt):
                            answer = "n"
                        if answer not in ("", "y", "yes"):
                            result = json.dumps({"error": "User denied tool execution"})
                            self.session.add({"role": "tool", "content": result})
                            continue

                    result = execute_tool(fn_name, fn_args, self._ask_user)

                    display_result = result[:3000] + (
                        "..." if len(result) > 3000 else ""
                    )
                    console.print(
                        Panel(
                            display_result,
                            title=f"Result: {fn_name}",
                            border_style="green",
                        )
                    )

                    self.session.add({"role": "tool", "content": result})
            else:
                self.session.add(assistant_msg)
                break

    async def _get_response(self, messages: list[dict]) -> dict:
        try:
            return await self._stream_response(messages)
        except Exception:
            return await self._non_stream(messages)

    async def _stream_response(self, messages: list[dict]) -> dict:
        content_parts: list[str] = []
        thinking_parts: list[str] = []
        tool_calls: list[dict] = []

        async for chunk in self.client.chat_stream(messages):
            msg = chunk.get("message", {})

            if msg.get("thinking"):
                thinking_parts.append(msg["thinking"])
                console.print(msg["thinking"], end="", style="dim", highlight=False)

            if msg.get("content"):
                content_parts.append(msg["content"])
                console.print(msg["content"], end="", highlight=False)

            if msg.get("tool_calls"):
                tool_calls.extend(msg["tool_calls"])

        if content_parts or thinking_parts:
            console.print()

        if not content_parts and not tool_calls:
            return await self._non_stream(messages)

        result: dict = {"role": "assistant", "content": "".join(content_parts) or None}
        if thinking_parts:
            result["thinking"] = "".join(thinking_parts)
        if tool_calls:
            result["tool_calls"] = tool_calls
        return result

    async def _non_stream(self, messages: list[dict]) -> dict:
        data = await self.client.chat(messages)
        msg = data.get("message", {})
        content = msg.get("content")
        thinking = msg.get("thinking")
        if thinking:
            console.print(thinking, style="dim")
        if content:
            console.print(Markdown(content))
        result: dict = {"role": "assistant", "content": content}
        if thinking:
            result["thinking"] = thinking
        if msg.get("tool_calls"):
            result["tool_calls"] = msg["tool_calls"]
        return result
