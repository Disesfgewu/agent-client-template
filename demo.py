"""Interactive agent TUI built on AgentClient.

This is an AGENT, not a chat bot: you give it a task and it works toward the goal
autonomously - reasoning step by step, running Python it writes, inspecting files -
and you see each step as it happens (like a coding agent). The client stays thin:
it constructs an AgentClient, renders the agent's events, and calls agent.chat().

One-time setup
--------------
    cp config/api.example.json   config/api.local.json   # fill in models / keys
    cp config/skills.example.json config/skills.json
    cp .env.example              .env                     # set EMBEDDING_API
    pip install -r requirements.txt

Run
---
    python demo.py

Commands
--------
    /file <path>   attach a file (works inline too, e.g. 'review /file a.py')
    /reset         start a fresh task / clear history
    /help          show this help
    /exit, /quit   leave
"""

import asyncio
import logging
import os
import re

from dotenv import load_dotenv

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.syntax import Syntax
except ImportError:
    raise SystemExit("This demo needs 'rich'. Install it with: pip install rich")

from disesfgewuAgent import AgentClient

ROOT = os.path.dirname(os.path.abspath(__file__))
API_CONFIG = os.path.join(ROOT, "config", "api.local.json")
SKILLS_CONFIG = os.path.join(ROOT, "config", "skills.json")
SKILLS_DIR = os.path.join(ROOT, "skills")
HISTORY_DIR = os.path.join(ROOT, "history")
LOG_DIR = os.path.join(ROOT, "logs")

HELP = (
    "  /file <path>   attach a file (works inline too, e.g. 'review /file a.py')\n"
    "  /reset         start a fresh task / clear history\n"
    "  /help          show this help\n"
    "  /exit, /quit   leave"
)

FILE_TOKEN_RE = re.compile(r"""/file\s+("[^"]+"|'[^']+'|\S+)""")

console = Console()


def _check_setup() -> bool:
    load_dotenv()
    ok = True
    if not os.path.exists(API_CONFIG):
        console.print("[red]Missing config/api.local.json[/red] - copy config/api.example.json.")
        ok = False
    if not os.path.exists(SKILLS_CONFIG):
        console.print("[red]Missing config/skills.json[/red] - copy config/skills.example.json.")
        ok = False
    if not os.getenv("EMBEDDING_API"):
        console.print("[red]Missing EMBEDDING_API[/red] - set it in .env (copy .env.example).")
        ok = False
    return ok


def _setup_logging() -> str:
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, "demo.log")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(fh)
    return log_path


def _extract_files(msg: str):
    paths = []

    def _repl(match):
        paths.append(match.group(1).strip("\"'"))
        return " "

    cleaned = FILE_TOKEN_RE.sub(_repl, msg).strip()
    return cleaned, paths


def _on_event(event: dict) -> None:
    """Render one step of the agent loop as it happens."""
    etype = event.get("type")
    if etype == "assessed":
        tag = "complex" if event["complex"] else "simple"
        console.print(f"[dim]planning - task looks {tag}[/dim]")
    elif etype == "step":
        reasoning = event.get("reasoning") or "(thinking)"
        console.print(f"[yellow]> reasoning[/yellow] [dim]{reasoning}[/dim]")
        nxt = event.get("next_action")
        if nxt:
            console.print(f"  [dim]next: {nxt}[/dim]")
    elif etype == "execute":
        reasoning = event.get("reasoning")
        if reasoning:
            console.print(f"[yellow]> reasoning[/yellow] [dim]{reasoning}[/dim]")
        console.print(
            Panel(
                Syntax(event.get("code", ""), "python", theme="monokai", word_wrap=True),
                title="[bold]> run python[/bold]",
                border_style="yellow",
                padding=(0, 1),
            )
        )
    elif etype == "execution_result":
        out = (event.get("stdout") or "").rstrip()
        err = (event.get("stderr") or "").rstrip()
        body = out or "[dim](no stdout)[/dim]"
        if err:
            body += f"\n[red]{err}[/red]"
        rc = event.get("exit_code", 0)
        console.print(
            Panel(
                body,
                title=f"[bold]output (exit {rc})[/bold]",
                border_style="green" if rc == 0 else "red",
                padding=(0, 1),
            )
        )


async def main() -> None:
    log_path = _setup_logging()

    if not _check_setup():
        return

    console.print(
        Panel.fit(
            "[bold]agent-client-template[/bold]\n"
            "[dim]autonomous reasoning + code-execution agent - /help - /exit[/dim]",
            border_style="cyan",
        )
    )
    console.print(f"[dim]logging INFO to {os.path.relpath(log_path, ROOT)}[/dim]\n")

    pending_files = []

    async with AgentClient(
        SKILLS_CONFIG,
        SKILLS_DIR,
        API_CONFIG,
        historyDir=HISTORY_DIR,
        enableCodeExecution=True,
        onEvent=_on_event,
    ) as agent:
        while True:
            try:
                user_msg = console.input("[bold cyan]you >[/bold cyan] ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print()
                break

            if not user_msg:
                continue
            if user_msg in ("/exit", "/quit"):
                break
            if user_msg == "/help":
                console.print(HELP + "\n")
                continue
            if user_msg == "/reset":
                agent.resetConversation()
                pending_files.clear()
                console.print("[dim](new task - history cleared)[/dim]\n")
                continue

            cleaned, paths = _extract_files(user_msg)
            for path in paths:
                if os.path.exists(path):
                    pending_files.append(path)
                    console.print(f"[dim](attached {os.path.basename(path)})[/dim]")
                else:
                    console.print(f"[red](file not found: {path})[/red]")

            if cleaned == "/file":
                console.print("[dim](usage: /file <path>)[/dim]\n")
                continue
            if not cleaned:
                console.print()
                continue
            if not paths and cleaned.startswith("/"):
                console.print("[dim](unknown command - type /help)[/dim]\n")
                continue

            files = pending_files[:]
            pending_files.clear()

            try:
                with console.status("[dim]agent working...[/dim]", spinner="dots"):
                    answer = await agent.chat(cleaned, inputFiles=files)
            except Exception as e:
                console.print(f"[red]error:[/red] {e}\n")
                continue

            console.print(
                Panel(
                    Markdown(answer),
                    title="[bold green]answer[/bold green]",
                    border_style="green",
                    padding=(0, 1),
                )
            )
            console.print()

    console.print("[dim]bye.[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
