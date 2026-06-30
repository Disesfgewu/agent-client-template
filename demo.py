"""Interactive CLI chat bot built on AgentClient.

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
    /file <path>   attach a local file (txt/md/pdf/xlsx/docx/pptx) to your next message
    /reset         clear the conversation history
    /help          show this help
    /exit, /quit   leave
"""

import asyncio
import logging
import os

from dotenv import load_dotenv

from disesfgewuAgent import AgentClient

ROOT = os.path.dirname(os.path.abspath(__file__))
API_CONFIG = os.path.join(ROOT, "config", "api.local.json")
SKILLS_CONFIG = os.path.join(ROOT, "config", "skills.json")
SKILLS_DIR = os.path.join(ROOT, "skills")
HISTORY_DIR = os.path.join(ROOT, "history")

# How many past turns to feed back as context so it behaves like a chat.
MAX_TURNS_IN_CONTEXT = 6

HELP = (
    "  /file <path>   attach a file to your next message\n"
    "  /reset         clear the conversation history\n"
    "  /help          show this help\n"
    "  /exit, /quit   leave"
)


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


def _build_input(history: list, user_msg: str) -> str:
    if not history:
        return user_msg
    transcript = "\n".join(
        f"{role}: {text}" for role, text in history[-MAX_TURNS_IN_CONTEXT * 2:]
    )
    return f"Conversation so far:\n{transcript}\n\nUser: {user_msg}"


async def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    if not _check_setup():
        return

    print("agent-client-template chat bot - type /help for commands, /exit to quit.\n")

    history = []        # list of (role, text)
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
                history.clear()
                pending_files.clear()
                print("(conversation cleared)\n")
                continue
            if user_msg == "/file" or user_msg.startswith("/file "):
                parts = user_msg.split(maxsplit=1)
                if len(parts) < 2 or not parts[1].strip():
                    print("(usage: /file <path>)\n")
                    continue
                path = parts[1].strip().strip('"').strip("'")
                if os.path.exists(path):
                    pending_files.append(path)
                    print(f"(attached {os.path.basename(path)})\n")
                else:
                    print(f"(file not found: {path})\n")
                continue
            if user_msg.startswith("/"):
                print("(unknown command - type /help)\n")
                continue

            prompt = _build_input(history, user_msg)
            files = pending_files[:]
            pending_files.clear()

            print("(thinking...)", flush=True)
            try:
                answer = await agent.ask(prompt, inputFiles=files)
            except Exception as e:
                print(f"bot > [error] {e}\n")
                continue

            print(f"bot > {answer}\n")
            history.append(("User", user_msg))
            history.append(("Assistant", answer))

    print("bye.")


if __name__ == "__main__":
    asyncio.run(main())
