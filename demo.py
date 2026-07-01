"""Interactive CLI chat bot built on AgentClient.

The client is intentionally thin: it constructs an AgentClient and calls
agent.chat(message) each turn. Conversation memory lives in AgentClient, so this
file only deals with terminal I/O and slash-commands.

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
    /file <path>   attach a file to your next message; may appear inline, e.g.
                   "code review /file src/app.py". Reads txt/md/pdf/xlsx/docx/pptx
                   and any plain-text/source file.
    /reset         clear the conversation history
    /help          show this help
    /exit, /quit   leave
"""

import asyncio
import logging
import os
import re

from dotenv import load_dotenv

from disesfgewuAgent import AgentClient

ROOT = os.path.dirname(os.path.abspath(__file__))
API_CONFIG = os.path.join(ROOT, "config", "api.local.json")
SKILLS_CONFIG = os.path.join(ROOT, "config", "skills.json")
SKILLS_DIR = os.path.join(ROOT, "skills")
HISTORY_DIR = os.path.join(ROOT, "history")
LOG_DIR = os.path.join(ROOT, "logs")

HELP = (
    "  /file <path>   attach a file (works inline too, e.g. 'review /file a.py')\n"
    "  /reset         clear the conversation history\n"
    "  /help          show this help\n"
    "  /exit, /quit   leave"
)

# Matches a "/file <path>" token anywhere in a message (quoted or bare path).
FILE_TOKEN_RE = re.compile(r"""/file\s+("[^"]+"|'[^']+'|\S+)""")


def _check_setup() -> bool:
    load_dotenv()
    ok = True
    if not os.path.exists(API_CONFIG):
        print("Missing config/api.local.json - copy config/api.example.json and fill it in.")
        ok = False
    if not os.path.exists(SKILLS_CONFIG):
        print("Missing config/skills.json - copy config/skills.example.json.")
        ok = False
    if not os.getenv("EMBEDDING_API"):
        print("Missing EMBEDDING_API - set it in .env (copy .env.example).")
        ok = False
    return ok


def _setup_logging() -> str:
    # INFO+ decisions (difficulty, chosen model, iterations, compression) go to a
    # file; only WARNING+ reaches the console so the chat stays readable.
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, "demo.log")

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(ch)
    return log_path


def _extract_files(msg: str):
    """Pull any '/file <path>' tokens out of a message; return (cleaned, paths)."""
    paths = []

    def _repl(match):
        paths.append(match.group(1).strip("\"'"))
        return " "

    cleaned = FILE_TOKEN_RE.sub(_repl, msg).strip()
    return cleaned, paths


async def main() -> None:
    log_path = _setup_logging()

    if not _check_setup():
        return

    print("agent-client-template chat bot - type /help for commands, /exit to quit.")
    print(f"(logging INFO to {os.path.relpath(log_path, ROOT)})\n")

    pending_files = []  # files attached for the next message

    async with AgentClient(
        SKILLS_CONFIG, SKILLS_DIR, API_CONFIG, historyDir=HISTORY_DIR
    ) as agent:
        while True:
            try:
                user_msg = input("you > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not user_msg:
                continue
            if user_msg in ("/exit", "/quit"):
                break
            if user_msg == "/help":
                print(HELP + "\n")
                continue
            if user_msg == "/reset":
                agent.resetConversation()
                pending_files.clear()
                print("(conversation cleared)\n")
                continue

            cleaned, paths = _extract_files(user_msg)
            for path in paths:
                if os.path.exists(path):
                    pending_files.append(path)
                    print(f"(attached {os.path.basename(path)})")
                else:
                    print(f"(file not found: {path})")

            if cleaned == "/file":
                print("(usage: /file <path>)\n")
                continue
            if not cleaned:
                # message was only attachments (or empty): wait for the question
                print()
                continue
            if not paths and cleaned.startswith("/"):
                print("(unknown command - type /help)\n")
                continue

            files = pending_files[:]
            pending_files.clear()

            print("(thinking...)", flush=True)
            try:
                answer = await agent.chat(cleaned, inputFiles=files)
            except Exception as e:
                print(f"bot > [error] {e}\n")
                continue

            print(f"bot > {answer}\n")

    print("bye.")


if __name__ == "__main__":
    asyncio.run(main())
