"""Minimal runnable example for the agent-client-template / disesfgewuAgent.

Prerequisites
-------------
1. cp config/api.example.json config/api.local.json   # then fill in your models / keys
2. cp config/skills.example.json config/skills.json
3. cp .env.example .env                                # then set EMBEDDING_API
4. pip install -r requirements.txt   (or: pip install .)

Run
---
    python example.py
"""

import asyncio
import os

from disesfgewuAgent import AgentClient

ROOT = os.path.dirname(os.path.abspath(__file__))
API_CONFIG = os.path.join(ROOT, "config", "api.local.json")
SKILLS_CONFIG = os.path.join(ROOT, "config", "skills.json")
SKILLS_DIR = os.path.join(ROOT, "skills")
HISTORY_DIR = os.path.join(ROOT, "history")

# Soft threshold (in tokens) at which accumulated context memory is compressed.
CONTEXT_WINDOW = 32000


async def main() -> None:
    # Config is injected explicitly: API_CONFIG is a path here, but a list of
    # model dicts works too. historyDir is optional (omit it to disable disk writes).
    async with AgentClient(
        SKILLS_CONFIG,
        SKILLS_DIR,
        API_CONFIG,
        contextWindowSize=CONTEXT_WINDOW,
        historyDir=HISTORY_DIR,
    ) as agent:
        # ask() returns a fixed-schema result dict; the text is result["answer"].
        # 1) A simple question.
        result = await agent.ask("What is 2 + 2? Reply with just the number.")
        print("Q1 ->", result["answer"])

        # 2) The same client is reusable for an unrelated task; per-conversation
        #    state (history, context memory) is reset on every ask().
        result = await agent.ask(
            "Give me three concise best practices for code review."
        )
        print("Q2 ->", result["answer"])

        # 3) Ask a question about one or more local files (txt/md/pdf/xlsx/docx/pptx).
        #    Uncomment and point at a real file to try it.
        # result = await agent.ask(
        #     "Summarize the attached document in three bullet points.",
        #     inputFiles=[os.path.join(ROOT, "README.md")],
        # )
        # print("Q3 ->", result["answer"])


if __name__ == "__main__":
    asyncio.run(main())
